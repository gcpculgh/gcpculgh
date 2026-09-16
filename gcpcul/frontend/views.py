from django.shortcuts import render, get_object_or_404, redirect
from .models import * 
from administrator.models import *
from django.contrib import messages
from administrator.forms import * 


# Create your views here.
def home(request):
    context = {
        # Grabs the 3 newest articles flagged for the top section
        'happenings': NewsArticle.objects.filter(is_recent_happening=True)[:3],
        
        # Grabs the 3 newest articles flagged for the bottom section
        'blogs': NewsArticle.objects.filter(is_blog_post=True)[:3],
    }
    return render(request, 'index.html', context)

def products(request):
    return render(request, 'products.html')

def about(request):
    return render(request, 'about.html')

def calculator(request): 
    return render(request, 'calculator.html')

def gallery(request):
    return render(request, 'gallery.html')

def downloads(request): 
    
    # We order them so the newest/most relevant ones show up first
    forms = DownloadableForm.objects.all().order_by('title')
    reports = AGMReport.objects.all().order_by('-year')
    
    # 3. Pack them into the context dictionary
    context = {
        'forms': forms,
        'reports': reports,
    }
    
    # 4. Pass the context to the template
    return render(request, 'downloads.html', context)


def news(request):
    # Grabs the featured article for the Hero (Must be published)
    featured_article = NewsArticle.objects.filter(is_featured=True, status='published').first()

    # Grabs ALL articles (Must be published)
    if featured_article:
        articles = NewsArticle.objects.filter(is_blog_post=True, status='published').exclude(id=featured_article.id)
    else:
        articles = NewsArticle.objects.filter(is_blog_post=True, status='published')

    context = {
        'featured': featured_article,
        'articles': articles,
    }
    return render(request, 'news.html', context)


def article_detail_view(request, article_id):
    article = get_object_or_404(NewsArticle, id=article_id)
    
    # Grab two random articles for the "Keep Reading" footer
    related = NewsArticle.objects.exclude(id=article.id).order_by('?')[:2]
    
    return render(request, 'article_detail.html', {'article': article, 'related': related})


def login(request):
    return render(request, 'login.html')

def contact(request):
    return render(request, 'contact.html')

def email_image(request):
    return render(request, "email-image.html")

def handle_waitlist_signup(request):
    if request.method == 'POST':
        form = PortalWaitlistForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "You're on the list! We'll email you the moment the portal opens.")
        else:
            error_msg = form.errors.get('email', ['Invalid email address.'])[0]
            messages.error(request, error_msg)
    return redirect('home')  # Or change to your landing page name if different


def handle_newsletter_signup(request):
    if request.method == 'POST':
        form = NewsletterForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Thanks for subscribing to GCPCUL financial updates.")
        else:
            error_msg = form.errors.get('email', ['Invalid email address.'])[0]
            messages.error(request, error_msg)
    return redirect('home')  # Or your relevant view/page name
