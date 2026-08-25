from django.db import models
from accounts.models import CustomUser
from enrollments.models import Enrollment


class StudentDashboardAccessLog(models.Model):
    """Log student dashboard access for analytics."""
    
    student = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='dashboard_access_logs')
    accessed_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True, null=True)
    
    class Meta:
        db_table = 'dashboard_studentaccesslog'
        verbose_name = 'Student Dashboard Access'
        verbose_name_plural = 'Student Dashboard Accesses'
        ordering = ['-accessed_at']
