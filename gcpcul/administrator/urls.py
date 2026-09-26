
from django.urls import path
from django.contrib.auth import views as auth_views

from . import views

app_name = "cms"
URL_PREFIX = "src/auth/admin"

urlpatterns = [
    path(f"{URL_PREFIX}/", views.dashboard, name="dashboard"),
    path(f"{URL_PREFIX}/news/", views.news_list, name="news_list"),
    path(f"{URL_PREFIX}/news/new/", views.news_create, name="news_create"),
    path(f"{URL_PREFIX}/news/<int:pk>/edit/", views.news_update, name="news_update"),
    path(f"{URL_PREFIX}/news/<int:pk>/delete/", views.news_delete, name="news_delete"),

    path(f"{URL_PREFIX}/documents/", views.document_list, name="document_list"),
    path(f"{URL_PREFIX}/documents/new/", views.document_create, name="document_create"),
    path(f"{URL_PREFIX}/documents/<int:pk>/edit/", views.document_update, name="document_update"),
    path(f"{URL_PREFIX}/documents/<int:pk>/delete/", views.document_delete, name="document_delete"),
    path(f"{URL_PREFIX}/documents/<int:doc_id>/download/", views.secure_document_download, name="secure_document_download"),

    path(f"{URL_PREFIX}/gallery/", views.gallery_list, name="gallery_list"),
    path(f"{URL_PREFIX}/gallery/new/", views.gallery_create, name="gallery_create"),
    path(f"{URL_PREFIX}/gallery/<int:pk>/edit/", views.gallery_update, name="gallery_update"),
    path(f"{URL_PREFIX}/gallery/<int:pk>/delete/", views.gallery_delete, name="gallery_delete"),
    path(f"{URL_PREFIX}/gallery/media/<int:pk>/delete/", views.gallery_media_delete, name="gallery_media_delete"),
    path(f"{URL_PREFIX}/login/", auth_views.LoginView.as_view(template_name="cms/admin_login.html", redirect_authenticated_user=True), name="admin_login"),
    path(f"{URL_PREFIX}/logout/", auth_views.LogoutView.as_view(next_page="home"), name="logout"),

    path(f'{URL_PREFIX}/api/generate-upload-url/', views.generate_upload_url, name='generate_upload_url'),
]