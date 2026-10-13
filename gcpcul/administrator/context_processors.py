from .models import Announcement

def global_announcements(request):
    """
    Fetches all active announcements from the database and makes them 
    available as 'global_alerts' in every HTML template automatically.
    """
    try:
        alerts = Announcement.objects.filter(is_active=True)
        return {'global_alerts': alerts}
    except Exception:
        # Failsafe: If the database table isn't created yet, don't crash the site
        return {'global_alerts': []}