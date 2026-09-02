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
    path('login/', views.login, name="login"),
    path('contact-us/', views.contact, name="contact"),
    path('src/email-image/', views.email_image, name="email-image")
]

