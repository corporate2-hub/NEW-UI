from django.contrib import admin
from django.http import HttpResponse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from unfold.admin import ModelAdmin, TabularInline, StackedInline
from django.db import models
from unfold.contrib.forms.widgets import WysiwygWidget

from .models import (
    Course, Section, Lesson,
    Requirement, Benefit, FAQ,
    Tool, CourseAudience, CertificateTemplate
)
from accounts.admin_mixins import CompanyAdminMixin
from accounts.models import CustomUser
from core.models import Category
from .models import CourseMedia
from enrollments.services.certificate_service import generate_sample_certificate_pdf

# =========================
# 🔹 INLINES
# =========================

class LessonInline(TabularInline):
    model = Lesson
    extra = 0
    fields = ('title', 'order', 'is_free', 'video_url')
    ordering = ('order',)
    show_change_link = True


class SectionInline(StackedInline):
    model = Section
    extra = 0
    fields = ('title', 'description', 'image', 'order')
    ordering = ('order',)
    show_change_link = True


class BenefitInline(TabularInline):
    model = Benefit
    extra = 0
    fields = ('title', 'icon', 'order')
    ordering = ('order',)


class RequirementInline(TabularInline):
    model = Requirement
    extra = 0
    fields = ('title', 'order')
    ordering = ('order',)


class FAQInline(StackedInline):
    model = FAQ
    extra = 0
    fields = ('question', 'answer', 'order')
    ordering = ('order',)


class CourseAudienceInline(TabularInline):
    model = CourseAudience
    extra = 0
    fields = ('title', 'icon_bg', 'order')
    ordering = ('order',)


# =========================
# 🔹 COURSE ADMIN
# =========================

