from django.contrib import admin
from .models import NewsArticle, Document, GalleryAlbum, GalleryMedia, Announcement

@admin.register(NewsArticle)
class NewsArticleAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'author', 'status', 'created_at')
    list_filter = ('category', 'status', 'created_at')
    search_fields = ('title', 'excerpt', 'body')
    prepopulated_fields = {"slug": ("title",)}

@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    pass