

# 🚀 FULL A2Z INSTRUCTIONS (UPDATED)

````md
# Skill Jobs SaaS Platform — Copilot Instructions (Full A2Z)

This is a Django 4.2 SaaS training platform.

We are building a **hybrid SaaS system**:

- Global marketplace (skill.jobs)
- Multi-company white-label system (company domains)
- Shared learners
- Company-owned courses

---

# 🧠 CORE ARCHITECTURE

Request → Domain → Company → Dynamic UI + Data

Each request MUST resolve a Company.

---

# 🏢 COMPANY MODEL (CORE)

Company controls:
- Branding
- Homepage content
- Header/Footer
- Domain routing

```python
class Company(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)

    # Domain / Routing
    domain = models.CharField(max_length=255, unique=True, help_text="example.com or company.skill.jobs")

    # Branding
    logo = models.ImageField(upload_to='company/', blank=True, null=True)
    favicon = models.ImageField(upload_to='company/', blank=True, null=True)

    # Header
    header_cta_text = models.CharField(max_length=100, blank=True)
    header_cta_link = models.CharField(max_length=255, blank=True)

    # Hero Section
    hero_title = models.CharField(max_length=255, blank=True)
    hero_subtitle = models.TextField(blank=True)
    hero_cta_text = models.CharField(max_length=100, blank=True)
    hero_cta_link = models.CharField(max_length=255, blank=True)

    # Stats Section
    total_students = models.CharField(max_length=50, blank=True)
    total_courses = models.CharField(max_length=50, blank=True)
    total_batches = models.CharField(max_length=50, blank=True)
    total_mentors = models.CharField(max_length=50, blank=True)

    # Footer
    footer_text = models.TextField(blank=True)
    contact_phone = models.CharField(max_length=50, blank=True)
    contact_email = models.EmailField(blank=True)

    # SEO
    meta_title = models.CharField(max_length=255, blank=True)
    meta_description = models.TextField(blank=True)

    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name
````

---

# 🌐 DOMAIN-BASED MULTI-TENANCY

## Middleware (REQUIRED)

Create:

```python
# core/middleware.py
from accounts.models import Company

class CompanyMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        host = request.get_host().split(':')[0]

        company = Company.objects.filter(domain=host, is_active=True).first()

        if not company:
            # fallback to main marketplace company
            company = Company.objects.filter(is_active=True).first()

        request.company = company

        return self.get_response(request)
```

## Add to settings:

```python
MIDDLEWARE += ['core.middleware.CompanyMiddleware']
```

---

# 🧾 CONTEXT PROCESSOR

```python
# core/context_processors.py
def company_context(request):
    return {
        'company': getattr(request, 'company', None)
    }
```

Add to settings:

```python
TEMPLATES[0]['OPTIONS']['context_processors'] += [
    'core.context_processors.company_context'
]
```

---

# 🎨 FRONTEND RULES (CRITICAL)

## NEVER HARDCODE UI CONTENT

Always use:

```django
{{ company }}
```

---

## HEADER

```django
{% if company.logo %}
<img src="{{ company.logo.url }}">
{% else %}
{{ company.name }}
{% endif %}
```

```django
<a href="{{ company.header_cta_link }}">
    {{ company.header_cta_text }}
</a>
```

---

## HERO SECTION

```django
<h1>{{ company.hero_title }}</h1>
<p>{{ company.hero_subtitle }}</p>

<a href="{{ company.hero_cta_link }}">
    {{ company.hero_cta_text }}
</a>
```

---

## STATS

```django
{{ company.total_students }}
{{ company.total_courses }}
{{ company.total_batches }}
{{ company.total_mentors }}
```

---

## FOOTER

```django
{{ company.footer_text }}
{{ company.contact_email }}
{{ company.contact_phone }}
```

---

# 👤 USER MODEL RULES

```python
class CustomUser(AbstractUser):
    role = models.CharField(...)
    company = models.ForeignKey(Company, null=True, blank=True)
```

## Rules:

* Students → GLOBAL (company can be NULL)
* Admin/Instructor → MUST belong to company
* Superuser → global access

---

# 📚 MULTI-TENANT DATA RULES

## Direct Models

```python
Course.company
Batch.company
```

---

## Indirect Filtering

| Model        | Filter                        |
| ------------ | ----------------------------- |
| Section      | course__company               |
| Lesson       | section__course__company      |
| ClassSession | batch__company                |
| Enrollment   | batch__company                |
| Attendance   | class_session__batch__company |

---

# 🔐 SECURITY RULES

Always validate:

```python
if obj.company != request.user.company and not request.user.is_superuser:
    raise PermissionDenied()
```

---

# 📊 QUERY RULES

## Public (Marketplace)

```python
Course.objects.filter(
    status='published',
    company__is_active=True
)
```

---

## Admin

```python
Course.objects.filter(company=request.user.company)
```

---

## Enrollment

```python
Enrollment.objects.filter(student=request.user)
```

---

# 🧾 ADMIN PANEL RULES

Superuser:

* access all companies

Company admin:

* only own company

Auto assign:

```python
obj.company = request.user.company
```

---

# 🌐 URL STRATEGY

Supported:

## Marketplace

```
skill.jobs
```

## Subdomain SaaS

```
company1.skill.jobs
company2.skill.jobs
```

## Custom Domain

```
company1.com
```

---

# ⚠️ IMPORTANT DECISIONS

## Slug Strategy

Option 1 (simple):

* global unique slug

Option 2 (advanced SaaS):

```
/courses/<company_slug>/<course_slug>/
```

---

# 🚫 DO NOT

* Do not use django-tenants
* Do not use schema-based tenancy
* Do not hardcode UI content
* Do not expose company selection in frontend

---

# 🎯 FINAL GOAL

Build a hybrid SaaS:

✔ Shared users (marketplace)
✔ Company-owned content
✔ Domain-based branding
✔ Full CMS control from admin
✔ Secure data isolation

---
