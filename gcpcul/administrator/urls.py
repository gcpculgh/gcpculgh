from django.urls import path

from administrator import views

app_name = 'portal'

urlpatterns = [
    path("src/auth/admin-dashboard", views.main_dashboard, name="main_dashboard"),
    path("src/auth/news/", views.portal_news_list, name="portal_newslist"),
    path('newsletter/signup/', views.handle_newsletter_signup, name='newsletter_signup'),
    path('waitlist/signup/', views.handle_waitlist_signup, name='waitlist_signup'),
]


