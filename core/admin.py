from django.contrib import admin
from django.db.models import Sum, Count, Q
from django.utils import timezone
from unfold.admin import ModelAdmin
from accounts.admin_mixins import CompanyAdminMixin
from .models import Category
from django import forms
from django.db import models
from django.utils.text import slugify
from django.utils.crypto import get_random_string
from unfold.contrib.forms.widgets import WysiwygWidget
from .widgets import FontAwesomeIconPickerWidget


class CategoryAdmin(CompanyAdminMixin, ModelAdmin):
    list_display = ['name', 'company', 'slug', 'created_at']
    list_filter = ['company', 'created_at']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['created_at', 'updated_at']
    formfield_overrides = {
        models.TextField: {
            'widget': WysiwygWidget,
        }
    }
    fieldsets = (
        ('Basic Info', {'fields': ('company', 'name', 'slug')}),
        ('Details', {'fields': ('description', 'icon')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )

    from django import forms as _forms

    class CategoryAdminForm(_forms.ModelForm):
        class Meta:
            model = Category
            fields = "__all__"
            widgets = {
                'icon': FontAwesomeIconPickerWidget(),
            }

    form = CategoryAdminForm

    def get_list_filter(self, request):
        if request.user.is_superuser:
            return ['company', 'created_at']
        return ['created_at']

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        return super().formfield_for_dbfield(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        # Ensure slug exists and is unique within the company scope.
        if not obj.slug and getattr(obj, 'name', None):
            base = slugify(obj.name)
            slug = base
            # Check for conflicts within the same company
            conflict_qs = Category.objects.filter(slug=slug)
            if getattr(request.user, 'company_id', None):
                conflict_qs = conflict_qs.filter(company=request.user.company)

            while conflict_qs.exists():
                slug = f"{base}-{get_random_string(4)}"
                conflict_qs = Category.objects.filter(slug=slug)
                if getattr(request.user, 'company_id', None):
                    conflict_qs = conflict_qs.filter(company=request.user.company)

            obj.slug = slug

        super().save_model(request, obj, form, change)


admin.site.register(Category, CategoryAdmin)

# Admin branding
admin.site.site_header = 'Skill Jobs Training SaaS'
admin.site.site_title = 'Skill Jobs Training SaaS'
admin.site.index_title = 'Dashboard'


# ─────────────────────────────────────────────────────────────────────────────
# Patch each_context – company-specific title + dashboard stats
# ─────────────────────────────────────────────────────────────────────────────

_original_each_context = admin.site.each_context


def _build_dashboard_stats(request):
    """
    Aggregate stats from all apps, scoped to the user's company when needed.
    Returns a dict consumed by templates/admin/index.html.
    """
    from accounts.models import CustomUser, Company
    from courses.models import Course
    from enrollments.models import Batch, Enrollment
    from classes.models import ClassSession
    from attendance.models import Attendance

    is_super = request.user.is_superuser
    company = getattr(request.user, 'company', None)

    def scoped(qs, company_field='company'):
        if is_super:
            return qs
        if not company:
            return qs.none()
        return qs.filter(**{company_field: company})

    now = timezone.now()

    # ── Users ──────────────────────────────────────────────────────────────
    if is_super:
        total_students    = CustomUser.objects.filter(role='student').count()
        total_instructors = CustomUser.objects.filter(role='instructor').count()
        total_companies   = Company.objects.count()
    else:
        total_students    = CustomUser.objects.filter(
            role='student',
            enrollments__batch__company=company
        ).distinct().count() if company else 0
        total_instructors = CustomUser.objects.filter(
            role='instructor', company=company
        ).count() if company else 0
        total_companies   = None  # hide from non-superusers

    # ── Courses ─────────────────────────────────────────────────────────────
    course_qs          = scoped(Course.objects.all())
    total_courses      = course_qs.count()
    published_courses  = course_qs.filter(status='published').count()
    draft_courses      = course_qs.filter(status='draft').count()

    # ── Batches ─────────────────────────────────────────────────────────────
    batch_qs           = scoped(Batch.objects.all())
    total_batches      = batch_qs.count()
    running_batches    = batch_qs.filter(status='running').count()
    upcoming_batches   = batch_qs.filter(status='upcoming').count()

    # ── Enrollments ─────────────────────────────────────────────────────────
    enroll_qs = Enrollment.objects.all() if is_super else (
        Enrollment.objects.filter(batch__company=company) if company
        else Enrollment.objects.none()
    )
    total_enrollments    = enroll_qs.count()
    approved_enrollments = enroll_qs.filter(status='approved').count()
    pending_enrollments  = enroll_qs.filter(status='pending').count()

    # ── Revenue ─────────────────────────────────────────────────────────────
    rev_qs = enroll_qs.filter(status='approved').select_related('batch__course')
    total_revenue = sum(
        e.batch.course.price for e in rev_qs
    ) if rev_qs.exists() else 0

    monthly_enroll = enroll_qs.filter(
        request_date__year=now.year,
        request_date__month=now.month,
    )
    monthly_enrollments = monthly_enroll.count()
    monthly_revenue = sum(
        e.batch.course.price
        for e in monthly_enroll.filter(status='approved').select_related('batch__course')
    )

    # ── Classes & Attendance ─────────────────────────────────────────────────
    session_qs     = scoped(ClassSession.objects.all(), company_field='batch__company')
    total_sessions = session_qs.count()
    today_sessions = session_qs.filter(scheduled_date=now.date()).count()

    attend_qs      = scoped(Attendance.objects.all(), company_field='class_session__batch__company')
    total_attend   = attend_qs.count()
    present_pct    = 0
    if total_attend:
        present_count = attend_qs.filter(status='present').count()
        present_pct   = round(present_count / total_attend * 100, 1)

    # ── Certificates ────────────────────────────────────────────────────────
    certs_issued = enroll_qs.filter(certificate_given=True).count()

    # ── Exams ───────────────────────────────────────────────────────────────
    from exams.models import Exam, ExamAttempt
    exam_qs = scoped(Exam.objects.all())
    total_exams = exam_qs.count()
    if is_super:
        total_attempts = ExamAttempt.objects.count()
    else:
        total_attempts = ExamAttempt.objects.filter(exam__company=company).count() if company else 0

    return {
        'is_superuser':        is_super,
        'total_companies':     total_companies,
        'total_students':      total_students,
        'total_instructors':   total_instructors,
        'total_courses':       total_courses,
        'published_courses':   published_courses,
        'draft_courses':       draft_courses,
        'total_batches':       total_batches,
        'running_batches':     running_batches,
        'upcoming_batches':    upcoming_batches,
        'total_enrollments':   total_enrollments,
        'approved_enrollments':approved_enrollments,
        'pending_enrollments': pending_enrollments,
        'total_revenue':       total_revenue,
        'monthly_enrollments': monthly_enrollments,
        'monthly_revenue':     monthly_revenue,
        'total_sessions':      total_sessions,
        'today_sessions':      today_sessions,
        'total_attendance':    total_attend,
        'attendance_pct':      present_pct,
        'certs_issued':        certs_issued,
        'total_exams':         total_exams,
        'total_attempts':      total_attempts,
        'month_label':         now.strftime('%B %Y'),
    }


def _each_context_with_company(request):
    context = _original_each_context(request)

    if request.user.is_authenticated:
        user_company = getattr(request.user, 'company', None)
        if user_company:
            context['site_header'] = f'{user_company.name} Admin'
            context['site_title']  = f'{user_company.name} Admin'

        # Inject dashboard stats for the index template
        try:
            context['dashboard_stats'] = _build_dashboard_stats(request)
        except Exception:
            pass  # never break admin for a missing stat

    return context


admin.site.each_context = _each_context_with_company
