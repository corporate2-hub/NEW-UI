from django.contrib import admin, messages
from django.utils.translation import gettext_lazy as _
from django.shortcuts import redirect, render
from django.utils.html import format_html
from django.urls import path, reverse
from django.utils import timezone
from django.http import HttpResponse
from django.db.models import Sum, Count, Q
import csv
import io

# Custom filter to allow filtering enrollments by related course ID
class CourseIDFilter(admin.SimpleListFilter):
    title = _('Course')
    parameter_name = 'batch__course__id'

    def lookups(self, request, model_admin):
        # Provide a list of courses for the dropdown.
        # Superusers see all courses; company users only see their company's courses.
        from courses.models import Course as _Course

        if request.user.is_superuser:
            qs = _Course.objects.all()
        else:
            company = getattr(request.user, 'company', None)
            if company is None:
                qs = _Course.objects.none()
            else:
                qs = _Course.objects.filter(company=company)

        return list(qs.order_by('title').values_list('id', 'title'))

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(batch__course_id=self.value())
        return queryset


class BatchFilter(admin.SimpleListFilter):
    title = _('Batch')
    parameter_name = 'batch__id'

    def lookups(self, request, model_admin):
        # Superusers see all batches; company users see only their company's batches
        from .models import Batch as _Batch

        if request.user.is_superuser:
            qs = _Batch.objects.all()
        else:
            company = getattr(request.user, 'company', None)
            if company is None:
                qs = _Batch.objects.none()
            else:
                qs = _Batch.objects.filter(company=company)

        return list(qs.order_by('name').values_list('id', 'name'))

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(batch_id=self.value())
        return queryset
 
from unfold.admin import ModelAdmin
from .models import Batch, Enrollment, SalesRecord, Coupon
from .services.certificate_service import generate_certificate_pdf
from .services.email_service import send_company_email
from accounts.admin_mixins import CompanyAdminMixin
from accounts.models import CustomUser
from courses.models import Course


