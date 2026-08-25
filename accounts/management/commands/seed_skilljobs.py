from django.core.management.base import BaseCommand
from accounts.models import Company


class Command(BaseCommand):
    help = "Seed Skill Jobs main platform data"

    def handle(self, *args, **kwargs):

        company, _ = Company.objects.update_or_create(
            slug="skilljobs",
            defaults={
                "name": "Skill Jobs",
                "domain": "skilljobs.proto",

                # HERO
                "hero_badge": "A Concern of Daffodil Group",
                "hero_title": "আপনার ক্যারিয়ার শুরু করুন আমাদের সাথে",
                "hero_subtitle": "লাইভ ক্লাস, ইন্ডাস্ট্রি এক্সপার্ট এবং প্র্যাকটিক্যাল প্রজেক্টের মাধ্যমে ক্যারিয়ার গড়ুন।",

                "hero_primary_text": "কোর্স দেখুন",
                "hero_primary_link": "/courses/",
                "hero_secondary_text": "আমাদের সম্পর্কে",
                "hero_secondary_link": "/about/",

                # STATS
                "total_students": "30,000+",
                "total_batches": "120+",
                "total_mentors": "50+",

                # FEATURED
                "featured_title": "জনপ্রিয় কোর্স",
                "featured_subtitle": "সর্বাধিক চাহিদাসম্পন্ন আইটি স্কিলগুলো শিখুন",

                # CTA
                "cta_title": "আজই আপনার ক্যারিয়ার শুরু করুন",
                "cta_subtitle": "প্রফেশনাল ট্রেনিং নিয়ে নিজের ভবিষ্যৎ তৈরি করুন",
                "cta_phone": "+8801847334766",

                # FOOTER
                "footer_text": "Skill Jobs একটি আধুনিক অনলাইন লার্নিং প্ল্যাটফর্ম যেখানে আপনি বাস্তবমুখী দক্ষতা অর্জন করতে পারেন।",
                "contact_phone": "+8801847334766",
                "contact_email": "support@skill.jobs",

                # SEO
                "meta_title": "Skill Jobs Training Platform",
                "meta_description": "বাংলাদেশের অন্যতম সেরা আইটি ট্রেনিং প্ল্যাটফর্ম।",
                "meta_keywords": "skill jobs, training, IT course, bangladesh",

                # OG
                "og_title": "Skill Jobs প্রশিক্ষণ প্ল্যাটফর্ম",
                "og_description": "আপনার ক্যারিয়ার গড়ুন Skill Jobs এর সাথে",

                "is_active": True,
            }
        )

        self.stdout.write(self.style.SUCCESS("✅ Skill Jobs seeded successfully"))