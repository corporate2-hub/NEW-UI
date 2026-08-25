from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import AdminPasswordChangeForm
from django.utils.html import format_html
from unfold.admin import ModelAdmin
from django.conf import settings
from django.core.exceptions import PermissionDenied
from .models import CustomUser, PasswordResetToken, Company, SMTPSettings
from .admin_mixins import CompanyAdminMixin

@admin.register(CustomUser)
class CustomUserAdmin(CompanyAdminMixin, BaseUserAdmin, ModelAdmin):
    """Custom user admin with role field and company scoping."""

    list_display = ['username', 'email', 'get_full_name', 'role', 'company', 'is_verified', 'date_joined']
    list_filter = BaseUserAdmin.list_filter + ('role', 'company', 'is_verified', 'date_joined')
    list_editable = ['is_verified']
    search_fields = ['username', 'email', 'first_name', 'last_name', 'phone']
    
    # Include the method name in readonly_fields
    readonly_fields = ['last_login', 'date_joined', 'password_change_link']

    change_password_form = AdminPasswordChangeForm

    fieldsets = (
        (None, {'fields': ('username',)}), # REMOVED 'password' to hide the broken text/link from your screenshot
        ('Personal info', {'fields': ('first_name', 'last_name', 'email')}),
        ('Authentication', {'fields': ('password_change_link',)}), # Your new working button
        ('Custom Fields', {'fields': ('role', 'company', 'phone', 'bio', 'profile_image', 'is_verified')}),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
            'classes': ('collapse',),
        }),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )

    def password_change_link(self, obj):
        if not obj.pk:
            return "-"
        
        # This tells the browser: Go back one level from 'change/' 
        # and go into 'password/'
        url = "../password/"
        
        return format_html(
            '<a class="bg-primary-600 font-semibold py-2 px-4 rounded text-white hover:bg-primary-700 transition-all inline-block shadow-sm" href="{}">'
            'Change Password'
            '</a>',
            url
        )

    password_change_link.short_description = "Password Action"

    def get_queryset(self, request):
        # Bypass CompanyAdminMixin.get_queryset (which hard-filters by company FK)
        # so we can include students whose company is NULL but who are enrolled
        # in this company's batches.
        qs = BaseUserAdmin.get_queryset(self, request)
        if request.user.is_superuser:
            return qs
        from enrollments.models import Enrollment
        # Staff/admins/instructors directly bound to this company
        company_users = qs.filter(company=request.user.company)
        # Students (company=None) enrolled in any of this company's batches
        enrolled_student_ids = Enrollment.objects.filter(
            batch__company=request.user.company,
        ).values_list('student_id', flat=True)
        enrolled_students = qs.filter(id__in=enrolled_student_ids)
        return (company_users | enrolled_students).distinct()

    def save_model(self, request, obj, form, change):
        # Always bind created/edited users to the current user's company for non-superusers
        if not request.user.is_superuser:
            obj.company = request.user.company
            # Prevent company admins from editing existing student users
            if change and getattr(obj, 'role', None) == 'student':
                from django.contrib import messages
                messages.error(request, "You are not allowed to modify student users.")
                raise PermissionDenied("Not allowed to modify student users.")
            # If creating a user and role is left as 'student' (model default), force 'instructor'
            if not change and getattr(obj, 'role', None) == 'student':
                obj.role = 'instructor'
        super().save_model(request, obj, form, change)

    def formfield_for_choice_field(self, db_field, request, **kwargs):
        # Limit role choices for non-superusers so they cannot create students
        if db_field.name == 'role' and not request.user.is_superuser:
            # Company admins may create `instructor` users; disallow `student` and `admin` roles here.
            kwargs['choices'] = [c for c in db_field.choices if c[0] == 'instructor']
        return super().formfield_for_choice_field(db_field, request, **kwargs)

    def get_changeform_initial_data(self, request):
        initial = super().get_changeform_initial_data(request)
        if not request.user.is_superuser:
            initial.setdefault('role', 'instructor')
        return initial

    def has_change_permission(self, request, obj=None):
        # Allow listing/change view for non-superusers, but prevent editing individual student objects
        if request.user.is_superuser:
            return True
        if obj is None:
            return True
        if getattr(obj, 'role', None) == 'student':
            return False
        return obj.company_id == request.user.company_id

    def has_delete_permission(self, request, obj=None):
        # Prevent non-superusers from deleting student users; allow deleting other company users
        if request.user.is_superuser:
            return True
        if obj is None:
            return True
        if getattr(obj, 'role', None) == 'student':
            return False
        return obj.company_id == request.user.company_id

    def has_add_permission(self, request):
        # Allow superusers. For company staff, allow adding users (but role choices exclude students).
        if request.user.is_superuser:
            return True
        # Only allow staff users who belong to a company to add users
        return bool(request.user.is_staff and getattr(request.user, 'company_id', None))

    def has_module_permission(self, request):
        # Ensure company staff can see the Users section in the admin index
        return request.user.is_staff or request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        # Allow viewing the user list for company staff; prevent viewing individual student objects
        if request.user.is_superuser:
            return True
        if obj is None:
            return bool(request.user.is_staff and getattr(request.user, 'company_id', None))
        if getattr(obj, 'role', None) == 'student':
            return False
        return obj.company_id == request.user.company_id

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        if 'password_change_link' not in readonly:
            readonly.append('password_change_link')

        if not request.user.is_superuser:
            if 'company' not in readonly:
                readonly.append('company')
            if 'is_superuser' not in readonly:
                readonly.append('is_superuser')
        return readonly

