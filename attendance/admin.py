from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Attendance
from .forms import AttendanceAdminForm
from classes.models import ClassSession
from accounts.models import CustomUser


class AttendanceAdmin(ModelAdmin):
    form = AttendanceAdminForm
    list_display = ['student', 'class_session', 'status', 'recorded_at', 'recorded_by']
    list_filter = ['status', 'class_session__batch', 'recorded_at']
    search_fields = ['student__username', 'class_session__title']
    readonly_fields = ['recorded_at', 'recorded_by']
    fieldsets = (
        ('Attendance', {'fields': ('class_session', 'student', 'status')}),
        ('Details', {'fields': ('recorded_by', 'remarks', 'recorded_at')}),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)

        if request.user.is_superuser:
            return qs

        return qs.filter(class_session__batch__company=request.user.company)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """
        Server-side queryset restriction — acts as the validation safety net
        independently of the Select2 widget filters.
        """
        if not request.user.is_superuser:
            if db_field.name == 'class_session':
                kwargs['queryset'] = ClassSession.objects.filter(
                    batch__company=request.user.company
                )

        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        if not obj.recorded_by_id:
            obj.recorded_by = request.user
        super().save_model(request, obj, form, change)


admin.site.register(Attendance, AttendanceAdmin)

