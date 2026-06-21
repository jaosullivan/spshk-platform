from django.conf import settings
from django.db import models, transaction

class StripeWebhookLog(models.Model):
    """Rule B: deduplicate incoming Stripe events by their unique event ID."""
    stripe_event_id = models.CharField(max_length=255, unique=True)
    event_type = models.CharField(max_length=255)
    received_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=['stripe_event_id'])]

class Event(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    date = models.DateTimeField()
    venue = models.CharField(max_length=255, blank=True)
    capacity = models.PositiveIntegerField(default=0)
    # HKD stored as integer cents: HK$888 → 88800
    price_hkd_cents = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.title

class Ticket(models.Model):
    event = models.ForeignKey(Event, on_delete=models.PROTECT, related_name='tickets')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='tickets')
    stripe_payment_intent_id = models.CharField(max_length=255, unique=True)
    purchased_at = models.DateTimeField(auto_now_add=True)
    qr_code = models.ImageField(upload_to='qr_codes/', blank=True)

    class Meta:
        unique_together = [('event', 'user')]

    def __str__(self):
        return f"{self.user} — {self.event}"

    class SoldOut(Exception):
        pass

    @classmethod
    def claim(cls, event_id, user, payment_intent_id):
        """Atomically claim one seat. Raises SoldOut if at capacity."""
        with transaction.atomic():
            event = Event.objects.select_for_update().get(pk=event_id)
            if event.capacity > 0 and event.tickets.count() >= event.capacity:
                raise cls.SoldOut(f"{event.title} is sold out")
            return cls.objects.get_or_create(
                event=event,
                user=user,
                defaults={'stripe_payment_intent_id': payment_intent_id},
            )
