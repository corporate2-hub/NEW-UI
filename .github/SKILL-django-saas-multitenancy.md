# Skill: django-saas-multitenancy

Purpose
-------
This skill codifies the repository's FK-based multi-tenancy rules and patterns for the Skill Training Django project. It exists to:

- Spell out conventions that Copilot (and contributors) must follow when touching tenancy-sensitive code.
- Provide copy-paste-ready code snippets and queries that preserve data isolation.
- Centralize admin, view, template, and testing guidance so future work is consistent and safe.

Where to place this skill
-------------------------
Preferred location: `.github/skills/django-saas-multitenancy/SKILL.md` so Copilot sessions and developers can find the tenancy rules quickly.

NOTE: The execution environment could not create nested directories in this session due to limited shell access. This file is created at `.github/SKILL-django-saas-multitenancy.md` as a temporary placement. If you want the canonical nested folder, I can move it once shell/file permissions are available or you can run the single command to create the folder and re-run this step.

Core principles (short)
-----------------------
- Tenancy is FK-based (column tenancy) — do NOT use schema-based tenancy or django-tenants.
- Students are global: student users may have `company = NULL` and can be enrolled across companies.
- Admins & instructors are company-scoped: they must be associated with a Company to access or manage company data.
- Superusers may access all companies and bypass scoping checks.
- NEVER return or act on unscoped querysets for company-scoped resources in production views or admin actions.

Quick references (code paths)
-----------------------------
- Middleware: `core.middleware.CompanyMiddleware` — sets `request.company`.
- Context processor: `core.context_processors.company_context` — exposes `company` to templates.
- Company model: `accounts.models.Company` — store branding, domain, scripts, and status.
- Custom user: `accounts.models.CustomUser` — includes `role` and `company` fields.
- Admin mixin: `accounts.admin_mixins.CompanyAdminMixin` — used across ModelAdmin classes.
- Course model: `courses.models.Course` — contains `company` FK; `unique_together = ('company', 'slug')`.

Design rules (expanded)
-----------------------
1) Students are global
   - The `CustomUser` may have `company = NULL` for students. Treat students as platform-level users: they can enroll in batches across companies.
   - When selecting students in the admin, prefer `CustomUser.objects.filter(role='student')` (global) and do NOT restrict students by company.

2) Admins & instructors are company-scoped
   - Admin and instructor users must have `company` set. Non-superuser admin/instructor accounts should only see and manage data for their company.
   - In the admin UI and in views, restrict querysets to `request.user.company` for non-superusers.

3) Company filtering logic (library of patterns)
   - Obtain current company safely:

     company = getattr(request, 'company', None)

   - View-level pattern (company-only view):

     qs = Course.objects.filter(status='published')
     company = getattr(request, 'company', None)
     if company:
         qs = qs.filter(company=company)
     else:
         # If this view is only for company sites, do not show marketplace content
         return Course.objects.none()

   - Marketplace (public/global) pattern:

     # Show published courses that belong to any active company
     Course.objects.filter(status='published', company__is_active=True)

   - For related models (Section, Lesson, ClassSession, Enrollment, Attendance) filter using joins:

     Section.objects.filter(course__company=company)
     Lesson.objects.filter(section__course__company=company)
     ClassSession.objects.filter(batch__company=company)
     Enrollment.objects.filter(batch__course__company=company)
     Attendance.objects.filter(class_session__batch__company=company)

4) Admin mixin usage
   - Use `CompanyAdminMixin` as the first mixin for ModelAdmin classes to enforce company scoping:

     class CourseAdmin(CompanyAdminMixin, ModelAdmin):
         # mixin implements get_queryset, save_model, get_readonly_fields
         pass

   - The mixin should:
     - Filter queryset for non-superusers to `company=request.user.company`.
     - Auto-assign `obj.company = request.user.company` on save for new objects (if field exists).
     - Mark `company` readonly for non-superusers in the admin form.

5) Security & data isolation rules
   - Always validate ownership on object-level operations:

     if obj.company != request.user.company and not request.user.is_superuser:
         raise PermissionDenied()

   - For bulk actions in admin or management commands, ensure querysets are pre-filtered to the acting user's company (unless `is_superuser`).
   - Do NOT rely solely on templates or client-side checks for isolation — enforce checks in views, model managers, signals, and admin classes.
   - Use `select_related` and `prefetch_related` responsibly to avoid accidental cross-tenant joins in loops.

