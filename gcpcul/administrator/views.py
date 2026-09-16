from django.shortcuts import render, redirect
from .models import *
from django.db.models import Q
from .forms import *

# Create your views here.
def main_dashboard(request):
    return render(request, 'admin_dashboard.html')



def portal_news_list(request):
    # 1. Search logic for News Articles
    query = request.GET.get('q', '')
    if query:
        articles = NewsArticle.objects.filter(
            Q(title__icontains=query) | Q(author__icontains=query)
        ).order_by('-published_date')
    else:
        articles = NewsArticle.objects.all().order_by('-published_date')

    # 2. Fetch all Announcements for the new dashboard panel
    announcements = Announcement.objects.all().order_by('-created_at')

    return render(request, 'portal/news_list.html', {
        'articles': articles,
        'announcements': announcements,
        'query': query
    })

