from django.db import models
from django.db.models import Q
from accounts.models import CustomUser
from classes.models import ClassSession
from enrollments.models import Enrollment


class Attendance(models.Model):
    """Student attendance records."""
    
    ATTENDANCE_STATUS = (
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('late', 'Late'),
    )
    
    class_session = models.ForeignKey(ClassSession, on_delete=models.CASCADE, related_name='attendance_records')
    student = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='attendance_records')
    status = models.CharField(max_length=20, choices=ATTENDANCE_STATUS)
    recorded_at = models.DateTimeField(auto_now_add=True)
    recorded_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='attendance_recorded')
    remarks = models.TextField(blank=True, null=True)
    
    class Meta:
        db_table = 'attendance_attendance'
        verbose_name = 'Attendance'
        verbose_name_plural = 'Attendance Records'
        ordering = ['-recorded_at']
        unique_together = ('class_session', 'student')
    
    def __str__(self):
        return f"{self.student.username} - {self.class_session.title} ({self.status})"
    
    @classmethod
    def get_attendance_summary(cls, student, batch):
        """
        Get attendance summary for a student in a batch.
        Returns dict with attendance counts and percentage.
        """
        sessions = ClassSession.objects.filter(batch=batch)
        records = cls.objects.filter(student=student, class_session__in=sessions)
        
        total = sessions.count()
        present = records.filter(status='present').count()
        absent = records.filter(status='absent').count()
        late = records.filter(status='late').count()
        
        percentage = (present / total * 100) if total > 0 else 0
        
        return {
            'total': total,
            'present': present,
            'absent': absent,
            'late': late,
            'percentage': round(percentage, 2)
        }
