from django.db import models

class NewsArticle(models.Model):
    TOPIC_CHOICES = [
        ('dividends', 'Dividends & Shares'),
        ('loans', 'Loans & Credit'),
        ('security', 'Digital Safety & Security'),
        ('governance', 'Governance & Leadership'),
        ('health', 'Healthcare & Practice'),
    ]

    title = models.CharField(max_length=255)
    topic = models.CharField(max_length=50, choices=TOPIC_CHOICES, default='dividends')
    
    is_featured = models.BooleanField(
        default=False,
        help_text="Pin to the giant top Hero section. (Checking this automatically unpins the previous one)."
    )

    is_recent_happening = models.BooleanField(
        default=False, 
        help_text="Check this to feature in the top 3 'Recent Happenings' grid on the home page."
    )

    is_blog_post = models.BooleanField(
        default=True, 
        help_text="Check this to display in the bottom 'Cooperative Insights' blog grid."
    )

    summary = models.TextField(help_text="Short excerpt for homepage preview cards.")
    content = models.TextField(help_text="Full article body (uses Summernote editor).")
    
    cover_image = models.ImageField(upload_to='news_images/')
    author = models.CharField(max_length=100, default="Finance Committee")
    published_date = models.DateField()

    STATUS_CHOICES = (
            ('draft', 'Draft'),
            ('published', 'Published'),
        )
    
    status = models.CharField(
        max_length=10, 
        choices=STATUS_CHOICES, 
        default='draft',
        help_text="Drafts are hidden from the public site."
    )
    
    def save(self, *args, **kwargs):
        if self.is_featured:
            # ...find any other article that is currently featured and uncheck it.
            NewsArticle.objects.filter(is_featured=True).update(is_featured=False)
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['-published_date']

    def __str__(self):
        return f"[{self.get_topic_display()}] {self.title}"


class Announcement(models.Model):
    ALERT_TYPES = (
        ('info', 'Information (Blue)'),
        ('warning', 'Warning/Reminder (Yellow)'),
        ('urgent', 'Urgent/Critical (Red)'),
    )
    
    # Upgraded to TextField and updated help_text to guide the admin
    message = models.TextField(
        help_text='Use HTML for inline links. Example: Join tomorrow\'s AGM <a href="https://zoom.us/...">via this link</a>.'
    )
    alert_type = models.CharField(max_length=10, choices=ALERT_TYPES, default='warning')
    is_active = models.BooleanField(default=True, help_text="Uncheck to hide this announcement globally.")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.message[:50]


class PortalWaitlist(models.Model):
    email = models.EmailField(unique=True, db_index=True)
    joined_at = models.DateTimeField(auto_now_add=True)
    is_notified = models.BooleanField(default=False)

    def __str__(self):
        return self.email


class NewsletterSubscriber(models.Model):
    email = models.EmailField(unique=True, db_index=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.email