@admin.register(Course)
class CourseAdmin(CompanyAdminMixin, ModelAdmin):

    list_display = (
        'title', 'company', 'category', 'instructors_display',
        'level', 'price', 'status',
        'created_at', 'image_preview'
    )

    list_filter = (
        'status', 'level', 'category',
        'created_at'
    )

    def get_list_filter(self, request):
        if request.user.is_superuser:
            return ('company', 'status', 'level', 'category', 'created_at')
        return ('status', 'level', 'category', 'created_at')

    search_fields = (
        'title', 'description',
        'instructors__email'
    )

    readonly_fields = (
        'created_at', 'updated_at', 'image_preview', 'sample_certificate_preview'
    )

    prepopulated_fields = {'slug': ('title',)}

    filter_horizontal = ('tools', 'instructors')

    formfield_overrides = {
        models.TextField: {
            'widget': WysiwygWidget,
        }
    }

    inlines = [
        SectionInline,
        BenefitInline,
        RequirementInline,
        FAQInline,
        CourseAudienceInline,
    ]

    class Media:
        js = ("admin/live_image_preview.js",)

    fieldsets = (
        ('Basic Info', {
            'fields': (
                'title', 'company', 'slug', 'description',
                'category', 'instructors'
            )
        }),

        ('Media', {
            'fields': (
                'banner_image', 'image_preview',
                'sample_certificate', 'sample_certificate_preview'
            )
        }),

        ('Course Details', {
            'fields': (
                'course_type', 'level', 'price',
                'duration_hours', 'tools'
            )
        }),

        ('Schedule', {
            'fields': (
                'registration_start',
                'registration_end',
                'start_date'
            ),
            'classes': ('collapse',)
        }),

        ('Status', {
            'fields': ('status',)
        }),

        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    # ✅ FIXED IMAGE PREVIEW
    def image_preview(self, obj):
        if obj.banner_image:
            return format_html(
                '<img src="{}" width="80" style="border-radius:6px;" />',
                obj.banner_image.url
            )
        return "-"
    image_preview.short_description = "Preview"

    def sample_certificate_preview(self, obj):
        if obj.sample_certificate:
            return format_html(
                '<img src="{}" width="180" style="border-radius:8px;border:1px solid #e2e8f0;" />',
                obj.sample_certificate.url
            )
        return "-"
    sample_certificate_preview.short_description = "Certificate Preview"

    # ✅ PERFORMANCE BOOST
    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related('category').prefetch_related('tools', 'instructors')

        if request.user.is_superuser:
            return qs

        if not getattr(request.user, 'company_id', None):
            return qs.none()

        return qs.filter(company=request.user.company)

    def formfield_for_choice_field(self, db_field, request, **kwargs):
        if db_field.name == 'course_type' and not request.user.is_superuser:
            company = getattr(request.user, 'company', None)
            if company is None or not company.allow_i2i:
                kwargs['choices'] = [('default', 'Default (Regular Course)')]
        return super().formfield_for_choice_field(db_field, request, **kwargs)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if not request.user.is_superuser and db_field.name == 'category':
            kwargs['queryset'] = Category.objects.filter(company=request.user.company)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if not request.user.is_superuser:
            if db_field.name == "instructors":
                kwargs["queryset"] = CustomUser.objects.filter(
                    company=request.user.company,
                    role='instructor'
                )

            if db_field.name == "tools":
                kwargs["queryset"] = Tool.objects.filter(
                    company=request.user.company
                )

        return super().formfield_for_manytomany(db_field, request, **kwargs)

    def instructors_display(self, obj):
        people = [u.get_full_name() or u.email for u in obj.instructors.all()]
        return ', '.join(people) if people else '-'
    instructors_display.short_description = 'Instructors'


# =========================
# 🔹 SECTION ADMIN
# =========================

@admin.register(Section)
class SectionAdmin(ModelAdmin):

    list_display = (
        'title', 'course', 'order',
        'created_at', 'image_preview'
    )

    list_filter = ('course', 'created_at')
    search_fields = ('title', 'course__title')
    ordering = ('course', 'order')

    inlines = [LessonInline]

    class Media:
        js = ("admin/live_image_preview.js",)

    formfield_overrides = {
        models.TextField: {
            'widget': WysiwygWidget,
        }
    }

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        if not getattr(request.user, 'company_id', None):
            return qs.none()
        return qs.filter(course__company=request.user.company)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if not request.user.is_superuser and db_field.name == 'course':
            kwargs['queryset'] = Course.objects.filter(company=request.user.company)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="60" />', obj.image.url)
        return "-"
    image_preview.short_description = "Preview"



# =========================
# 🔹 LESSON ADMIN
# =========================

@admin.register(Lesson)
class LessonAdmin(ModelAdmin):

    list_display = (
        'title', 'section', 'order',
        'is_free', 'created_at', 'image_preview'
    )

    list_filter = (
        'is_free',
        'section__course',
        'created_at'
    )

    search_fields = (
        'title', 'section__title'
    )

    ordering = ('section', 'order')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        if not getattr(request.user, 'company_id', None):
            return qs.none()
        return qs.filter(section__course__company=request.user.company)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if not request.user.is_superuser and db_field.name == 'section':
            kwargs['queryset'] = Section.objects.filter(course__company=request.user.company)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def image_preview(self, obj):
        if obj.thumbnail:
            return format_html('<img src="{}" width="60" />', obj.thumbnail.url)
        return "-"
    image_preview.short_description = "Preview"

    # Show WYSIWYG for text fields on add/change
    formfield_overrides = {
        models.TextField: {
            'widget': WysiwygWidget,
        }
    }

    class Media:
        js = ("admin/live_image_preview.js",)

    # Show thumbnail preview and timestamps in the form
    readonly_fields = ('image_preview', 'created_at', 'updated_at')

    fieldsets = (
        ('Basic Info', {
            'fields': ('section', 'title', 'description', 'content', 'order', 'is_free', 'video_url')
        }),
        ('Media', {
            'fields': ('thumbnail', 'image_preview')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    


# =========================
# 🔹 SIMPLE ADMINS
# =========================

@admin.register(Requirement)
class RequirementAdmin(ModelAdmin):
    list_display = ('title', 'course', 'order')
    list_filter = ('course',)
    ordering = ('order',)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        if not getattr(request.user, 'company_id', None):
            return qs.none()
        return qs.filter(course__company=request.user.company)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if not request.user.is_superuser and db_field.name == 'course':
            kwargs['queryset'] = Course.objects.filter(company=request.user.company)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    
    formfield_overrides = {
        models.TextField: {
            'widget': WysiwygWidget,
        }
    }


@admin.register(Benefit)
class BenefitAdmin(ModelAdmin):
    list_display = ('title', 'course', 'order', 'image_preview')
    ordering = ('order',)
    class Media:
        js = ("admin/live_image_preview.js",)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        if not getattr(request.user, 'company_id', None):
            return qs.none()
        return qs.filter(course__company=request.user.company)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if not request.user.is_superuser and db_field.name == 'course':
            kwargs['queryset'] = Course.objects.filter(company=request.user.company)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def image_preview(self, obj):
        if obj.icon:
            return format_html('<img src="{}" width="40" />', obj.icon.url)
        return "-"
    image_preview.short_description = "Icon"



@admin.register(FAQ)
class FAQAdmin(ModelAdmin):
    list_display = ('question_display', 'course', 'order', 'created_at')
    ordering = ('order',)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        if not getattr(request.user, 'company_id', None):
            return qs.none()
        return qs.filter(course__company=request.user.company)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if not request.user.is_superuser and db_field.name == 'course':
            kwargs['queryset'] = Course.objects.filter(company=request.user.company)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    formfield_overrides = {
        models.TextField: {
            'widget': WysiwygWidget,
        }
    }

    def question_display(self, obj):
        return mark_safe(obj.question)
    question_display.short_description = 'Question'


@admin.register(Tool)
class ToolAdmin(CompanyAdminMixin, ModelAdmin):
    list_display = ('name', 'company', 'category')
    list_filter = ('company', 'category')
    search_fields = ('name', 'category')
    fieldsets = (
        ('Basic Info', {'fields': ('company', 'name', 'category')}),
        ('Details', {'fields': ('icon_url',)}),
    )


@admin.register(CourseAudience)
class CourseAudienceAdmin(ModelAdmin):
    list_display = ('title', 'course', 'order')
    ordering = ('order',)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        if not getattr(request.user, 'company_id', None):
            return qs.none()
        return qs.filter(course__company=request.user.company)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if not request.user.is_superuser and db_field.name == 'course':
            kwargs['queryset'] = Course.objects.filter(company=request.user.company)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    formfield_overrides = {
        models.TextField: {
            'widget': WysiwygWidget,
        }
    }


@admin.register(CourseMedia)
class CourseMediaAdmin(ModelAdmin):
    list_display = ('course', 'uploaded_at', 'image_preview')
    readonly_fields = ('uploaded_at',)

    class Media:
        js = ("admin/live_image_preview.js",)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        if not getattr(request.user, 'company_id', None):
            return qs.none()
        return qs.filter(course__company=request.user.company)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if not request.user.is_superuser and db_field.name == 'course':
            kwargs['queryset'] = Course.objects.filter(company=request.user.company)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="80" />', obj.image.url)
        return '-'
    image_preview.short_description = 'Preview'



@admin.register(CertificateTemplate)
class CertificateTemplateAdmin(CompanyAdminMixin, ModelAdmin):
    company_field = 'course__company'
    
    list_display = (
        'name',
        'course',
        'is_default',
        'width_mm',
        'height_mm',
        'created_at',
    )

    def get_list_filter(self, request):
        if request.user.is_superuser:
            return ('is_default', 'course__company', 'course')
        return ('is_default', 'course')

    search_fields = (
        'name',
        'course__title',
    )

    fieldsets = (
        ('Template Info', {
            'fields': (
                'course',
                'name',
                'background_image',
                'is_default',
            )
        }),
        ('Page Size', {
            'fields': (
                'width_mm',
                'height_mm',
            )
        }),
        ('Student Name Position', {
            'fields': (
                'student_name_x',
                'student_name_y',
                'student_name_font_size',
            )
        }),
        ('Course Title Position', {
            'fields': (
                'course_title_x',
                'course_title_y',
                'course_title_font_size',
            )
        }),
        ('Issue Date Position', {
            'fields': (
                'date_issued_x',
                'date_issued_y',
                'date_issued_font_size',
            )
        }),
        ('Certificate Number Position', {
            'fields': (
                'certificate_no_x',
                'certificate_no_y',
                'certificate_no_font_size',
            )
        }),
        ('Registration Number Position', {
            'fields': (
                'registration_no_x',
                'registration_no_y',
                'registration_no_font_size',
            )
        }),
        ('Total Months Position', {
            'fields': (
                'total_months_x',
                'total_months_y',
                'total_months_font_size',
            )
        }),
        ('Start Period Position', {
            'fields': (
                'start_period_x',
                'start_period_y',
                'start_period_font_size',
            )
        }),
        ('End Period Position', {
            'fields': (
                'end_period_x',
                'end_period_y',
                'end_period_font_size',
            )
        }),
        ('Custom Text Position', {
            'fields': (
                'custom_text_content',
                'custom_text_x',
                'custom_text_y',
                'custom_text_font_size',
            )
        }),
        ('QR Code Position', {
            'fields': (
                'qr_code_x',
                'qr_code_y',
                'qr_code_size',
            )
        }),
        ('Colors', {
            'fields': (
                'primary_text_color',
                'secondary_text_color',
            )
        }),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)

        if request.user.is_superuser:
            return qs

        if not getattr(request.user, 'company_id', None):
            return qs.none()

        return qs.filter(course__company=request.user.company)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if not request.user.is_superuser and db_field.name == 'course':
            kwargs['queryset'] = Course.objects.filter(company=request.user.company)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    formfield_overrides = {
        models.TextField: {
            'widget': WysiwygWidget,
        }
    }

    class Media:
        js = ("admin/live_image_preview.js",)

    actions = ['download_sample_certificate']

    def download_sample_certificate(self, request, queryset):
        """
        Admin action to download a sample certificate preview.
        """
        if queryset.count() != 1:
            self.message_user(request, 'Please select exactly one certificate template.', admin.messages.ERROR)
            return

        template = queryset.first()

        try:
            pdf_buffer = generate_sample_certificate_pdf(template)
            response = HttpResponse(pdf_buffer.read(), content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="sample-certificate-{template.id}.pdf"'
            return response
        except Exception as e:
            self.message_user(request, f'Error generating sample certificate: {str(e)}', admin.messages.ERROR)
            return

    download_sample_certificate.short_description = '📥 Download Sample Certificate'
