from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import StudentDashboardAccessLog


class StudentDashboardAccessLogAdmin(ModelAdmin):
    list_display = ['student', 'accessed_at', 'ip_address']
    list_filter = ['accessed_at']
    search_fields = ['student__username', 'ip_address']
    readonly_fields = ['accessed_at', 'ip_address', 'user_agent']

    def has_add_permission(self, request):
        """Disable adding new access logs."""
        return False

    def has_change_permission(self, request, obj=None):
        """Disable editing access logs."""
        return False

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        if not getattr(request.user, 'company_id', None):
            return qs.none()
        # Scope to students enrolled in this company's batches
        return qs.filter(
            student__enrollments__batch__company=request.user.company
        ).distinct()


admin.site.register(StudentDashboardAccessLog, StudentDashboardAccessLogAdmin)
