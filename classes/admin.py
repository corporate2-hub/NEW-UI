from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import ClassSession, ClassResource
from enrollments.models import Batch



class ClassResourceInline(admin.TabularInline):
    model = ClassResource
    extra = 1


class ClassSessionAdmin(ModelAdmin):
    list_display = ['title', 'batch', 'scheduled_date', 'scheduled_time', 'topic', 'has_recording']
    list_filter = ['scheduled_date']
    search_fields = ['title', 'topic', 'batch__name']

    def get_list_filter(self, request):
        if request.user.is_superuser:
            return ['scheduled_date', 'batch__course']
        return ['scheduled_date']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [ClassResourceInline]
    fieldsets = (
        ('Basic Info', {'fields': ('batch', 'title', 'topic', 'description')}),
        ('Schedule', {'fields': ('scheduled_date', 'scheduled_time')}),
        ('Links', {'fields': ('meet_link', 'recording_link')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )
    
    def has_recording(self, obj):
        return bool(obj.recording_link)
    has_recording.boolean = True
    has_recording.short_description = 'Recording'

    def get_queryset(self, request):
        qs = super().get_queryset(request)

        if request.user.is_superuser:
            return qs

        return qs.filter(batch__company=request.user.company)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'batch' and not request.user.is_superuser:
            if getattr(request.user, 'company_id', None):
                kwargs['queryset'] = Batch.objects.filter(company=request.user.company)
            else:
                kwargs['queryset'] = Batch.objects.none()

        return super().formfield_for_foreignkey(db_field, request, **kwargs)


admin.site.register(ClassSession, ClassSessionAdmin)
