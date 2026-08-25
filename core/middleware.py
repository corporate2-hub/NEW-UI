from django.db import DatabaseError
from accounts.models import Company


class CompanyMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        host = request.get_host().split(':')[0]

        company = None
        try:
            company = Company.objects.filter(domain=host, is_active=True).first()
        except DatabaseError:
            # DB not ready (migrations) or other DB issue — leave company as None
            company = None

        if not company:
            try:
                company = Company.objects.filter(is_active=True).first()
            except DatabaseError:
                company = None

        request.company = company

        return self.get_response(request)
