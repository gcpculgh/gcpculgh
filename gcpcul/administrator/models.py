
import re

from django.db import models
from django.utils import timezone
from django.utils.text import slugify


class NewsArticle(models.Model):
    CATEGORY_CHOICES = [
        ("dividend", "Dividends"),
        ("guide", "Financial Literacy"),
        ("security", "Security & Portal"),
        ("news", "Union Governance"),
    ]
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("published", "Published"),
    ]

    title = models.CharField(max_length=220)
    slug = models.SlugField(max_length=240, unique=True, blank=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default="news")
    author = models.CharField(max_length=120, help_text="Author or committee name, e.g. 'Finance Committee'")
    featured_image = models.ImageField(upload_to="news/featured/", blank=True, null=True)
    excerpt = models.CharField(max_length=160, blank=True, help_text="Shown in the article grid teaser")
    body = models.TextField(blank=True, help_text="Rich HTML content from the article editor")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="draft")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)[:230] or "article"
            slug_candidate = base_slug
            i = 2
            # Guard against two articles slugifying to the same value.
            while NewsArticle.objects.filter(slug=slug_candidate).exclude(pk=self.pk).exists():
                slug_candidate = f"{base_slug}-{i}"
                i += 1
            self.slug = slug_candidate

        if self.status == "published" and self.published_at is None:
            self.published_at = timezone.now()

        super().save(*args, **kwargs)

    @property
    def read_time_minutes(self):
        """Word-count-derived read time — same '~200 words/min' convention
        the admin editor's live preview already uses client-side."""
        plain_text = re.sub(r"<[^>]+>", " ", self.body or "")
        word_count = len(plain_text.split())
        return max(1, round(word_count / 200))

    @property
    def read_time_display(self):
        return f"{self.read_time_minutes} min read"


class Document(models.Model):
    CATEGORY_CHOICES = [
        ("form", "Application Form"),
        ("report", "Statement & Report"),
        ("agm", "AGM Minutes / Report"),
        ("legal", "Policy & By-Laws"),
    ]
    # Matches exactly the choices offered in the admin icon picker.
    ICON_CHOICES = [
        ("description", "Document"),
        ("person_add", "Person (single applicant)"),
        ("group_add", "Group / Guarantor"),
        ("gavel", "Governance / Legal"),
        ("receipt_long", "Statement / Report"),
        ("health_and_safety", "Health / Insurance"),
        ("badge", "ID / Membership"),
        ("account_balance", "Institutional"),
    ]

    title = models.CharField(max_length=220)
    category = models.CharField(max_length=10, choices=CATEGORY_CHOICES, default="form")
    year = models.PositiveIntegerField(
        blank=True, null=True,
        help_text="Required for AGM documents — drives the auto-generated title in the admin form.",
    )
    description = models.CharField(max_length=300, blank=True)
    pages = models.PositiveIntegerField(blank=True, null=True)
    icon_name = models.CharField(max_length=40, choices=ICON_CHOICES, default="description")
    document = models.FileField(upload_to="documents/%Y/", blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["category", "-year", "title"]

    def __str__(self):
        return self.title

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.category == "agm" and not self.year:
            raise ValidationError({"year": "AGM documents need a year — it drives the title and public sort order."})

    @property
    def is_uploaded(self):
        return bool(self.document)

    @property
    def safe_file_size(self):
        """Never let a missing/moved file crash the public Downloads page —
        matches the defensive property name the live template already calls."""
        if not self.document:
            return 0
        try:
            return self.document.size
        except (FileNotFoundError, ValueError, OSError):
            return 0


class GalleryAlbum(models.Model):
    CATEGORY_CHOICES = [
        ("agm", "AGM Meetings"),
        ("outreach", "Community Outreach"),
        ("hospital", "Hospital Visits"),
    ]

    title = models.CharField(max_length=180)
    subtitle = models.CharField(max_length=280, blank=True)
    category = models.CharField(max_length=10, choices=CATEGORY_CHOICES, default="agm")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    @property
    def cover(self):
        return self.media.filter(is_cover=True).first() or self.media.first()

    @property
    def media_count(self):
        return self.media.count()

    @property
    def uses_placeholder_media(self):
        """Powers the Dashboard's 'Gallery is still stock photography' alert
        and the album grid's 'Stock Photos' tag — true only if every item in
        the album was seeded without a real uploaded file."""
        return self.media.exists() and not self.media.exclude(file="").exists()


class GalleryMedia(models.Model):
    TYPE_CHOICES = [("image", "Photo"), ("video", "Video")]

    album = models.ForeignKey(GalleryAlbum, related_name="media", on_delete=models.CASCADE)
    file = models.FileField(upload_to="gallery/%Y/")
    media_type = models.CharField(max_length=10, choices=TYPE_CHOICES, default="image")
    caption = models.CharField(max_length=280, blank=True)
    is_cover = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"{self.album.title} — item {self.order}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Exactly one cover per album — enforced here so a stray extra
        # `is_cover=True` can never slip in from a bulk edit.
        if self.is_cover:
            GalleryMedia.objects.filter(album=self.album).exclude(pk=self.pk).update(is_cover=False)


class PortalWaitlist(models.Model):
    email = models.EmailField(unique=True)
    joined_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.email

class NewsletterSubscriber(models.Model):
    email = models.EmailField(unique=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.email

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