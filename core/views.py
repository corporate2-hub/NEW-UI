from django.contrib.sitemaps.views import sitemap
from django.shortcuts import render
from django.views.generic import TemplateView
from courses.models import Course, Category
from accounts.models import Company
from .sitemaps import CourseSitemap, StaticSitemap


def home(request):
    """Homepage view with featured courses.

    Behavior:
    - If `request.company` is set (domain-resolved), show company-owned content/stats.
    - Otherwise show marketplace/global content.
    """
    # Resolve company from request (middleware should set this), fallback to first active
    company = getattr(request, 'company', None)
    if not company:
        try:
            company = Company.objects.filter(is_active=True).first()
        except Exception:
            company = None

    # Courses: company-specific when company exists, otherwise marketplace
    if company:
        base_qs = Course.objects.filter(status='published', company=company)
        total_courses = base_qs.count()
        training_programs = base_qs.filter(course_type='default').order_by('-created_at')[:6]
        i2i_programs = base_qs.filter(course_type='i2i').order_by('-created_at')[:6] if company.allow_i2i else []
    else:
        base_qs = Course.objects.filter(status='published', company__is_active=True)
        total_courses = base_qs.count()
        training_programs = base_qs.filter(course_type='default').order_by('-created_at')[:6]
        i2i_programs = []

    categories = Category.objects.all()

    context = {
        'company': company,
        'training_programs': training_programs,
        'i2i_programs': i2i_programs,
        'categories': categories,
        'total_courses': total_courses,
    }
    return render(request, 'core/index.html', context)


def about(request):
    company = getattr(request, 'company', None)

    return render(request, 'core/about.html', {
        'company': company
    })


def company_sitemap(request):
    """Tenant-aware sitemap.xml view.

    Resolves the current company from ``request.company`` (set by
    CompanyMiddleware) and returns an XML sitemap scoped to that tenant,
    covering the home, about, courses list, and individual course pages.
    """
    company = getattr(request, 'company', None)
    sitemaps = {
        'static': StaticSitemap(company),
        'courses': CourseSitemap(company),
    }
    return sitemap(request, sitemaps, content_type='application/xml')
