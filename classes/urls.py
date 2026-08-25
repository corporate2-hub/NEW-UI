from django.urls import path
from . import views

app_name = 'classes'

urlpatterns = [
    path('batch/<int:batch_id>/', views.BatchClassListView.as_view(), name='batch_class_list'),
    path('<int:class_id>/', views.ClassDetailView.as_view(), name='class_detail'),
]