class BatchAdmin(CompanyAdminMixin, ModelAdmin):
    list_display = ['name', 'company', 'course', 'start_date', 'end_date', 'get_enrolled_count', 'status']
    list_filter = ['status', 'start_date']

    def get_list_filter(self, request):
        if request.user.is_superuser:
            return ['company', 'status', 'course', 'start_date']
        return ['status', 'start_date']
    search_fields = ['name', 'course__title']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('Basic Info', {'fields': ('company', 'course', 'name', 'instructors')}),
        ('Batch Duration', {'fields': ('start_date', 'end_date')}),
        ('Settings', {'fields': ('max_students', 'status')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )

    def save_model(self, request, obj, form, change):
        if not request.user.is_superuser and not obj.company_id:
            obj.company = request.user.company
        super().save_model(request, obj, form, change)

    def get_queryset(self, request):
        # CompanyAdminMixin already filters by batch.company; add course__company guard
        qs = super().get_queryset(request)
        if not request.user.is_superuser and getattr(request.user, 'company_id', None):
            qs = qs.filter(course__company=request.user.company)
        return qs

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if not request.user.is_superuser:
            if db_field.name == "course":
                kwargs["queryset"] = Course.objects.filter(company=request.user.company)

        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if not request.user.is_superuser:
            if db_field.name == "instructors":
                kwargs["queryset"] = CustomUser.objects.filter(
                    company=request.user.company,
                    role='instructor'
                )

        return super().formfield_for_manytomany(db_field, request, **kwargs)


class EnrollmentAdmin(ModelAdmin):
    list_display = [
        'student', 'batch', 'status', 'get_status_badge',
        'payment_status', 'course_fee', 'applied_discount', 'total_due_display',
        'request_date', 'approval_date', 'approved_by', 'certificate_allowed', 'certificate_given', 'certificate_link',
    ]
    list_editable = ['status', 'certificate_given', 'payment_status']
    list_filter = ['status', 'payment_status', 'certificate_allowed', 'certificate_given', 'request_date']
    search_fields = ['student__username', 'student__email', 'batch__name', 'certificate_number']
    readonly_fields = ['request_date', 'approval_date', 'course_fee', 'total_due', 'certificate_uuid', 'certificate_number', 'certificate_pdf', 'certificate_generated_at', 'certificate_preview_link']
    fieldsets = (
        ('Enrollment Info', {'fields': ('student', 'batch')}),
        ('Payment', {'fields': ('course_fee', 'coupon', 'applied_discount', 'total_due', 'payment_status', 'payment_reference')}),
        ('Status', {'fields': ('status', 'approval_date', 'approved_by')}),
        ('Rejection', {'fields': ('rejection_reason',)}),
        ('Certificate', {'fields': ('certificate_allowed', 'certificate_given', 'certificate_uuid', 'certificate_number', 'certificate_pdf', 'certificate_generated_at', 'certificate_preview_link')}),
        ('Audit', {'fields': ('request_date',), 'classes': ('collapse',)}),
    )
    
    actions = ['approve_enrollment', 'reject_enrollment', 'allow_certificate', 'disable_certificate', 'generate_certificate_now', 'clear_certificate']

    def _get_company_admin_email(self, company):
        admin_email = getattr(company, 'contact_email', None)
        if admin_email:
            return admin_email
        admin_user = company.users.filter(role='admin').exclude(email='').first()
        if admin_user:
            return admin_user.email
        return None

    def _send_approval_email(self, request, enrollment):
        student_email = getattr(enrollment.student, 'email', None)
        if not student_email:
            return

        company = enrollment.batch.company
        admin_email = self._get_company_admin_email(company)
        protocol = 'https' if request.is_secure() else 'http'
        domain = request.get_host()
        context = {
            'student_name': enrollment.student.get_full_name() or enrollment.student.username,
            'course_name': enrollment.batch.course.title,
            'batch_name': enrollment.batch.name,
            'approval_date': timezone.now().strftime("%B %d, %Y"),
            'dashboard_url': f"{protocol}://{domain}{reverse('enrollments:my_enrollments')}",
            'company_name': company.name,
            'current_year': timezone.now().year,
        }

        send_company_email(
            company=company,
            subject=f"Enrollment Approved - {enrollment.batch.course.title}",
            template_name='emails/enrollment_approved_student.html',
            context=context,
            recipient_list=[student_email],
            cc_list=[admin_email] if admin_email else None,
        )

    def save_model(self, request, obj, form, change):
        # Auto-fill approver metadata when enrollment is marked approved.
        if obj.status == 'approved':
            if not obj.approval_date:
                obj.approval_date = timezone.now()
            if not obj.approved_by_id:
                obj.approved_by = request.user
        super().save_model(request, obj, form, change)
    
    def has_add_permission(self, request):
        """Only superusers can add enrollments."""
        return request.user.is_superuser

    def get_readonly_fields(self, request, obj=None):
        """course_fee and total_due are always readonly (auto-computed).
        company admins additionally cannot change student or batch."""
        readonly = list(super().get_readonly_fields(request, obj))
        for f in ('course_fee', 'total_due'):
            if f not in readonly:
                readonly.append(f)
        if not request.user.is_superuser:
            for f in ('student', 'batch'):
                if f not in readonly:
                    readonly.append(f)
        return readonly

    def get_list_filter(self, request):
        # Base filters always available
        base_filters = ['status', 'payment_status', 'request_date']
        # Include custom Batch and Course filters for scoping
        return base_filters + [BatchFilter, CourseIDFilter]
    
    def total_due_display(self, obj):
        from decimal import Decimal
        if obj.payment_status in ('paid', 'waived'):
            return format_html('<span style="color:#10b981;font-weight:700;">0.00 ✓</span>')
        color = '#dc3545' if obj.total_due > Decimal('0') else '#10b981'
        return format_html(
            '<span style="font-weight:700;color:{}">{}</span>', color, obj.total_due
        )
    total_due_display.short_description = 'Balance Due'
    total_due_display.admin_order_field = 'total_due'

    def get_status_badge(self, obj):
        colors = {'pending': '#FFA500', 'approved': '#28a745', 'rejected': '#dc3545'}
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display()
        )
    get_status_badge.short_description = 'Status'
    
    def approve_enrollment(self, request, queryset):
        from django.utils import timezone
        now = timezone.now()
        updated = 0
        for obj in queryset.filter(status='pending'):
            obj.status = 'approved'
            obj.approved_by = request.user
            obj.approval_date = now
            # Auto-waive if no fee; leave payment_status untouched if already paid
            if obj.total_due == 0 and obj.payment_status == 'unpaid':
                obj.payment_status = 'waived'
            obj.save()
            self._send_approval_email(request, obj)
            updated += 1
        self.message_user(request, f'{updated} enrollment(s) approved.')
    approve_enrollment.short_description = 'Approve selected enrollments'

    def reject_enrollment(self, request, queryset):
        count = queryset.filter(status='pending').update(status='rejected')
        self.message_user(request, f'{count} enrollment(s) rejected.')
    reject_enrollment.short_description = 'Reject selected enrollments'

    def get_queryset(self, request):
        qs = super().get_queryset(request)

        if request.user.is_superuser:
            return qs

        return qs.filter(batch__company=request.user.company)

    def lookup_allowed(self, lookup, value):
        # Allow admin filtering by related batch->course lookup for company scoping
        # Django by default may disallow nested lookups like 'batch__course__id'
        if lookup and lookup.startswith('batch__course__'):
            return True
        return super().lookup_allowed(lookup, value)

    def certificate_link(self, obj):
        if not obj.certificate_allowed:
            return '-'

        url = reverse(
            'enrollments:certificate_public',
            kwargs={'uuid': obj.certificate_uuid}
        )

        return format_html('<a href="{}" target="_blank">View</a>', url)

    certificate_link.short_description = 'Certificate'

    def certificate_preview_link(self, obj):
        if not obj.pk:
            return '-'

        if not obj.certificate_allowed:
            return 'Certificate not allowed yet.'

        url = reverse(
            'enrollments:certificate_public',
            kwargs={'uuid': obj.certificate_uuid}
        )

        return format_html('<a href="{}" target="_blank">Open public certificate page</a>', url)

    certificate_preview_link.short_description = 'Certificate Public Link'

    @admin.action(description='Allow certificate for selected enrollments')
    def allow_certificate(self, request, queryset):
        updated = queryset.filter(status='approved').update(certificate_allowed=True)
        self.message_user(
            request,
            f'Certificate allowed for {updated} approved enrollment(s).',
            messages.SUCCESS
        )

    @admin.action(description='Disable certificate for selected enrollments')
    def disable_certificate(self, request, queryset):
        updated = queryset.update(certificate_allowed=False)
        self.message_user(
            request,
            f'Certificate disabled for {updated} enrollment(s).',
            messages.WARNING
        )

    @admin.action(description='Generate certificate PDF now')
    def generate_certificate_now(self, request, queryset):
        success = 0
        failed = 0

        for enrollment in queryset.filter(status='approved', certificate_allowed=True):
            try:
                generate_certificate_pdf(enrollment, request=request, force=False)
                success += 1
            except Exception as e:
                failed += 1
                self.message_user(
                    request,
                    f'Failed for enrollment #{enrollment.id}: {e}',
                    messages.ERROR
                )

        self.message_user(
            request,
            f'Generated {success} certificate(s). Failed: {failed}.',
            messages.SUCCESS if failed == 0 else messages.WARNING
        )

    @admin.action(description='Clear certificate for regeneration')
    def clear_certificate(self, request, queryset):
        """Clear generated certificate PDF and metadata to allow student to regenerate."""
        updated = 0
        for enrollment in queryset:
            enrollment.certificate_pdf = None
            enrollment.certificate_generated_at = None
            enrollment.certificate_given = False
            # Optionally reset per-enrollment certificate data fields so they're auto-filled fresh
            enrollment.certificate_registration_no = None
            enrollment.certificate_total_months = None
            enrollment.certificate_start_period = None
            enrollment.certificate_end_period = None
            enrollment.save()
            updated += 1
        
        self.message_user(
            request,
            f'Cleared certificate for {updated} enrollment(s). Student can now regenerate.',
            messages.SUCCESS
        )

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<int:enrollment_id>/change-status/<str:status>/', self.admin_site.admin_view(self.change_status_view), name='enrollments_enrollment_change_status'),
        ]
        return custom_urls + urls

    def change_status_view(self, request, enrollment_id, status):
        obj = self.get_queryset(request).filter(pk=enrollment_id).first()
        if not obj:
            self.message_user(request, 'Enrollment not found or access denied.', level=messages.ERROR)
            return redirect(request.META.get('HTTP_REFERER', reverse('admin:enrollments_enrollment_changelist')))

        if status not in dict(obj.ENROLLMENT_STATUS):
            self.message_user(request, f'Invalid status: {status}', level=messages.ERROR)
            return redirect(request.META.get('HTTP_REFERER', reverse('admin:enrollments_enrollment_changelist')))

        obj.status = status
        if status == 'approved':
            obj.approved_by = request.user
            obj.approval_date = timezone.now()
            if obj.total_due == 0 and obj.payment_status == 'unpaid':
                obj.payment_status = 'waived'
        obj.save()
        if status == 'approved':
            self._send_approval_email(request, obj)
        self.message_user(request, f'Enrollment {obj} set to {obj.get_status_display()}.')
        return redirect(request.META.get('HTTP_REFERER', reverse('admin:enrollments_enrollment_changelist')))

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if not request.user.is_superuser:
            if db_field.name == 'batch':
                kwargs['queryset'] = Batch.objects.filter(company=request.user.company)

            if db_field.name == 'student':
                # Students are global learners
                kwargs['queryset'] = CustomUser.objects.filter(role='student')

            if db_field.name == 'approved_by':
                kwargs['queryset'] = CustomUser.objects.filter(company=request.user.company)

            if db_field.name == 'coupon':
                kwargs['queryset'] = Coupon.objects.filter(company=request.user.company)

        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def quick_actions(self, obj):
        approve_url = reverse('admin:enrollments_enrollment_change_status', args=[obj.pk, 'approved'])
        reject_url = reverse('admin:enrollments_enrollment_change_status', args=[obj.pk, 'rejected'])
        return format_html(
            '<a class="button" href="{}" style="background:#28a745;color:#fff;margin-right:6px;padding:4px 8px;border-radius:4px;">Approve</a>'
            '<a class="button" href="{}" style="background:#dc3545;color:#fff;padding:4px 8px;border-radius:4px;">Reject</a>',
            approve_url,
            reject_url,
        )
    quick_actions.short_description = 'Quick Actions'


