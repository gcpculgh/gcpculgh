from django import forms
from .models import *

class PortalWaitlistForm(forms.ModelForm):
    class Meta:
        model = PortalWaitlist
        fields = ['email']

    def clean_email(self):
        email = self.cleaned_data.get('email').lower().strip()
        if PortalWaitlist.objects.filter(email=email).exists():
            raise forms.ValidationError("You're already on the priority list!")
        return email


class NewsletterForm(forms.ModelForm):
    class Meta:
        model = NewsletterSubscriber
        fields = ['email']

    def clean_email(self):
        email = self.cleaned_data.get('email').lower().strip()
        if NewsletterSubscriber.objects.filter(email=email).exists():
            raise forms.ValidationError("This email is already subscribed to financial updates.")
        return email



class NewsArticleForm(forms.ModelForm):
    class Meta:
        model = NewsArticle
        fields = ["title", "category", "author", "featured_image", "excerpt", "body", "status"]
        widgets = {
            # Populated by JS from the contenteditable body just before submit
            # (see fldBody's sync in admin_news.html) — never shown to the user.
            "body": forms.Textarea(attrs={"id": "fldBodyRaw", "style": "display:none;"}),
            "excerpt": forms.Textarea(attrs={"rows": 2, "maxlength": 160}),
            "status": forms.HiddenInput(),
        }

    def clean_title(self):
        title = self.cleaned_data["title"].strip()
        if not title:
            raise forms.ValidationError("Every article needs a title.")
        return title


class DocumentForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = ["category", "year", "title", "description", "pages", "icon_name"]

    def clean(self):
        cleaned = super().clean()
        category = cleaned.get("category")
        year = cleaned.get("year")
        if category == "agm" and not year:
            self.add_error("year", "AGM documents need a year.")
        return cleaned

class GalleryAlbumForm(forms.ModelForm):
    class Meta:
        model = GalleryAlbum
        fields = ["title", "subtitle", "category"]

    def clean_title(self):
        title = self.cleaned_data["title"].strip()
        if not title:
            raise forms.ValidationError("Every album needs a title.")
        return title