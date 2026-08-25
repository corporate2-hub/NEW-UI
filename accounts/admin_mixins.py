from django.contrib import admin


class CompanyAdminMixin:
    company_field = 'company'

    def get_queryset(self, request):
        qs = super().get_queryset(request)

        if request.user.is_superuser:
            return qs

        if not getattr(request.user, 'company_id', None):
            return qs.none()

        return qs.filter(**{self.company_field: request.user.company})

    def save_form(self, request, form, change):
        obj = super().save_form(request, form, change)
        if hasattr(obj, self.company_field) and not getattr(obj, f"{self.company_field}_id", None):
            # 1. Try request.company (from middleware)
            # 2. Try request.user.company
            # 3. Fallback to first active company for staff members
            company = getattr(request, 'company', None)
            if not company:
                company = getattr(request.user, 'company', None)
            
            if not company and request.user.is_staff:
                from .models import Company
                company = Company.objects.filter(is_active=True).first()

            if company:
                setattr(obj, self.company_field, company)
        return obj

    def save_model(self, request, obj, form, change):
        if hasattr(obj, self.company_field) and not getattr(obj, f"{self.company_field}_id", None):
            # 1. Try request.company (from middleware)
            # 2. Try request.user.company
            # 3. Fallback to first active company for staff members
            company = getattr(request, 'company', None)
            if not company:
                company = getattr(request.user, 'company', None)
            
            if not company and request.user.is_staff:
                from .models import Company
                company = Company.objects.filter(is_active=True).first()

            if company:
                setattr(obj, self.company_field, company)

        super().save_model(request, obj, form, change)

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))

        if not request.user.is_superuser and self.company_field not in readonly:
            readonly.append(self.company_field)

        return readonly
