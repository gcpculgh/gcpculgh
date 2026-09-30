from django.shortcuts import render, get_object_or_404, redirect
from administrator.models import *
from django.contrib import messages
from administrator.forms import * 
from administrator.models import Document 

from django.http import Http404

# GLOBAL STATIC DATA HYDRATION
TEAM_DATA = {
    "Operational Leadership": [
        {
            "slug": "eric-adjei-yeboah", 
            "name": "Eric Adjei-Yeboah", 
            "role": "Chief Executive Officer", 
            "image": "eric-adjei-yeboah.jpeg",
            "email": "eric.adjei-yeboah@gcpcul.com",  
            "linkedin": "https://linkedin.com/in/eric-adjei",
            "bio": """Eric Adjei – Yeboah, is a professional Finance and Investment Banker with over twenty (21) years of experience. Eric is results-driven Financial Service Professional, Investment Banker and a Legal Student. Currently working with Ghana Co-operative Pharmacists Credit Union Limited as the Chief Executive Officer.

Prior to this position, Eric was the Head of Wealth Management Department at UMB Investment Holdings Limited now Merban Capital Ltd. Eric was in charge of Collective Investment Schemes, Trustee Business, High Net Worth Portfolio Management and a Legal Deponent for the company.

Eric began his investment banking career with Merchant Bank’s Ghana Limited now Universal Merchant Bank (UMB) in the year 2004 and was elevated through the ranks of the bank over the years. Eric has a good knowledge in Banking, Finance and Investment, Marketing and Products Developments. He also worked with Cocoa Processing Company as an account trainee at the Finished Products Stores at Tema Industrial Area.

Eric was formerly the Chief Executive Officer for ASN Investment Holdings Limited as of late 2015 till early 2017.

Eric holds Bachelor of Laws (LLB), Professional Executive Master in Alternative Dispute Resolution (ADR) and a Certified Member of Ghana National Association of ADR Practitioners (GNAAP), MSc. (Finance Option) from the Ghana Institute of Management and Public Administration (GIMPA), Master of Art in Ministry (MAM), Trinity Theological Seminary- Legon), Bachelor of Business Administration (BBA) from Methodist University College, Ghana Stock Exchange Course and as a licensed Fund Manager Representative, Level Three (3) at Chartered Institute of Bankers. Certificates in Money Market and Practices, Capital Market and Securities Analysis and Portfolio Structuring."""
        },
        {
            "slug": "yompab-joseph-baaman", 
            "name": "Yompab Joseph Nanoni Baaman", 
            "role": "Senior Accountant", 
            "image": "yompab-joseph.jpeg",
            "email": "yompab-joseph@gcpcul.com",  
            "linkedin": "https://linkedin.com/in/yompab-joseph-baaman",
            "bio": """Yompab Joseph Nanoni Baaman-C. A possesses an extensive 18-year career in Accounting and Finance, including 6 years of experience as a Chartered Accountant. He is a qualified Chartered Accountant and a member of The Institute of Chartered Accountants, Ghana (ICAG).

He holds a Master of Science in Accounting and Finance and a Bachelor of Science in Business Administration with a concentration in Accounting, both from the Kwame Nkrumah University of Science and Technology (KNUST) Business School. Currently, he is pursuing final-level professional courses with the Chartered Institute of Bankers Ghana and the Chartered Institute of Taxation Ghana.

His professional experience includes significant roles within the Rural and Community Banking and Financial Services sectors. He is currently serving as the Senior Accountant at the Ghana Cooperative Pharmacists’ Credit Union."""
        },
        {
            "slug": "okyere-michael-owusu", "name": "Okyere Michael Owusu", "role": "Business Dev. Executive", "image": "okyere-michael.jpeg",
            "bio": """Okyere Michael Owusu is a Business Development and Account Management professional with over 15 years of experience in sales, business development, client relationship management and revenue growth across the financial, services and development sectors.

At Ghana Co-operative Pharmacists’ Credit Union Limited (GCPCUL), he is responsible for driving business development initiatives, managing member relationships across all branches, spearheading deposits and loan portfolio growth, and identifying opportunities for membership and business expansion. He also coordinates sales activities, relationship management and market engagement through various channels.

His professional experience also includes regional sales leadership, client engagement, account and operations support, market research and business development. He has managed extensive client engagements, including outbound engagement with over 5,000 clients across five regions.

Okyere holds a Bachelor of Business Administration (BBA) from the University of Professional Studies, Accra, a Certificate in Entrepreneurship and Small Business Management from GIMPA, and a Diploma in Business Studies (Accounting) from Koforidua Polytechnic.

His professional strength lies in combining account management, business development, sales strategy and relationship management to drive sustainable business growth and deliver value to members and stakeholders."""
        },
    ],
    "Board of Directors": [
        {"slug": "dr-paul-owusu-donkor", "name": "Dr. Paul Owusu Donkor", "role": "BOD Chairman", "image": "dr-paul-donkor.jpg", "bio": "Detailed biography coming soon."},
        {"slug": "dr-brenda-yayra-opong", "name": "Dr. Brenda Yayra Opong", "role": "BOD Vice Chairperson", "image": "dr-brenda-opong.jpg", "bio": "Detailed biography coming soon."},
        {"slug": "dr-anna-kwarley-quartey", "name": "Dr. Anna Kwarley Quartey", "role": "BOD Member", "image": "dr-anna-quartey.jpg", "bio": "Detailed biography coming soon."},
    ],
    "Supervisory Committee": [
        {"slug": "dr-mahmood-oppong-brobbey", "name": "Dr. Mahmood Oppong Brobbery", "role": "Supervisory Committee Chairperson", "image": "dr-mahmood-brobbey.png", "bio": "Detailed biography coming soon."},
        {"slug": "dr-kwasi-yelarge", "name": "Dr. Kwasi Yelarge", "role": "Supervisory Committee Secretary", "image": "dr-kwasi-yelarge.jpg", "bio": "Detailed biography coming soon."},
        {"slug": "dr-eleazer-ofei", "name": "Dr. Eleazer Ofei", "role": "Supervisory Committee Member", "image": "dr-eleazer-ofei.jpg", "bio": "Detailed biography coming soon."},
    ],
    "Loans Committee": [
        {"slug": "mr-eric-forson", "name": "Mr. Eric Forson", "role": "Loans Committee Chairperson", "image": "mr-eric-forson.jpg", "bio": "Detailed biography coming soon."},
        {"slug": "leticia-baah", "name": "Leticia Baah", "role": "Loan Committee Secretary", "image": "leticia-baah.jpeg", "bio": "Detailed biography coming soon."},
        {"slug": "dr-kofi-panyin-boakye", "name": "Dr. Kofi Panyin Boakye", "role": "Loan Committee Member", "image": "dr-kofi-boakye.jpeg", "bio": "Detailed biography coming soon."},
    ],
    "Management & Staff": [
        {"slug": "benette-anokye", "name": "Benette Anokye", "role": "Accounts Officer", "image": "benette-anokye.jpg", "bio": "Detailed biography coming soon."},
        {"slug": "emelia-laar", "name": "Emelia Laar", "role": "Facility Officer", "image": "emelia-laar.jpg", "bio": "Detailed biography coming soon."},
        {"slug": "francis-abebio-mensah", "name": "Francis Abebio Mensah", "role": "Relationship Officer", "image": "francis-abebio-mensah.jpg", "bio": "Detailed biography coming soon."},
        {"slug": "hamidatu-abubakar", "name": "Hamidatu Abubakar", "role": "Relationship Officer", "image": "hamidatu-abubakar.jpg", "bio": "Detailed biography coming soon."},
        {"slug": "ekow-akomeah-sekyi", "name": "Ekow Akomeah Sekyi", "role": "Relationship Officer - Takoradi", "image": "ekow-sekyi.jpeg", "bio": "Detailed biography coming soon."},
        {"slug": "jonathan-wornyo", "name": "Jonathan Wornyo", "role": "Transport Officer", "image": "jonathan-wornyo.png", "bio": "Detailed biography coming soon."},
    ]
}

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
    return render(request, 'about.html', {
        "team_groups": TEAM_DATA,
        "leadership": TEAM_DATA["Operational Leadership"]
    })

def team_bio_view(request, slug):
    target_member = None
    target_category = None
    related_members = []
    
    for category_name, members in TEAM_DATA.items():
        for member in members:
            if member['slug'] == slug:
                target_member = member
                target_category = category_name
                break
        if target_member:
            break
            
    if not target_member:
        raise Http404("Team member not found.")
        
    related_members = [m for m in TEAM_DATA[target_category] if m['slug'] != slug][:3]
    
    context = {
        'member': target_member,
        'category': target_category,
        'related': related_members,
    }
    return render(request, 'team_bio.html', context)

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
