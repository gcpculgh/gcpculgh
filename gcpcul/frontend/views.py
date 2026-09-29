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
    # Static Data Hydration for the Team Page
    team_data = {
        "Board of Directors": [
            {"name": "Dr. Paul Owusu Donkor", "role": "BOD Chairman", "image": "dr-paul-donkor.jpg"},
            {"name": "Dr. Brenda Yayra Opong", "role": "BOD Vice Chairperson", "image": "dr-brenda-opong.jpg"},
            {"name": "Dr. Anna Kwarley Quartey", "role": "BOD Member", "image": "dr-anna-quartey.jpg"},
        ],
        "Supervisory Committee": [
            {"name": "Dr. Mahmood Oppong Brobbery", "role": "Supervisory Committee Chairperson", "image": "dr-mahmood-brobbey.png"}, 
            {"name": "Dr. Kwasi Yelarge", "role": "Supervisory Committee Secretary", "image": "dr-kwasi-yelarge.jpg"},
            {"name": "Dr. Eleazer Ofei", "role": "Supervisory Committee Member", "image": "dr-eleazer-ofei.jpg"},
        ],
        "Loans Committee": [
            {"name": "Mr. Eric Forson", "role": "Loans Committee Chairperson", "image": "mr-eric-forson.jpg"}, 
            {"name": "Leticia Baah", "role": "Loan Committee Secretary", "image": "leticia-baah.jpeg"},
            {"name": "Dr. Kofi Panyin Boakye", "role": "Loan Committee Member", "image": "dr-kofi-boakye.jpeg"}, 
        ],
        "Management & Staff": [
            {"name": "Benette Anokye", "role": "Accounts Officer", "image": "benette-anokye.jpg"},
            {"name": "Emelia Laar", "role": "Facility Officer", "image": "emelia-laar.jpg"},
            {"name": "Francis Abebio Mensah", "role": "Relationship Officer", "image": "francis-abebio-mensah.jpg"}, 
            {"name": "Hamidatu Abubakar", "role": "Relationship Officer", "image": "hamidatu-abubakar.jpg"},
            {"name": "Ekow Akomeah Sekyi", "role": "Relationship Officer - Takoradi", "image": "ekow-sekyi.jpeg"}, 
            {"name": "Jonathan Wornyo", "role": "Transport Officer", "image": "jonathan-wornyo.png"}, 
        ]
    }
    
    return render(request, 'about.html', {"team_groups": team_data})



def calculator(request): 
    return render(request, 'calculator.html')

def gallery(request):
    albums = GalleryAlbum.objects.filter(is_deleted=False, status='published').prefetch_related('media')
    
    return render(request, "gallery.html", {
        "albums": albums,
    })


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


def article_detail_view(request, public_id):
    article = get_object_or_404(NewsArticle, public_id=public_id)
    
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
