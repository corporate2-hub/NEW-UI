"""
File path:
    courses/management/commands/seed_fullstack_course.py

Run:
    python manage.py seed_fullstack_course
    python manage.py seed_fullstack_course --reset-images
    python manage.py seed_fullstack_course --slug django-react-full-stack-masterclass

What it does:
    - Creates/updates one complete Django + React full-stack course
    - Creates/updates category, instructor, tools, audiences, benefits, requirements, FAQs
    - Creates/updates sections and lessons by order, so re-running updates safely
    - Creates/updates a batch
    - Downloads Unsplash images into ImageField/FileField only when missing
    - Use --reset-images to re-download/replace images
"""

import os
import tempfile
from decimal import Decimal
from datetime import timedelta
from urllib.parse import urlparse

import requests
from django.core.files import File
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from core.models import Category
from courses.models import (
    Course,
    Section,
    Lesson,
    Benefit,
    Requirement,
    FAQ,
    Tool,
    CourseAudience,
)
from enrollments.models import Batch
from accounts.models import Company

User = get_user_model()


UNSPLASH_IMAGES = {
    "course_banner": "https://images.unsplash.com/photo-1498050108023-c5249f4df085?auto=format&fit=crop&w=1600&q=85",
    "section_frontend": "https://images.unsplash.com/photo-1461749280684-dccba630e2f6?auto=format&fit=crop&w=1200&q=85",
    "section_backend": "https://images.unsplash.com/photo-1515879218367-8466d910aaa4?auto=format&fit=crop&w=1200&q=85",
    "section_api": "https://images.unsplash.com/photo-1558494949-ef010cbdcc31?auto=format&fit=crop&w=1200&q=85",
    "section_deployment": "https://images.unsplash.com/photo-1551288049-bebda4e38f71?auto=format&fit=crop&w=1200&q=85",
    "lesson_react": "https://images.unsplash.com/photo-1633356122544-f134324a6cee?auto=format&fit=crop&w=900&q=80",
    "lesson_django": "https://images.unsplash.com/photo-1517694712202-14dd9538aa97?auto=format&fit=crop&w=900&q=80",
    "lesson_api": "https://images.unsplash.com/photo-1555949963-aa79dcee981c?auto=format&fit=crop&w=900&q=80",
    "lesson_deploy": "https://images.unsplash.com/photo-1451187580459-43490279c0fa?auto=format&fit=crop&w=900&q=80",
}