# --- Remaining Models ---

@admin.register(PasswordResetToken)
class PasswordResetTokenAdmin(ModelAdmin):
    list_display = ['user', 'created_at', 'expires_at', 'is_used']
    list_filter = ['is_used', 'created_at']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['token', 'created_at']

@admin.register(Company)
class CompanyAdmin(ModelAdmin):
    list_display = ['name', 'slug', 'domain', 'is_active', 'allow_i2i', 'created_at']
    readonly_fields = ['created_at', 'updated_at']

    # All fieldsets — visibility is filtered per role in get_fieldsets()
    _all_fieldsets = (
        ('Basic Info', {
            'fields': ('name', 'slug', 'domain', 'is_active'),
            'description': 'Core identity settings — only editable by superusers.',
        }),
        ('Features', {
            'fields': ('allow_i2i',),
            'description': 'Superuser-controlled feature flags for this company.',
        }),
        ('Branding', {
            'fields': ('logo', 'favicon', 'partner_logo', 'feature_image'),
        }),
        ('Hero Section', {
            'fields': (
                'hero_badge',
                'hero_title', 'hero_subtitle',
                'hero_primary_text', 'hero_primary_link',
                'hero_secondary_text', 'hero_secondary_link',
            ),
        }),
        ('Stats', {
            'fields': ('total_students', 'total_batches', 'total_mentors'),
        }),
        ('Featured Section', {
            'fields': ('featured_title', 'featured_subtitle'),
        }),
        ('CTA Section', {
            'fields': ('cta_title', 'cta_subtitle', 'cta_phone'),
        }),
        ('Footer & Contact', {
            'fields': ('footer_text', 'contact_phone', 'contact_email'),
        }),
        ('Social Links', {
            'fields': ('facebook_url', 'x_url', 'linkedin_url', 'youtube_url'),
        }),
        ('SEO & Open Graph', {
            'fields': (
                'meta_title', 'meta_description', 'meta_keywords',
                'og_title', 'og_description', 'og_image',
            ),
            'classes': ('collapse',),
        }),
        ('SSL Commerce', {
            'fields': ('ssl_commerce_key', 'ssl_commerce_secret', 'ssl_commerce_url'),
            'classes': ('collapse',),
        }),
        ('Scripts & Custom CSS', {
            'fields': ('custom_css', 'header_scripts', 'footer_scripts'),
            'classes': ('collapse',),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    # Fieldsets company admins are NOT allowed to see or change
    _superuser_only_sections = {'Basic Info', 'Features'}

    def get_fieldsets(self, request, obj=None):
        if request.user.is_superuser:
            return self._all_fieldsets
        return [fs for fs in self._all_fieldsets if fs[0] not in self._superuser_only_sections]

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        if not request.user.is_superuser:
            for field in ('name', 'slug', 'domain', 'is_active', 'allow_i2i'):
                if field not in readonly:
                    readonly.append(field)
        return readonly

    def has_module_permission(self, request):
        return request.user.is_staff or request.user.is_superuser

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(id=request.user.company_id)

    def has_view_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        if obj is None:
            return True
        return obj.id == request.user.company_id

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        if obj is None:
            return True
        return obj.id == request.user.company_id

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

from django.contrib import messages
from enrollments.services.email_service import send_company_email

@admin.register(SMTPSettings)
class SMTPSettingsAdmin(CompanyAdminMixin, ModelAdmin):
    actions = ['send_test_email']
    list_display = ['company', 'email_host', 'email_port', 'email_host_user', 'email_use_tls', 'email_use_ssl']
    list_filter = ['email_use_tls', 'email_use_ssl']
    search_fields = ['company__name', 'email_host_user']

    def send_test_email(self, request, queryset):
        """Admin action to send a test email using the selected SMTP settings."""
        for smtp_setting in queryset:
            company = smtp_setting.company
            if not company:
                self.message_user(request, "SMTP setting has no associated company.", level=messages.ERROR)
                continue
            # Use the logged‑in user’s email if it exists; otherwise fall back to the default FROM email.
            if getattr(request.user, "email", None):
                recipient = [request.user.email]
            elif getattr(settings, "DEFAULT_FROM_EMAIL", None):
                recipient = [settings.DEFAULT_FROM_EMAIL]
            else:
                recipient = []
            if not recipient:
                self.message_user(request, "No recipient email available for the test email.", level=messages.ERROR)
                continue
            # Email details
            subject = "Test SMTP Settings"
            template_name = "emails/enrollment_request_admin.html"
            context = {"company": company}
            
            from django.core.mail import get_connection, EmailMultiAlternatives
            from django.template.loader import render_to_string
            try:
                connection = get_connection(
                    backend='django.core.mail.backends.smtp.EmailBackend',
                    host=smtp_setting.email_host,
                    port=smtp_setting.email_port,
                    username=smtp_setting.email_host_user,
                    password=smtp_setting.email_host_password,
                    use_tls=smtp_setting.email_use_tls,
                    use_ssl=smtp_setting.email_use_ssl,
                    fail_silently=False,
                )
                html_content = render_to_string(template_name, context)
                from_email = smtp_setting.default_from_email or smtp_setting.email_host_user or getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@example.com')
                
                msg = EmailMultiAlternatives(
                    subject=subject,
                    body="Please view this email in a client that supports HTML.",
                    from_email=from_email,
                    to=recipient,
                    connection=connection
                )
                msg.attach_alternative(html_content, "text/html")
                msg.send()
                self.message_user(request, f"Test email sent successfully for {company.name}.", level=messages.SUCCESS)
            except Exception as e:
                self.message_user(request, f"SMTP Connection failed for {company.name}. Error: {str(e)}", level=messages.ERROR)

    send_test_email.short_description = "Send test email using selected SMTP settings"
    
    def has_module_permission(self, request):
        return request.user.is_staff or request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        if obj is None:
            return True
        return obj.company_id == request.user.company_id

    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        if obj is None:
            return True
        return obj.company_id == request.user.company_id

    # Removed manual get_readonly_fields as CompanyAdminMixin handles it.
