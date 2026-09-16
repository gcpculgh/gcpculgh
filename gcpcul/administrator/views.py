from django.shortcuts import render, redirect
from .models import *
from django.db.models import Q
from .forms import *
from django.contrib import messages

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


def handle_waitlist_signup(request):
    if request.method == 'POST':
        form = PortalWaitlistForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "You're on the list! We'll email you the moment the portal opens.")
        else:
            # Grab the specific error message from the form validator
            error_msg = form.errors.get('email', ['Invalid email address.'])[0]
            messages.error(request, error_msg)
    return redirect('home')  # Or wherever your landing/login page is


def handle_newsletter_signup(request):
    if request.method == 'POST':
        form = NewsletterForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Thanks for subscribing to GCPCUL financial updates.")
        else:
            error_msg = form.errors.get('email', ['Invalid email address.'])[0]
            messages.error(request, error_msg)
    return redirect('home')