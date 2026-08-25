from django.urls import path
from . import views

app_name = 'enrollments'

urlpatterns = [
    path('batch/<int:batch_id>/request/', views.EnrollmentRequestView.as_view(), name='enrollment_request'),
    path('my-enrollments/', views.MyEnrollmentsView.as_view(), name='my_enrollments'),
    path(
        'certificate/<uuid:uuid>/',
        views.CertificatePublicView.as_view(),
        name='certificate_public'
    ),

    path(
        'certificate/<uuid:uuid>/pdf/',
        views.CertificatePDFView.as_view(),
        name='certificate_pdf'
    ),

    path(
        'my-enrollment/<int:enrollment_id>/certificate/',
        views.StudentCertificateRedirectView.as_view(),
        name='student_certificate'
    ),
]
