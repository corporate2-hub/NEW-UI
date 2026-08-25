from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('student/', views.StudentDashboardView.as_view(), name='student_dashboard'),
    path('instructor/', views.InstructorDashboardView.as_view(), name='instructor_dashboard'),
    path('admin/', views.AdminDashboardView.as_view(), name='admin_dashboard'),
]
