from django.urls import path
from . import views

app_name = 'exams'

urlpatterns = [
    path('', views.ExamListView.as_view(), name='exam_list'),
    path('<int:exam_id>/take/', views.TakeExamView.as_view(), name='take_exam'),
    path('result/<int:attempt_id>/', views.ExamResultView.as_view(), name='exam_result'),
]
