from django.urls import path

from administrator import views

app_name = 'portal'

urlpatterns = [
    path("src/auth/admin-dashboard", views.main_dashboard, name="main_dashboard"),
    path("src/auth/news/", views.portal_news_list, name="portal_newslist"),
]


