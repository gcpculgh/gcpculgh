from django.db import models
from django.core.validators import FileExtensionValidator

class AGMReport(models.Model):
    title = models.CharField(max_length=200, default="AGM Report")
    year = models.IntegerField()
    description = models.TextField(default="Official audited financials and executive committee reports for the fiscal year.", help_text="Summary of the report.")
    icon_name = models.CharField(max_length=50, default="pie_chart", help_text="Use Google Material Symbol names (e.g., 'pie_chart', 'analytics')")
    document = models.FileField(upload_to='agm_reports/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-year']

    def __str__(self):
        return f"{self.year} {self.title}"


class DownloadableForm(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(help_text="Short summary of what this form is used for.")
    icon_name = models.CharField(max_length=50, default="description", help_text="Use Google Material Symbol names (e.g., 'description', 'health_and_safety', 'assignment')")
    document = models.FileField(upload_to='official_forms/', blank=True, null=True)
    pages = models.IntegerField(default=1)
    
    def __str__(self):
        return self.title