from django.urls import path

from frontend import views

urlpatterns = [
    path("", views.home, name="home"),
    path('products/', views.products, name="products"),
    path("about-us/", views.about, name="about"),
    path('team/<slug:slug>/', views.team_bio_view, name='team_bio'),
    path('calculator/', views.calculator, name="calculator"), 
    path('gallery/', views.gallery, name="gallery"),
    path('downloads/', views.downloads, name="downloads"),
    path('news/', views.news, name="news"), 
    path('news/<uuid:public_id>/', views.article_detail_view, name='article_detail'),
    path('portal/', views.member_portal, name="member_portal"),
    path('contact-us/', views.contact, name="contact"),
    path('src/email-image/', views.email_image, name="email-image"),
    path('newsletter/signup/', views.handle_newsletter_signup, name='newsletter_signup'),
    path('waitlist/signup/', views.handle_waitlist_signup, name='waitlist_signup'),
]

