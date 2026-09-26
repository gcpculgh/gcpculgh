from django.shortcuts import render, get_object_or_404, redirect
from administrator.models import *
from django.contrib import messages
from administrator.forms import * 
from administrator.models import Document 



# Create your views here.
def home(request):
    context = {
        # Grabs the 3 newest articles flagged for the top section
        'happenings': NewsArticle.objects.filter(status='published').order_by('-published_at')[:3],
        
        # Grabs the 3 newest articles flagged for the bottom section
        'blogs': NewsArticle.objects.filter(status='published', category='guide').order_by('-published_at')[:3],
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
    # Query the unified table by category
    forms = Document.objects.filter(category="form").exclude(document="")
    reports = Document.objects.filter(category="report").exclude(document="")
    agm_docs = Document.objects.filter(category="agm").exclude(document="")
    policies = Document.objects.filter(category="legal").exclude(document="")

    context = {
        "forms": forms,
        "reports": reports,
        "agm_docs": agm_docs,
        "policies": policies,
    }
    return render(request, 'downloads.html', context)

def news(request):
    # Fetch all published articles once, ordered by newest first
    published_articles = NewsArticle.objects.filter(status='published').order_by('-created_at')
    
    # Grab the newest one for the hero section
    featured_article = published_articles.first()

    # Exclude the featured article from the grid below so it doesn't appear twice
    if featured_article:
        articles = published_articles.exclude(pk=featured_article.pk)
    else:
        articles = published_articles

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


def member_portal(request):
    return render(request, 'member_portal.html')

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
