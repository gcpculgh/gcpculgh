from django import forms
from .models import PortalWaitlist, NewsletterSubscriber

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