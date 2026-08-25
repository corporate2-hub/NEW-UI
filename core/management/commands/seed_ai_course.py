"""
File: courses/management/commands/seed_ai_course.py

Run:
    python manage.py seed_ai_course
    python manage.py seed_ai_course --reset-images

Creates a COMPLETE Data Science + Agentic AI course.
Idempotent: safe to re-run (updates existing data).
"""

import os
import tempfile
from decimal import Decimal
from datetime import timedelta, date
from urllib.parse import urlparse

import requests
from django.core.files import File
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from core.models import Category
from courses.models import Course, Section, Lesson, Tool, Benefit, Requirement, FAQ, CourseAudience
from enrollments.models import Batch
from accounts.models import Company

User = get_user_model()

IMAGES = {
    "banner": "https://images.unsplash.com/photo-1677442136019-21780ecad995?w=1600",
    "section": "https://images.unsplash.com/photo-1555949963-aa79dcee981c?w=1200",
    "lesson": "https://images.unsplash.com/photo-1518779578993-ec3579fee39f?w=900",
}

class Command(BaseCommand):
    help = "Seed Data Science + Agentic AI Course"

    def add_arguments(self, parser):
        parser.add_argument(
            "--company",
            default="default",
            help="Company slug to assign created company-scoped objects to.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        slug = "data-science-agentic-ai"

        company_slug = options.get("company") if options else "default"
        company, _ = Company.objects.get_or_create(
            slug=company_slug,
            defaults={"name": company_slug.replace("-"," ").title()},
        )

        category, _ = Category.objects.get_or_create(
            name="Data Science & AI",
            defaults={"description": "AI, ML, and Agentic systems"}
        )

        instructor, _ = User.objects.update_or_create(
            username="ai_mentor",
            defaults={
                "email": "ai@mentor.com",
                "first_name": "AI",
                "last_name": "Mentor",
                "role": "instructor",
                "company": company,
            }
        )
        instructor.set_password("password123")
        instructor.save()

        course, _ = Course.objects.update_or_create(
            slug=slug,
            company=company,
            defaults={
                "title": "Data Science & Agentic AI Masterclass",
                "description": "Learn Data Science, Machine Learning, and build AI Agents using LLMs, LangChain, and RAG systems.",
                "category": category,
                "level": "intermediate",
                "price": Decimal("10000"),
                "duration_hours": 120,
                "status": "published",
                # Explicit registration & start dates per request
                "registration_start": date(2026, 4, 25),
                "registration_end": date(2026, 6, 11),
                "start_date": date(2026, 5, 7),
            }
        )

        course.instructors.set([instructor])

        self.download_image(course, "banner_image", IMAGES["banner"])

        # Tools (production-level set)
        tools_list = [
            "Python","NumPy","Pandas","Matplotlib","Seaborn",
            "Scikit-learn","TensorFlow","PyTorch",
            "OpenAI API","LangChain","Pinecone","FAISS",
            "FastAPI","Docker"
        ]
        tools = []
        for name in tools_list:
            t, _ = Tool.objects.get_or_create(name=name)
            tools.append(t)
        course.tools.set(tools)

        # Sections and lessons (rich, production-level curriculum)
        sections = [
            {
                "title": "Python & Data Science Foundations",
                "lessons": [
                    "Python Refresher for Data Science",
                    "NumPy Deep Dive",
                    "Pandas Data Analysis",
                    "Data Cleaning & Preprocessing",
                    "Exploratory Data Analysis (EDA)",
                ]
            },
            {
                "title": "Data Visualization & Storytelling",
                "lessons": [
                    "Matplotlib Mastery",
                    "Seaborn Advanced Plots",
                    "Dashboard Thinking",
                    "Real Dataset Visualization Project",
                ]
            },
            {
                "title": "Machine Learning (Core)",
                "lessons": [
                    "Supervised vs Unsupervised Learning",
                    "Regression Models",
                    "Classification Models",
                    "Model Evaluation & Metrics",
                    "Feature Engineering",
                    "End-to-End ML Project",
                ]
            },
            {
                "title": "Deep Learning",
                "lessons": [
                    "Neural Networks Basics",
                    "TensorFlow vs PyTorch",
                    "CNN for Image Tasks",
                    "RNN & Sequence Models",
                ]
            },
            {
                "title": "LLMs & Generative AI",
                "lessons": [
                    "How GPT & LLMs Work",
                    "Prompt Engineering",
                    "Fine-tuning Basics",
                    "OpenAI API Integration",
                ]
            },
            {
                "title": "Agentic AI Systems",
                "lessons": [
                    "Intro to Agentic AI",
                    "LangChain Chains & Agents",
                    "Tools, Memory & Planning",
                    "Multi-Agent Systems",
                    "Autonomous Task Execution",
                ]
            },
            {
                "title": "RAG & Vector Databases",
                "lessons": [
                    "What is RAG",
                    "Embeddings & Vector Search",
                    "Pinecone / FAISS",
                    "Build AI Knowledge Assistant",
                ]
            },
            {
                "title": "AI Projects (Real World)",
                "lessons": [
                    "AI Chatbot with Memory",
                    "Resume Analyzer AI",
                    "Document Q&A System",
                    "AI SaaS Mini Project",
                ]
            },
        ]

        for i, section_data in enumerate(sections, start=1):
            sec, _ = Section.objects.update_or_create(
                course=course,
                order=i,
                defaults={"title": section_data["title"]}
            )

            self.download_image(sec, "image", IMAGES["section"])

            for j, lesson_title in enumerate(section_data["lessons"], start=1):
                lesson, _ = Lesson.objects.update_or_create(
                    section=sec,
                    order=j,
                    defaults={
                        "title": lesson_title,
                        "content": f"{lesson_title} practical implementation",
                        "is_free": j == 1,
                    }
                )
                self.download_image(lesson, "thumbnail", IMAGES["lesson"])

        # Benefits (upgraded)
        benefits = [
            "Master Data Science from scratch",
            "Build real Machine Learning models",
            "Create AI Agents using LangChain",
            "Develop RAG-based systems",
            "Work on real-world AI projects",
            "Become job-ready AI engineer",
        ]
        for i, b in enumerate(benefits, 1):
            Benefit.objects.update_or_create(
                course=course,
                title=b,
                defaults={"order": i}
            )

        # Requirements (expanded)
        requirements = [
            "Basic Python",
            "Basic statistics and probability",
            "Familiarity with linear algebra (vectors & matrices)",
            "Comfort using the command line",
            "Basic experience with Git/GitHub",
        ]
        for i, r in enumerate(requirements, 1):
            Requirement.objects.update_or_create(
                course=course,
                title=r,
                defaults={"order": i}
            )

        # FAQs (expanded)
        faqs = [
            {"question": "Do I need prior experience?", "answer": "No — the course starts with fundamentals and builds up to advanced topics. Some basic Python familiarity helps."},
            {"question": "How long will I have access?", "answer": "You will have lifetime access to course materials, including recordings and code samples."},
            {"question": "Are there projects and assessments?", "answer": "Yes — multiple real-world projects with starter code, datasets, and evaluation rubrics."},
            {"question": "Is mentorship or instructor support available?", "answer": "Yes — mentorship via office hours, community channels, and guided feedback on projects."},
            {"question": "What are the payment and refund policies?", "answer": "Flexible payment options are available; please check the pricing page or contact support for refund details."},
        ]
        for i, f in enumerate(faqs, 1):
            FAQ.objects.update_or_create(
                course=course,
                question=f["question"],
                defaults={"answer": f["answer"], "order": i}
            )

        # Audiences (upgraded)
        audiences = [
            "Aspiring Data Scientists",
            "Software Developers",
            "AI Enthusiasts",
            "Freelancers",
            "Students",
        ]
        for i, a in enumerate(audiences, 1):
            CourseAudience.objects.update_or_create(
                course=course,
                title=a,
                defaults={"order": i}
            )

        Batch.objects.update_or_create(
            course=course,
            name="AI Batch 01",
            defaults={
                "instructor": instructor,
                # align batch dates with course start
                "start_date": course.start_date,
                "end_date": course.start_date + timedelta(days=60),
                "max_students": 50,
                "status": "upcoming",
                "company": course.company,
            }
        )

        self.stdout.write(self.style.SUCCESS("AI Course Seeded Successfully"))

    def download_image(self, obj, field, url):
        try:
            r = requests.get(url)
            r.raise_for_status()
            path = os.path.join(tempfile.gettempdir(), "img.jpg")
            with open(path, "wb") as f:
                f.write(r.content)
            getattr(obj, field).save("img.jpg", File(open(path,'rb')), save=True)
        except Exception:
            pass
