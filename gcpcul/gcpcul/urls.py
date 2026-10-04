from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from django.contrib.auth import views as auth_views  

from frontend import urls as frontend_urls
from users import urls as users_urls
from administrator import urls as admin_urls
from django.views.generic import TemplateView
from .sitemaps import StaticViewSitemap
from django.contrib.sitemaps.views import sitemap

sitemaps = {
    'static': StaticViewSitemap,
}

urlpatterns = [
    path('src/auth/sec/admin/', admin.site.urls),
    path('src/auth/admin/admin-access/', auth_views.LoginView.as_view(
        template_name='admin_login.html', 
        redirect_authenticated_user=True
    ), name='admin_login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='home'), name='logout'),

    path('', include(frontend_urls)),
    path('', include(users_urls)),
    path("", include(admin_urls)),
    path('summernote/', include('django_summernote.urls')),
    path('robots.txt', TemplateView.as_view(template_name="robots.txt", content_type="text/plain")),
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
]