6) Public course marketplace behavior
   - The marketplace shows courses across companies. Use an explicit marketplace view/route and query:

     Course.objects.filter(status='published', company__is_active=True).order_by('-created_at')

   - Company-branded sites (domain-resolved via Company.domain) must show only company-owned courses; the middleware sets `request.company` for this case.
   - Templates should render `company` values (logo, hero, CTA) from `request.company` and fall back to marketplace defaults when `company` is None.

7) Model and DB conventions
   - Any model that must be tenant-scoped MUST include a `company = models.ForeignKey('accounts.Company', on_delete=models.CASCADE)` field.
   - Use `unique_together = ('company', 'slug')` or similar to enforce per-tenant uniqueness.
   - Avoid using `company` in implicit relationships where it can be omitted — prefer explicit joins/filters described above.

8) Testing guidance
   - Tests that rely on company resolution should set the `Host` header (or set `request.company` manually) to simulate domain resolution.
   - Always create Company fixtures in tests and attach instructor/admin users to a Company where required.
   - Example (test client):

     client = Client(HTTP_HOST='acme.example')
     # ensure Company(domain='acme.example') exists
     response = client.get(reverse('courses:course_list'))

9) Seed / sample data
   - `core.management.commands.populate_sample_data` exists; review and update it when models change so seeded courses/batches honor `company` constraints.

10) Admin & management operations
    - When writing admin actions (approve_enrollment, reject_enrollment), update only records filtered to `request.user.company` for non-superusers.
    - When creating objects via admin, prefer `formfield_for_foreignkey`/`formfield_for_manytomany` overrides to limit choices to the current company for non-superusers.

Examples & snippets
-------------------
- Object-level validation (views or signals):

  def ensure_company_owned(obj, user):
      if not user.is_superuser and getattr(obj, 'company', None) != getattr(user, 'company', None):
          raise PermissionDenied()

- Admin mixin minimal implementation pattern (reference existing `accounts.admin_mixins`):

  class CompanyAdminMixin:
      company_field = 'company'

      def get_queryset(self, request):
          qs = super().get_queryset(request)
          if request.user.is_superuser:
              return qs
          if not getattr(request.user, 'company_id', None):
              return qs.none()
          return qs.filter(**{self.company_field: request.user.company})

      def save_model(self, request, obj, form, change):
          if not request.user.is_superuser and hasattr(obj, self.company_field):
              if not getattr(obj, f"{self.company_field}_id", None):
                  setattr(obj, self.company_field, request.user.company)
          super().save_model(request, obj, form, change)

Operational notes
-----------------
- When adding a new tenant-scoped model:
  1. Add `company = ForeignKey(Company, on_delete=CASCADE)`.
  2. Add `unique_together` where appropriate.
  3. Update admin to include `CompanyAdminMixin` and restrict FK choices.
  4. Update views and templates to filter by company.
  5. Update tests and seeders.

- When building API endpoints, apply the same company scoping at the viewset/queryset level and in serializer `create()`/`update()` when setting `company`.

FAQ (short)
-----------
Q: Should I ever return unscoped Course.objects.all()?  
A: No. For company pages, always scope by company. For marketplace pages use the explicit marketplace query.

Q: Are students tenant-scoped?  
A: No — students are global users (company may be NULL). Only instructors/admins are required to have `company`.

Q: Can superusers bypass company scoping?  
A: Yes — superusers have full access and admin UI capabilities.

Where to change this skill
-------------------------
- Update this SKILL.md whenever tenancy rules change (e.g., moving to schema tenancy or changing student tenancy).
- Add examples and common pitfalls encountered in PR reviews here so Copilot sessions pick up practical context.

Contact
-------
If unsure about a tenancy decision, open an issue and reference this skill. Tag `@platform-owner` (or your team) for a second opinion before changing scoping rules.

----
Generated from `copilot-instructions-multicompany.md` guidance; keep this file authoritative for FK-based tenancy rules.
