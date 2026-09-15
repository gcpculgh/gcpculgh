from django.contrib import admin
from .models import *

# Register your models here.
@admin.register(AGMReport)
class AGMReportAdmin(admin.ModelAdmin):
    list_display = ("title", "year", "uploaded_at")
    search_fields = ("title", "year")

@admin.register(DownloadableForm)
class DownloadableFormAdmin(admin.ModelAdmin):
    list_display = ('title', 'icon_name', 'pages', 'has_document')
    
    def has_document(self, obj):
        return bool(obj.document)
    has_document.boolean = True