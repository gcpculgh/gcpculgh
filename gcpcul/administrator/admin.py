from django.contrib import admin
from django_summernote.admin import SummernoteModelAdmin
from .models import *

@admin.register(NewsArticle)
class NewsArticleAdmin(SummernoteModelAdmin):
    summernote_fields = ('content',) 
    
    # Add 'is_featured' to the display
    list_display = ('title', 'topic', 'is_featured', 'is_recent_happening', 'is_blog_post', 'published_date')
    
    # This magic line lets the admin check/uncheck the box directly from the list page!
    list_editable = ('is_featured', 'is_recent_happening', 'is_blog_post') 
    
    list_filter = ('topic', 'is_featured', 'published_date')
    search_fields = ('title', 'summary', 'content')

@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ('message', 'alert_type', 'is_active', 'created_at')
    list_filter = ('alert_type', 'is_active')
    search_fields = ('message',)