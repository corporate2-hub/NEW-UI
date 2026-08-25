from django.core.management.base import BaseCommand
from accounts.models import Company


class Command(BaseCommand):
    help = "Seed BSDI company data"


    def handle(self, *args, **kwargs):

        company, _ = Company.objects.update_or_create(
            slug="bsdi",
            defaults={
                "name": "Bangladesh Skill Development Institute",
                "domain": "bsdi.proto",

                # HERO
                "hero_badge": "Government Approved Training Institute",
                "hero_title": "Skill Development for Future Bangladesh",
                "hero_subtitle": "আমাদের লক্ষ্য দেশের যুবসমাজকে দক্ষ করে তোলা এবং কর্মসংস্থানের সুযোগ তৈরি করা।",

                "hero_primary_text": "Courses",
                "hero_primary_link": "/courses/",
                "hero_secondary_text": "About BSDI",
                "hero_secondary_link": "/about/",

                # STATS
                "total_students": "15,000+",
                "total_batches": "80+",
                "total_mentors": "25+",

                # FEATURED
                "featured_title": "Training Programs",
                "featured_subtitle": "Industry-relevant skills with real-world training",

                # CTA
                "cta_title": "Join BSDI Today",
                "cta_subtitle": "Empowering youth with practical skills and career opportunities",
                "cta_phone": "+8801700000000",

                # FOOTER
                "footer_text": "BSDI একটি স্কিল ডেভেলপমেন্ট ইনস্টিটিউট যা বাংলাদেশের তরুণদের দক্ষ করে তুলতে কাজ করে।",
                "contact_phone": "+8801700000000",
                "contact_email": "info@bsdi.org",

                # SEO
                "meta_title": "BSDI - Bangladesh Skill Development Institute",
                "meta_description": "Professional training and skill development programs in Bangladesh.",
                "meta_keywords": "bsdi, training institute, bangladesh skill development",

                # OG
                "og_title": "BSDI Training Institute",
                "og_description": "Build your future with BSDI training programs",

                "is_active": True,
            }
        )

        self.stdout.write(self.style.SUCCESS("✅ BSDI seeded successfully"))