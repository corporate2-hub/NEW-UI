from django.urls import path
from . import views

app_name = 'attendance'

urlpatterns = [
    path('class/<int:class_id>/', views.MarkAttendanceView.as_view(), name='mark_attendance'),
    path('batch/<int:batch_id>/summary/', views.AttendanceSummaryView.as_view(), name='attendance_summary'),
]
