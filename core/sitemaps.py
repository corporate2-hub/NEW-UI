from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from courses.models import Course


class StaticSitemap(Sitemap):
    """Sitemap for static pages: home, about, courses list."""

    priority = 0.8
    changefreq = "weekly"

    def __init__(self, company):
        self.company = company

    def items(self):
        return [
            ("core:home", {}, 1.0),
            ("core:about", {}, 0.7),
            ("courses:course_list", {}, 0.9),
        ]

    def location(self, item):
        name, kwargs, _priority = item
        return reverse(name, kwargs=kwargs)

    def priority(self, item):  # noqa: F811 – override class attr
        _name, _kwargs, prio = item
        return prio

    def lastmod(self, item):
        return None


class CourseSitemap(Sitemap):
    """Sitemap for individual course detail pages, scoped to the current tenant."""

    changefreq = "weekly"
    priority = 0.9

    def __init__(self, company):
        self.company = company

    def items(self):
        if not self.company:
            return Course.objects.none()
        return Course.objects.filter(
            company=self.company, status="published"
        ).only("slug", "updated_at")

    def location(self, course):
        return reverse("courses:course_detail", kwargs={"slug": course.slug})

    def lastmod(self, course):
        return course.updated_at