admin.site.register(Batch, BatchAdmin)
admin.site.register(Enrollment, EnrollmentAdmin)


@admin.register(Coupon)
class CouponAdmin(CompanyAdminMixin, ModelAdmin):
    list_display = ['code', 'company', 'batch', 'discount_type', 'discount_amount', 'start_date', 'end_date', 'used_count', 'is_active']
    list_filter = ['discount_type', 'is_active', 'start_date', 'end_date']
    search_fields = ['code', 'company__name', 'batch__name']
    readonly_fields = ['used_count']
    
    def has_delete_permission(self, request, obj=None):
        # Prevent deletion if coupon has been used in any enrollments
        if obj and obj.used_count > 0:
            return False
        return super().has_delete_permission(request, obj)
    
    def get_list_filter(self, request):
        if request.user.is_superuser:
            return ['company', 'discount_type', 'is_active', 'start_date']
        return ['discount_type', 'is_active', 'start_date']
        
    def save_model(self, request, obj, form, change):
        if not request.user.is_superuser and not getattr(obj, 'company_id', None):
            obj.company = request.user.company
        super().save_model(request, obj, form, change)
        
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not request.user.is_superuser and getattr(request.user, 'company_id', None):
            qs = qs.filter(company=request.user.company)
        return qs

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if not request.user.is_superuser:
            if db_field.name == 'batch':
                kwargs['queryset'] = Batch.objects.filter(company=request.user.company)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
