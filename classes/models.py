from django.db import models
from django.utils import timezone
from accounts.models import CustomUser
from enrollments.models import Batch


class ClassSession(models.Model):
    """Live class sessions."""
    
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name='class_sessions')
    title = models.CharField(max_length=255)
    topic = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    scheduled_date = models.DateField()
    scheduled_time = models.TimeField()
    meet_link = models.URLField()
    recording_link = models.URLField(blank=True, null=True, help_text="Added after class")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'classes_classsession'
        verbose_name = 'Class Session'
        verbose_name_plural = 'Class Sessions'
        ordering = ['-scheduled_date', '-scheduled_time']
    
    def __str__(self):
        return f"{self.batch.name} - {self.title} ({self.scheduled_date})"
    
    @property
    def is_upcoming(self):
        from datetime import datetime
        session_datetime = datetime.combine(self.scheduled_date, self.scheduled_time)
        return session_datetime > datetime.now()
    
    @property
    def is_completed(self):
        from datetime import datetime
        session_datetime = datetime.combine(self.scheduled_date, self.scheduled_time)
        return session_datetime < datetime.now()


class ClassResource(models.Model):
    """Resources attached to class sessions."""
    
    class_session = models.ForeignKey(ClassSession, on_delete=models.CASCADE, related_name='resources')
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to='class_resources/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'classes_classresource'
        verbose_name = 'Class Resource'
        verbose_name_plural = 'Class Resources'
        ordering = ['-uploaded_at']
    
    def __str__(self):
        return self.title
