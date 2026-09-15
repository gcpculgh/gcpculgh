from .models import Announcement

def global_announcements(request):
    # Grabs all active announcements to display globally
    alerts = Announcement.objects.filter(is_active=True)
    return {'global_alerts': alerts}