# Sales Records  (virtual – backed by the enrollments_salesrecord DB view)
# ─────────────────────────────────────────────────────────────────────────────

class CompanySalesFilter(admin.SimpleListFilter):
    """Allow superusers to slice the sales table by company."""

    title = 'Company'
    parameter_name = 'company_id'

    def lookups(self, request, model_admin):
        from accounts.models import Company
        return list(Company.objects.values_list('id', 'name').order_by('name'))

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(batch__company_id=self.value())
        return queryset


class StatusSalesFilter(admin.SimpleListFilter):
    """Filter by enrollment status."""

    title = 'Status'
    parameter_name = 'status'

    def lookups(self, request, model_admin):
        return [
            ('pending',  'Pending'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
        ]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(status=self.value())
        return queryset


@admin.register(SalesRecord)
class SalesRecordAdmin(ModelAdmin):
    """
    Read-only admin view over the enrollments_salesrecord database view.
    Provides:
      • Analytics dashboard (totals, revenue, monthly breakdown)
      • CSV export of the current filtered queryset
      • CSV bulk-import to create real Enrollment records
      • Full company scoping: admins see only their own data
    """

    # ── list ──────────────────────────────────────────────────────────────────
    list_display = [
        'student_name', 'student_email', 'course_title', 'batch_name',
        'status_badge', 'course_fee_display', 'discount_display',
        'total_due_display', 'payment_status_badge',
        'request_date_fmt', 'approval_date_fmt', 'cert_status',
    ]
    # search_fields must use real DB paths (annotations can't be searched by admin)
    search_fields = [
        'student__first_name', 'student__last_name', 'student__username',
        'student__email', 'batch__course__title', 'batch__name',
    ]
    ordering = ['-request_date']
    actions = ['export_as_csv']

    def get_list_filter(self, request):
        if request.user.is_superuser:
            return [CompanySalesFilter, StatusSalesFilter, 'payment_status', 'request_date']
        return [StatusSalesFilter, 'payment_status', 'request_date']

    # ── permissions (read-only view) ──────────────────────────────────────────
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    # ── queryset scoping ──────────────────────────────────────────────────────
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        company_id = getattr(request.user, 'company_id', None)
        if not company_id:
            return qs.none()
        return qs.filter(batch__company_id=company_id)

    # ── display helpers ───────────────────────────────────────────────────────
    def status_badge(self, obj):
        palette = {
            'pending':  ('#f59e0b', '#fff8e1'),
            'approved': ('#10b981', '#ecfdf5'),
            'rejected': ('#ef4444', '#fef2f2'),
        }
        bg, text_bg = palette.get(obj.status, ('#6b7280', '#f9fafb'))
        return format_html(
            '<span style="background:{};color:#fff;padding:3px 12px;'
            'border-radius:12px;font-size:11px;font-weight:700;'
            'letter-spacing:.4px;">{}</span>',
            bg, obj.status.upper(),
        )
    status_badge.short_description = 'Status'
    status_badge.admin_order_field = 'status'

    def course_fee_display(self, obj):
        return format_html(
            '<span style="color:#6b7280;">{}</span>', obj.course_fee
        )
    course_fee_display.short_description = 'List Fee'
    course_fee_display.admin_order_field = 'course_fee'

    def discount_display(self, obj):
        if obj.applied_discount:
            return format_html(
                '<span style="color:#f59e0b;">- {}</span>', obj.applied_discount
            )
        return format_html('<span style="color:#d1d5db;">—</span>')
    discount_display.short_description = 'Discount'
    discount_display.admin_order_field = 'applied_discount'

    def total_due_display(self, obj):
        color = '#10b981' if obj.payment_status == 'paid' else '#1d4ed8'
        return format_html(
            '<span style="font-weight:700;color:{};">{}</span>', color, obj.total_due
        )
    total_due_display.short_description = 'Total Due'
    total_due_display.admin_order_field = 'total_due'

    def payment_status_badge(self, obj):
        palette = {
            'unpaid':  '#f59e0b',
            'paid':    '#10b981',
            'waived':  '#8b5cf6',
        }
        color = palette.get(obj.payment_status, '#6b7280')
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 10px;'
            'border-radius:10px;font-size:11px;font-weight:700;">{}</span>',
            color, obj.payment_status.upper(),
        )
    payment_status_badge.short_description = 'Payment'
    payment_status_badge.admin_order_field = 'payment_status'

    def request_date_fmt(self, obj):
        if obj.request_date:
            return obj.request_date.strftime('%d %b %Y')
        return '—'
    request_date_fmt.short_description = 'Enrolled'
    request_date_fmt.admin_order_field = 'request_date'

    def approval_date_fmt(self, obj):
        if obj.approval_date:
            return obj.approval_date.strftime('%d %b %Y')
        return format_html('<span style="color:#9ca3af;">—</span>')
    approval_date_fmt.short_description = 'Approved'
    approval_date_fmt.admin_order_field = 'approval_date'

    def cert_status(self, obj):
        if obj.certificate_given:
            return format_html(
                '<span style="color:#10b981;font-weight:700;">&#10003; Issued</span>'
            )
        return format_html('<span style="color:#d1d5db;">&#8212;</span>')
    cert_status.short_description = 'Certificate'
    cert_status.admin_order_field = 'certificate_given'

    # ── analytics: inject stats into changelist context ───────────────────────
    def changelist_view(self, request, extra_context=None):
        qs = self.get_queryset(request)

        # Apply any active filters so stats match what's visible
        cl_filters = {}
        if request.GET.get('status'):
            cl_filters['status'] = request.GET['status']
        if request.GET.get('company_id') and request.user.is_superuser:
            cl_filters['company_id'] = request.GET['company_id']
        if cl_filters:
            qs = qs.filter(**cl_filters)

        now = timezone.now()
        stats = qs.aggregate(
            total=Count('id'),
            approved=Count('id', filter=Q(status='approved')),
            pending=Count('id',  filter=Q(status='pending')),
            rejected=Count('id', filter=Q(status='rejected')),
            # Revenue = sum of total_due for paid enrollments (actual collected)
            revenue=Sum('total_due', filter=Q(status='approved', payment_status='paid')),
            # Pipeline = sum of total_due for approved-but-unpaid (money expected)
            pipeline=Sum('total_due', filter=Q(status='approved', payment_status='unpaid')),
        )
        monthly = qs.filter(
            request_date__year=now.year,
            request_date__month=now.month,
        ).aggregate(
            monthly_count=Count('id'),
            monthly_revenue=Sum('total_due', filter=Q(status='approved', payment_status='paid')),
        )

        import_url = reverse('admin:enrollments_salesrecord_import_csv')

        extra_context = extra_context or {}
        extra_context.update({
            'sales_stats': {
                'total':           stats['total'] or 0,
                'approved':        stats['approved'] or 0,
                'pending':         stats['pending'] or 0,
                'rejected':        stats['rejected'] or 0,
                'revenue':         stats['revenue'] or 0,
                'pipeline':        stats.get('pipeline') or 0,
                'monthly_count':   monthly['monthly_count'] or 0,
                'monthly_revenue': monthly['monthly_revenue'] or 0,
                'month_label':     now.strftime('%B %Y'),
            },
            'import_url': import_url,
        })
        return super().changelist_view(request, extra_context=extra_context)

    # ── CSV export action ─────────────────────────────────────────────────────
    def export_as_csv(self, request, queryset):
        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = (
            f'attachment; filename="sales_report_{timestamp}.csv"'
        )
        writer = csv.writer(response)
        writer.writerow([
            'ID', 'Student Name', 'Student Email',
            'Course', 'List Price', 'Batch', 'Company',
            'Enrollment Status', 'Coupon', 'Course Fee', 'Discount', 'Total Due', 'Payment Status',
            'Enrolled On', 'Approved On', 'Certificate Issued',
        ])
        for obj in queryset:
            writer.writerow([
                obj.pk,
                obj.student_name,
                obj.student_email,
                obj.course_title,
                obj.batch.course.price,
                obj.batch_name,
                obj.company_name,
                obj.status,
                obj.coupon.code if obj.coupon_id else '',
                obj.course_fee,
                obj.applied_discount,
                obj.total_due,
                obj.payment_status,
                obj.request_date.strftime('%Y-%m-%d %H:%M') if obj.request_date else '',
                obj.approval_date.strftime('%Y-%m-%d %H:%M') if obj.approval_date else '',
                'Yes' if obj.certificate_given else 'No',
            ])
        self.message_user(
            request,
            f'{queryset.count()} record(s) exported successfully.',
            messages.SUCCESS,
        )
        return response
    export_as_csv.short_description = '📥 Export selected records as CSV'

    # ── CSV import custom view ────────────────────────────────────────────────
    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                'import-csv/',
                self.admin_site.admin_view(self.import_csv_view),
                name='enrollments_salesrecord_import_csv',
            ),
        ]
        return custom + urls

    def import_csv_view(self, request):
        """
        Accept a CSV with columns:
            student_email, batch_id, status (optional – defaults to 'pending')

        Creates Enrollment records; skips duplicates (student+batch unique
        together) and rows where the batch doesn't belong to the admin's
        company.
        """
        ctx = dict(self.admin_site.each_context(request))
        ctx['title'] = 'Import Enrollments via CSV'
        ctx['opts'] = self.model._meta
        ctx['media'] = self.media

        if request.method != 'POST':
            return render(
                request,
                'admin/enrollments/salesrecord/import_csv.html',
                ctx,
            )

        csv_file = request.FILES.get('csv_file')
        if not csv_file:
            self.message_user(request, 'No file uploaded.', messages.ERROR)
            return redirect(reverse('admin:enrollments_salesrecord_import_csv'))

        if not csv_file.name.endswith('.csv'):
            self.message_user(
                request, 'Please upload a valid .csv file.', messages.ERROR
            )
            return redirect(reverse('admin:enrollments_salesrecord_import_csv'))

        try:
            data = csv_file.read().decode('utf-8-sig')
            reader = csv.DictReader(io.StringIO(data))
        except Exception:
            self.message_user(
                request, 'Could not parse the CSV file.', messages.ERROR
            )
            return redirect(reverse('admin:enrollments_salesrecord_import_csv'))

        required_cols = {'student_email', 'batch_id'}
        if not required_cols.issubset({c.strip().lower() for c in (reader.fieldnames or [])}):
            self.message_user(
                request,
                'CSV must contain at minimum: student_email, batch_id',
                messages.ERROR,
            )
            return redirect(reverse('admin:enrollments_salesrecord_import_csv'))

        created = skipped = errors = 0
        company_id = getattr(request.user, 'company_id', None)

        for row_num, row in enumerate(reader, start=2):
            email = row.get('student_email', '').strip()
            batch_id_raw = row.get('batch_id', '').strip()
            status = row.get('status', 'pending').strip().lower()

            if status not in ('pending', 'approved', 'rejected'):
                status = 'pending'

            if not email or not batch_id_raw:
                errors += 1
                continue

            try:
                batch_id = int(batch_id_raw)
            except ValueError:
                errors += 1
                continue

            # company scoping – non-superusers can only import into their own batches
            batch_qs = Batch.objects.filter(pk=batch_id)
            if not request.user.is_superuser and company_id:
                batch_qs = batch_qs.filter(company_id=company_id)

            batch = batch_qs.first()
            if not batch:
                errors += 1
                continue

            student = CustomUser.objects.filter(
                email__iexact=email, role='student'
            ).first()
            if not student:
                errors += 1
                continue

            _, was_created = Enrollment.objects.get_or_create(
                student=student,
                batch=batch,
                defaults={'status': status},
            )
            if was_created:
                created += 1
            else:
                skipped += 1

        self.message_user(
            request,
            f'Import complete — Created: {created}, Skipped (duplicates): {skipped}, Errors: {errors}.',
            messages.SUCCESS if errors == 0 else messages.WARNING,
        )
        return redirect(reverse('admin:enrollments_salesrecord_changelist'))