class Command(BaseCommand):
    help = "Create/update a complete Django React full-stack sample course with downloaded Unsplash images."

    def add_arguments(self, parser):
        parser.add_argument(
            "--slug",
            default="django-react-full-stack-masterclass",
            help="Stable slug used to create/update the course.",
        )
        parser.add_argument(
            "--title",
            default="Django + React Full Stack Masterclass",
            help="Course title.",
        )
        parser.add_argument(
            "--category",
            default="Full Stack Web Development",
            help="Category name.",
        )
        parser.add_argument(
            "--price",
            default="6999.00",
            help="Course price. Example: 6999.00",
        )
        parser.add_argument(
            "--instructors",
            default="nizam_mentor,react_django_mentor",
            help="Comma-separated instructor usernames.",
        )
        parser.add_argument(
            "--reset-images",
            action="store_true",
            help="Force re-download and replace all image fields.",
        )
        parser.add_argument(
            "--no-images",
            action="store_true",
            help="Skip image download/upload.",
        )
        parser.add_argument(
            "--company",
            default="default",
            help="Company slug to assign created company-scoped objects to.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        slug = slugify(options["slug"])
        title = options["title"].strip()
        category_name = options["category"].strip()
        price = Decimal(str(options["price"]))
        reset_images = options["reset_images"]
        no_images = options["no_images"]

        self.stdout.write(self.style.NOTICE("Creating/updating Django + React full-stack course..."))

        company_slug = options.get("company")
        company, _ = Company.objects.get_or_create(
            slug=company_slug,
            defaults={"name": company_slug.replace("-", " ").title()},
        )

        category = self.upsert_category(category_name)
        instructors = self.upsert_instructors(options["instructors"], company)
        course = self.upsert_course(slug, title, category, price, company)

        if instructors:
            course.instructors.set(instructors)

        if not no_images:
            self.set_image_if_needed(
                obj=course,
                field_name="banner_image",
                url=UNSPLASH_IMAGES["course_banner"],
                filename=f"{slug}-banner.jpg",
                reset=reset_images,
            )

        tools = self.upsert_tools()
        course.tools.set(tools)

        self.upsert_audiences(course)
        self.upsert_benefits(course)
        self.upsert_requirements(course)
        self.upsert_faqs(course)
        self.upsert_sections_and_lessons(course, reset_images=reset_images, no_images=no_images)
        self.upsert_batch(course, instructors[0] if instructors else None)

        self.stdout.write(self.style.SUCCESS("Done. Full-stack course data is ready."))
        self.stdout.write(self.style.SUCCESS(f"Course: {course.title}"))
        self.stdout.write(self.style.SUCCESS(f"Slug: {course.slug}"))
        self.stdout.write(self.style.SUCCESS(f"Sections: {course.sections.count()}"))
        self.stdout.write(
            self.style.SUCCESS(
                f"Lessons: {sum(section.lessons.count() for section in course.sections.all())}"
            )
        )
        self.stdout.write(self.style.SUCCESS(f"Tools: {course.tools.count()}"))
        self.stdout.write(self.style.SUCCESS(f"Audiences: {course.audiences.count()}"))
        self.stdout.write(self.style.SUCCESS(f"Batches: {course.batches.count()}"))

    def upsert_category(self, name):
        category, created = Category.objects.update_or_create(
            name=name,
            defaults={
                "description": "Production-focused full-stack web development courses using Django, DRF, React, Tailwind, PostgreSQL, and deployment workflows."
            },
        )
        self.log_action(created, "category", category.name)
        return category

    def upsert_instructors(self, instructors_arg, company):
        usernames = [u.strip() for u in instructors_arg.split(",") if u.strip()]
        instructors = []

        instructor_profiles = {
            "nizam_mentor": {
                "email": "nizam.mentor@example.com",
                "first_name": "Nizam",
                "last_name": "Uddin",
            },
            "react_django_mentor": {
                "email": "mentor.fullstack@example.com",
                "first_name": "Full Stack",
                "last_name": "Mentor",
            },
        }

        for username in usernames:
            defaults = instructor_profiles.get(
                username,
                {
                    "email": f"{username}@example.com",
                    "first_name": username.replace("_", " ").title(),
                    "last_name": "Instructor",
                },
            )
            defaults["role"] = "instructor"

            # ensure instructor is assigned to the company
            if isinstance(defaults, dict):
                defaults['company'] = company

            user, created = User.objects.update_or_create(
                username=username,
                defaults=defaults,
            )
            user.set_password("password123")
            user.save()
            instructors.append(user)
            self.log_action(created, "instructor", user.username)

        return instructors

    def upsert_course(self, slug, title, category, price, company):
        now = timezone.now()
        course, created = Course.objects.update_or_create(
            slug=slug,
            company=company,
            defaults={
                "title": title,
                "description": (
                    "A practical full-stack development program where students build and deploy "
                    "a production-style LMS/job portal using Django, Django REST Framework, React, "
                    "Tailwind CSS, PostgreSQL, authentication, role-based dashboards, API integration, "
                    "payments-ready architecture, and deployment workflows."
                ),
                "category": category,
                "level": "intermediate",
                "price": price,
                "duration_hours": 96,
                "status": "published",
                "registration_start": now - timedelta(days=2),
                "registration_end": now + timedelta(days=45),
                "start_date": (now + timedelta(days=10)).date(),
            },
        )
        self.log_action(created, "course", course.title)
        return course

    def upsert_tools(self):
        tools_data = [
            {"name": "Python", "category": "Language", "icon_url": "https://cdn.jsdelivr.net/gh/devicons/devicon/icons/python/python-original.svg"},
            {"name": "Django", "category": "Backend", "icon_url": "https://cdn.jsdelivr.net/gh/devicons/devicon/icons/django/django-plain.svg"},
            {"name": "Django REST Framework", "category": "Backend", "icon_url": ""},
            {"name": "React", "category": "Frontend", "icon_url": "https://cdn.jsdelivr.net/gh/devicons/devicon/icons/react/react-original.svg"},
            {"name": "Tailwind CSS", "category": "Frontend", "icon_url": "https://cdn.jsdelivr.net/gh/devicons/devicon/icons/tailwindcss/tailwindcss-original.svg"},
            {"name": "PostgreSQL", "category": "Database", "icon_url": "https://cdn.jsdelivr.net/gh/devicons/devicon/icons/postgresql/postgresql-original.svg"},
            {"name": "Docker", "category": "DevOps", "icon_url": "https://cdn.jsdelivr.net/gh/devicons/devicon/icons/docker/docker-original.svg"},
            {"name": "GitHub Actions", "category": "DevOps", "icon_url": "https://cdn.jsdelivr.net/gh/devicons/devicon/icons/github/github-original.svg"},
            {"name": "Nginx", "category": "Deployment", "icon_url": "https://cdn.jsdelivr.net/gh/devicons/devicon/icons/nginx/nginx-original.svg"},
            {"name": "Redis", "category": "Performance", "icon_url": "https://cdn.jsdelivr.net/gh/devicons/devicon/icons/redis/redis-original.svg"},
        ]

        tools = []
        for item in tools_data:
            tool, created = Tool.objects.update_or_create(
                name=item["name"],
                defaults={
                    "category": item["category"],
                    "icon_url": item["icon_url"],
                },
            )
            tools.append(tool)
            self.log_action(created, "tool", tool.name)
        return tools

    def upsert_sections_and_lessons(self, course, reset_images=False, no_images=False):
        sections_data = [
            {
                "order": 1,
                "title": "Frontend Foundation with React",
                "description": "Build reusable React components, pages, routing, forms, state, and API-ready UI with Tailwind CSS.",
                "image_key": "section_frontend",
                "lessons": [
                    {"order": 1, "title": "React Project Setup with Vite", "description": "Create a scalable React app structure.", "free": True, "image_key": "lesson_react"},
                    {"order": 2, "title": "Tailwind Design System", "description": "Build buttons, cards, layouts, and responsive sections.", "free": True, "image_key": "lesson_react"},
                    {"order": 3, "title": "React Router and Page Layouts", "description": "Create public pages, dashboards, and protected routes.", "free": False, "image_key": "lesson_react"},
                    {"order": 4, "title": "Forms with Validation", "description": "Handle forms, error states, and reusable input components.", "free": False, "image_key": "lesson_react"},
                    {"order": 5, "title": "API Integration Pattern", "description": "Use Axios/fetch, loading states, and reusable API services.", "free": False, "image_key": "lesson_api"},
                ],
            },
            {
                "order": 2,
                "title": "Backend Foundation with Django",
                "description": "Design models, admin, views, authentication-ready structure, and clean Django project architecture.",
                "image_key": "section_backend",
                "lessons": [
                    {"order": 1, "title": "Django Project Architecture", "description": "Apps, settings, environment, and scalable folder structure.", "free": True, "image_key": "lesson_django"},
                    {"order": 2, "title": "Models and Migrations", "description": "Design normalized database models for real applications.", "free": False, "image_key": "lesson_django"},
                    {"order": 3, "title": "Django Admin Customization", "description": "Manage courses, users, enrollments, and content from admin.", "free": False, "image_key": "lesson_django"},
                    {"order": 4, "title": "Authentication and Roles", "description": "Student, instructor, and admin role-based access.", "free": False, "image_key": "lesson_django"},
                    {"order": 5, "title": "Media Uploads and Storage", "description": "Handle images, files, validation, and MEDIA settings.", "free": False, "image_key": "lesson_django"},
                ],
            },
            {
                "order": 3,
                "title": "REST API with Django REST Framework",
                "description": "Create professional APIs for React, including serializers, permissions, pagination, and filtering.",
                "image_key": "section_api",
                "lessons": [
                    {"order": 1, "title": "DRF Serializers", "description": "Convert Django models to clean JSON API responses.", "free": True, "image_key": "lesson_api"},
                    {"order": 2, "title": "ViewSets and Routers", "description": "Build maintainable CRUD endpoints quickly.", "free": False, "image_key": "lesson_api"},
                    {"order": 3, "title": "Permissions and JWT", "description": "Secure APIs with authenticated role-based access.", "free": False, "image_key": "lesson_api"},
                    {"order": 4, "title": "Filtering, Search and Pagination", "description": "Make APIs production-friendly for large datasets.", "free": False, "image_key": "lesson_api"},
                    {"order": 5, "title": "API Documentation", "description": "Generate browsable and shareable API docs.", "free": False, "image_key": "lesson_api"},
                ],
            },
            {
                "order": 4,
                "title": "Full Stack Integration and Deployment",
                "description": "Connect React with Django APIs, deploy with PostgreSQL, Docker, Nginx, and production settings.",
                "image_key": "section_deployment",
                "lessons": [
                    {"order": 1, "title": "Connecting React with DRF", "description": "Authentication, tokens, headers, and protected routes.", "free": False, "image_key": "lesson_api"},
                    {"order": 2, "title": "Production Environment Variables", "description": "Secure environment setup for frontend and backend.", "free": False, "image_key": "lesson_deploy"},
                    {"order": 3, "title": "Dockerizing Django and React", "description": "Create Dockerfiles and compose services.", "free": False, "image_key": "lesson_deploy"},
                    {"order": 4, "title": "Nginx and Static/Media Files", "description": "Serve production assets and uploaded media correctly.", "free": False, "image_key": "lesson_deploy"},
                    {"order": 5, "title": "Final Capstone Project", "description": "Build and deploy a complete LMS/job portal feature set.", "free": False, "image_key": "lesson_deploy"},
                ],
            },
        ]

        existing_section_ids = []
        for section_item in sections_data:
            section, created = Section.objects.update_or_create(
                course=course,
                order=section_item["order"],
                defaults={
                    "title": section_item["title"],
                    "description": section_item["description"],
                },
            )
            existing_section_ids.append(section.id)
            self.log_action(created, "section", section.title)

            if not no_images and hasattr(section, "image"):
                self.set_image_if_needed(
                    obj=section,
                    field_name="image",
                    url=UNSPLASH_IMAGES[section_item["image_key"]],
                    filename=f"{course.slug}-section-{section.order}.jpg",
                    reset=reset_images,
                )

            existing_lesson_ids = []
            for lesson_item in section_item["lessons"]:
                lesson, lesson_created = Lesson.objects.update_or_create(
                    section=section,
                    order=lesson_item["order"],
                    defaults={
                        "title": lesson_item["title"],
                        "description": lesson_item["description"],
                        "content": self.lesson_content(section.title, lesson_item["title"]),
                        "is_free": lesson_item["free"],
                        "video_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ" if lesson_item["free"] else "",
                    },
                )
                existing_lesson_ids.append(lesson.id)
                self.log_action(lesson_created, "lesson", lesson.title)

                if not no_images and hasattr(lesson, "thumbnail"):
                    self.set_image_if_needed(
                        obj=lesson,
                        field_name="thumbnail",
                        url=UNSPLASH_IMAGES[lesson_item["image_key"]],
                        filename=f"{course.slug}-section-{section.order}-lesson-{lesson.order}.jpg",
                        reset=reset_images,
                    )

            # Remove old lessons under this section that are no longer in the seed list.
            section.lessons.exclude(id__in=existing_lesson_ids).delete()

        # Remove old sections for this course that are no longer in the seed list.
        course.sections.exclude(id__in=existing_section_ids).delete()

    def lesson_content(self, section_title, lesson_title):
        return f"""
# {lesson_title}

This lesson belongs to **{section_title}**.

You will learn:

1. Core concept explanation
2. Hands-on implementation
3. Common mistakes and debugging
4. Real-world best practices
5. Assignment for practice

By the end of this lesson, students should be able to apply the concept in a production-style Django + React project.
""".strip()

    def upsert_benefits(self, course):
        data = [
            (1, "Build a production-style full-stack project", "Create a real Django + React application with API, dashboard, authentication, and deployment structure."),
            (2, "Master Django REST Framework", "Design clean serializers, ViewSets, permissions, filtering, pagination, and API documentation."),
            (3, "Create modern React interfaces", "Build reusable UI components, routing, forms, API states, and Tailwind layouts."),
            (4, "Understand deployment workflow", "Prepare PostgreSQL, Docker, Nginx, static files, media files, and environment variables."),
            (5, "Portfolio-ready capstone", "Complete a project that can be shown to employers, clients, or internship panels."),
            (6, "Career and freelancing confidence", "Learn how full-stack features are planned, estimated, built, tested, and delivered."),
        ]
        self.upsert_ordered_model(Benefit, course, data, description_field=True)

    def upsert_requirements(self, course):
        data = [
            (1, "Basic Python knowledge", "Variables, functions, classes, virtual environments, and package installation."),
            (2, "Basic HTML, CSS, and JavaScript", "Enough knowledge to understand React components and Tailwind layouts."),
            (3, "Laptop or desktop computer", "Any modern system that can run Python, Node.js, PostgreSQL, and a code editor."),
            (4, "Commitment to practice", "Students should build along with each lesson and complete assignments."),
        ]
        self.upsert_ordered_model(Requirement, course, data, description_field=True)

    def upsert_faqs(self, course):
        data = [
            (1, "Is this course beginner friendly?", "Yes, but it is best if you already know basic Python, HTML, CSS, and JavaScript."),
            (2, "Will I build a real project?", "Yes. You will build a production-style Django + React full-stack application step by step."),
            (3, "Does the course cover API authentication?", "Yes. The course explains JWT/session-ready API patterns and protected React routes."),
            (4, "Will deployment be covered?", "Yes. Deployment architecture, Docker, Nginx, PostgreSQL, static files, and media handling are covered."),
            (5, "Can I use this for freelancing?", "Yes. The course is designed around practical features clients commonly request."),
            (6, "How long will I have access?", "You will have lifetime access to recorded lessons and course materials, depending on your platform policy."),
        ]
        for order, question, answer in data:
            faq, created = FAQ.objects.update_or_create(
                course=course,
                question=question,
                defaults={"answer": answer, "order": order},
            )
            self.log_action(created, "faq", faq.question)
        course.faqs.exclude(question__in=[item[1] for item in data]).delete()

    def upsert_audiences(self, course):
        data = [
            (1, "Django Developers", "Backend developers who want to become full-stack with React.", "linear-gradient(135deg,#16a34a,#0f766e)"),
            (2, "React Developers", "Frontend developers who want to understand Django and APIs.", "linear-gradient(135deg,#0284c7,#2563eb)"),
            (3, "CSE/IT Students", "Students who need practical project experience beyond academic theory.", "linear-gradient(135deg,#7c3aed,#db2777)"),
            (4, "Freelancers", "Developers who want to build client-ready dashboards, portals, and business apps.", "linear-gradient(135deg,#ea580c,#dc2626)"),
            (5, "Career Switchers", "Learners preparing for junior full-stack developer roles.", "linear-gradient(135deg,#0891b2,#4f46e5)"),
            (6, "Startup Builders", "Founders and developers who want to build MVPs fast and cleanly.", "linear-gradient(135deg,#0f172a,#334155)"),
        ]
        active_titles = []
        for order, title, description, bg in data:
            active_titles.append(title)
            audience, created = CourseAudience.objects.update_or_create(
                course=course,
                title=title,
                defaults={
                    "description": description,
                    "icon_bg": bg,
                    "icon_svg": self.default_audience_icon_svg(),
                    "order": order,
                },
            )
            self.log_action(created, "audience", audience.title)
        course.audiences.exclude(title__in=active_titles).delete()

    def default_audience_icon_svg(self):
        return """
<svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
</svg>
""".strip()

    def upsert_ordered_model(self, model_class, course, data, description_field=False):
        active_titles = []
        for order, title, description in data:
            active_titles.append(title)
            defaults = {"order": order}
            if description_field:
                defaults["description"] = description
            obj, created = model_class.objects.update_or_create(
                course=course,
                title=title,
                defaults=defaults,
            )
            self.log_action(created, model_class.__name__.lower(), title)
        model_class.objects.filter(course=course).exclude(title__in=active_titles).delete()

    def upsert_batch(self, course, instructor):
        batch, created = Batch.objects.update_or_create(
            course=course,
            name="Full Stack Batch 01",
            defaults={
                "instructor": instructor,
                "start_date": timezone.now().date() + timedelta(days=10),
                "end_date": timezone.now().date() + timedelta(days=100),
                "max_students": 50,
                "status": "upcoming",
                "company": course.company,
            },
        )
        self.log_action(created, "batch", batch.name)
        return batch

    def set_image_if_needed(self, obj, field_name, url, filename, reset=False):
        field_file = getattr(obj, field_name, None)
        has_file = bool(field_file and getattr(field_file, "name", ""))

        if has_file and not reset:
            self.stdout.write(f"Image exists, skipped: {obj} -> {field_name}")
            return

        if has_file and reset:
            try:
                field_file.delete(save=False)
            except Exception as exc:
                self.stdout.write(self.style.WARNING(f"Could not delete old image for {obj}: {exc}"))

        try:
            downloaded_path = self.download_image(url, filename)
            with open(downloaded_path, "rb") as image_file:
                getattr(obj, field_name).save(filename, File(image_file), save=True)
            os.remove(downloaded_path)
            self.stdout.write(self.style.SUCCESS(f"Uploaded image: {obj} -> {field_name}"))
        except Exception as exc:
            self.stdout.write(self.style.WARNING(f"Image download/upload failed for {obj}: {exc}"))

    def download_image(self, url, filename):
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            raise ValueError("Only HTTP/HTTPS image URLs are allowed.")

        response = requests.get(
            url,
            timeout=25,
            headers={
                "User-Agent": "Mozilla/5.0 Django Seed Command",
                "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
            },
        )
        response.raise_for_status()

        content_type = response.headers.get("content-type", "")
        if "image" not in content_type:
            raise ValueError(f"URL did not return an image. content-type={content_type}")

        safe_filename = slugify(os.path.splitext(filename)[0]) + os.path.splitext(filename)[1].lower()
        if not os.path.splitext(safe_filename)[1]:
            safe_filename += ".jpg"

        temp_dir = tempfile.gettempdir()
        path = os.path.join(temp_dir, safe_filename)
        with open(path, "wb") as file_obj:
            file_obj.write(response.content)
        return path

    def log_action(self, created, model_name, label):
        action = "Created" if created else "Updated"
        style = self.style.SUCCESS if created else self.style.NOTICE
        self.stdout.write(style(f"{action} {model_name}: {label}"))
