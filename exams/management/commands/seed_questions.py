import random
from django.core.management.base import BaseCommand
from accounts.models import Company
from core.models import Category
from exams.models import Question

class Command(BaseCommand):
    help = 'Seeds 30 realistic MCQ questions for BSDI'

    def handle(self, *args, **options):
        # 1. Find the company
        try:
            company = Company.objects.get(domain='bsdi.proto')
        except Company.DoesNotExist:
            self.stdout.write(self.style.ERROR('Company with domain bsdi.proto not found.'))
            return

        # 2. Get or Create a Category
        category, _ = Category.objects.get_or_create(
            name='General Knowledge',
            company=company
        )

        # 3. Questions Data
        questions_data = [
            {
                "text": "What does CPU stand for?",
                "options": ["Central Process Unit", "Central Processing Unit", "Computer Personal Unit", "Central Processor Unifier"],
                "correct": "B"
            },
            {
                "text": "Which programming language is primarily used for Android app development?",
                "options": ["Swift", "Kotlin", "C#", "PHP"],
                "correct": "B"
            },
            {
                "text": "What is the main purpose of a Firewall?",
                "options": ["Monitoring", "Data Storage", "Security", "Networking"],
                "correct": "C"
            },
            {
                "text": "Which protocol is used to send emails?",
                "options": ["HTTP", "FTP", "SMTP", "SSH"],
                "correct": "C"
            },
            {
                "text": "What is the capital of Bangladesh?",
                "options": ["Chittagong", "Dhaka", "Sylhet", "Rajshahi"],
                "correct": "B"
            },
            {
                "text": "In Python, which keyword is used to define a function?",
                "options": ["func", "define", "def", "lambda"],
                "correct": "C"
            },
            {
                "text": "What is the default port for HTTP?",
                "options": ["443", "21", "80", "8080"],
                "correct": "C"
            },
            {
                "text": "Which data structure follows the LIFO (Last In First Out) principle?",
                "options": ["Queue", "Linked List", "Stack", "Tree"],
                "correct": "C"
            },
            {
                "text": "Who is known as the father of the World Wide Web?",
                "options": ["Steve Jobs", "Tim Berners-Lee", "Bill Gates", "Mark Zuckerberg"],
                "correct": "B"
            },
            {
                "text": "What is the full form of RAM?",
                "options": ["Read Access Memory", "Random Access Memory", "Real Access Memory", "Run Access Memory"],
                "correct": "B"
            },
            {
                "text": "Which company developed the Java programming language?",
                "options": ["Microsoft", "Sun Microsystems", "Apple", "Google"],
                "correct": "B"
            },
            {
                "text": "What does SQL stand for?",
                "options": ["Simple Query Language", "Structured Query Language", "System Query Language", "Standard Query Language"],
                "correct": "B"
            },
            {
                "text": "Which of the following is a NoSQL database?",
                "options": ["MySQL", "PostgreSQL", "MongoDB", "Oracle"],
                "correct": "C"
            },
            {
                "text": "What is the extension of a Python file?",
                "options": [".js", ".py", ".html", ".css"],
                "correct": "B"
            },
            {
                "text": "Which tag is used for the largest heading in HTML?",
                "options": ["<h6>", "<head>", "<h1>", "<header>"],
                "correct": "C"
            },
            {
                "text": "What is the main function of an Operating System?",
                "options": ["Word Processing", "Resource Management", "Web Browsing", "Emailing"],
                "correct": "B"
            },
            {
                "text": "Which of these is a CSS framework?",
                "options": ["React", "Django", "Bootstrap", "Laravel"],
                "correct": "C"
            },
            {
                "text": "What does UI stand for in design?",
                "options": ["User Interaction", "User Interface", "Universal Interface", "User Integration"],
                "correct": "B"
            },
            {
                "text": "Which of the following is a version control system?",
                "options": ["Docker", "Git", "Kubernetes", "Jenkins"],
                "correct": "B"
            },
            {
                "text": "What is the full form of URL?",
                "options": ["Uniform Resource Locator", "Universal Resource Locator", "United Resource Link", "Uniform Resource Link"],
                "correct": "A"
            },
            {
                "text": "Which cloud provider offers AWS?",
                "options": ["Google", "Microsoft", "Amazon", "IBM"],
                "correct": "C"
            },
            {
                "text": "What is the binary representation of the decimal number 5?",
                "options": ["100", "101", "110", "111"],
                "correct": "B"
            },
            {
                "text": "Which symbol is used for comments in Python?",
                "options": ["//", "/*", "#", "--"],
                "correct": "C"
            },
            {
                "text": "What does API stand for?",
                "options": ["Application Program Integration", "Application Programming Interface", "Access Program Interface", "Automated Program Interface"],
                "correct": "B"
            },
            {
                "text": "Which of the following is a frontend library?",
                "options": ["Express", "React", "Flask", "Spring"],
                "correct": "B"
            },
            {
                "text": "What is the primary use of Docker?",
                "options": ["Text Editing", "Containerization", "Game Development", "Video Editing"],
                "correct": "B"
            },
            {
                "text": "Which language is used for styling web pages?",
                "options": ["HTML", "CSS", "Python", "SQL"],
                "correct": "B"
            },
            {
                "text": "What does DNS stand for?",
                "options": ["Domain Name System", "Data Name System", "Digital Name System", "Domain Network System"],
                "correct": "A"
            },
            {
                "text": "Which unit is used to measure processor speed?",
                "options": ["MB", "GB", "GHz", "Mbps"],
                "correct": "C"
            },
            {
                "text": "What is the latest version of HTML?",
                "options": ["HTML4", "HTML5", "HTML6", "XHTML"],
                "correct": "B"
            }
        ]

        # 4. Create Questions
        created_count = 0
        for item in questions_data:
            Question.objects.create(
                company=company,
                category=category,
                question_text=item["text"],
                option_a=item["options"][0],
                option_b=item["options"][1],
                option_c=item["options"][2],
                option_d=item["options"][3],
                correct_option=item["correct"]
            )
            created_count += 1

        self.stdout.write(self.style.SUCCESS(f'Successfully seeded {created_count} questions for BSDI.'))
