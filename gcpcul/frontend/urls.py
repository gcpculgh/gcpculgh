from django.urls import path

from frontend import views

urlpatterns = [
    path("", views.home, name="home"),
    path('products/', views.products, name="products"),
    path("about-us/", views.about, name="about"),
    path('calculator/', views.calculator, name="calculator"), 
    path('gallery/', views.gallery, name="gallery"),
    path('downloads/', views.downloads, name="downloads"),
    path('news/', views.news, name="news"), 
    path('news/<int:article_id>/', views.article_detail_view, name='article_detail'),
    path('login/', views.login, name="login"),
    path('contact-us/', views.contact, name="contact"),
    path('src/email-image/', views.email_image, name="email-image"),
    path('newsletter/signup/', views.handle_newsletter_signup, name='newsletter_signup'),
    path('waitlist/signup/', views.handle_waitlist_signup, name='waitlist_signup'),
]

