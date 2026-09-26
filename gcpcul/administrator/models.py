import re

from django.db import models
from django.utils import timezone
from django.utils.text import slugify
from .utils import optimize_and_convert_to_webp
from django.core.validators import FileExtensionValidator
import os
from django.core.exceptions import ValidationError

import bleach
from bleach.linkifier import Linker
import markdown


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
        # Automatically compress & convert featured image to WebP if newly uploaded
        if self.featured_image and not self.featured_image.name.endswith('.webp'):
            self.featured_image = optimize_and_convert_to_webp(self.featured_image)

        if not self.slug:
            base_slug = slugify(self.title)[:230] or "article"
            slug_candidate = base_slug
            i = 2
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

def validate_secure_document(file):
    valid_extensions = ['.pdf', '.doc', '.docx']
    ext = os.path.splitext(file.name)[1].lower()
    
    if ext not in valid_extensions:
        raise ValidationError(f"Unsupported file extension: {ext}. Allowed types: PDF, DOC, DOCX.")
    
    # ZERO-TRUST: Read the first 8 bytes (Magic Bytes) to prove the file isn't spoofed
    file.seek(0)
    header = file.read(8)
    file.seek(0) # Reset pointer so Django can save it properly later
    
    is_pdf = header.startswith(b'%PDF')
    is_docx = header.startswith(b'PK\x03\x04') # Standard ZIP/XML header for modern Word docs
    is_doc = header.startswith(b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1') # OLE header for legacy Word docs
    
    if ext == '.pdf' and not is_pdf:
        raise ValidationError("Spoofed file detected: Extension is PDF, but content is malicious/invalid.")
    if ext == '.docx' and not is_docx:
        raise ValidationError("Spoofed file detected: Extension is DOCX, but content is malicious/invalid.")
    if ext == '.doc' and not is_doc:
        raise ValidationError("Spoofed file detected: Extension is DOC, but content is malicious/invalid.")


class Document(models.Model):
    CATEGORY_CHOICES = [
        ("form", "Application Form"),
        ("report", "Statement & Report"),
        ("agm", "AGM Minutes / Report"),
        ("legal", "Policy & By-Laws"),
    ]
   

    title = models.CharField(max_length=220)
    category = models.CharField(max_length=10, choices=CATEGORY_CHOICES, default="form")
    year = models.PositiveIntegerField(
        blank=True, null=True,
        help_text="Required for AGM documents — drives the auto-generated title in the admin form.",
    )
    description = models.CharField(max_length=300, blank=True)
    pages = models.PositiveIntegerField(blank=True, null=True)
    icon_name = models.CharField(max_length=40, default="description")
    document = models.FileField(
        upload_to="documents/%Y/", 
        blank=True, 
        null=True,
        validators=[validate_secure_document]
    )

    file_hash = models.CharField(max_length=64, blank=True, null=True, help_text="SHA-256 cryptographic checksum")
    page_count = models.PositiveIntegerField(blank=True, null=True)
    thumbnail = models.ImageField(upload_to='document_thumbs/', blank=True, null=True)

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
    message = models.TextField(
        help_text="Keep it brief. Paste URLs normally (defaults to 'View Link'), or use Markdown for custom text: [Click Here](https://example.com)"
    )
    is_active = models.BooleanField(
        default=False,
        help_text="Check this to display the announcement site-wide. Uncheck to hide it."
    )

    def save(self, *args, **kwargs):
        if self.message:
            # 1. Parse custom Markdown tags first
            html_content = markdown.markdown(self.message)

            # 2. Sanitize and destroy any raw malicious HTML
            clean_html = bleach.clean(
                html_content,
                tags=['a', 'p', 'strong', 'em', 'br'],
                attributes={'a': ['href']},
                protocols=['http', 'https', 'mailto'],
                strip=True
            )

            # 3. Intercept all links to enforce security and UX standards
            def secure_link_attributes(attrs, new=False):
                href = attrs.get((None, 'href'), '')
                if not href.startswith(('http:', 'https:', 'mailto:')):
                    return None

                # Enforce anti-tabnabbing
                attrs[(None, 'target')] = '_blank'
                attrs[(None, 'rel')] = 'noopener noreferrer'

                # THE UX FIX: If this is a raw URL (new=True), replace the long text with a clean default
                if new:
                    attrs['_text'] = 'View Link'

                return attrs

            linker = Linker(callbacks=[secure_link_attributes])
            self.message = linker.linkify(clean_html)

        super().save(*args, **kwargs)