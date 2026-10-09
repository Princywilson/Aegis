from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from accountability.models import AuthenticationRateLimitCounter


class Command(BaseCommand):
    help = "Delete expired authentication rate-limit counters."

    def handle(self, *args, **options):
        now = timezone.now()
        cutoff = now - timedelta(minutes=15)
        expired = Q(updated_at__lt=cutoff) & (
            Q(blocked_until__isnull=True) | Q(blocked_until__lte=now)
        )
        deleted, _ = AuthenticationRateLimitCounter.objects.filter(expired).delete()
        self.stdout.write(f"Deleted {deleted} expired authentication rate-limit counter(s).")
