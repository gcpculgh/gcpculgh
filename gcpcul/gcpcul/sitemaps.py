from django.contrib import sitemaps
from django.urls import reverse

class StaticViewSitemap(sitemaps.Sitemap):
    priority = 0.8
    changefreq = 'weekly'
    protocol = 'https'

    def items(self):
        # List all the 'name' attributes of your main page URLs
        return ['home', 'about', 'products', 'calculator', 'gallery', 'news', 'contact']

    def location(self, item):
        return reverse(item)