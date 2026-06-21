from django.conf import settings
from django.db import models, transaction


class SoldOut(Exception):
    pass


class StripeWebhookLog(models.Model):
    """Deduplicate incoming Stripe events by their unique event ID (idempotency)."""
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
    price_hkd_cents = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.title

    @property
    def is_sold_out(self):
        if self.capacity == 0:
            return False
        return self.tickets.count() >= self.capacity


class Ticket(models.Model):
    event = models.ForeignKey(Event, on_delete=models.PROTECT, related_name='tickets')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='tickets')
    stripe_payment_intent_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    purchased_at = models.DateTimeField(auto_now_add=True)
    qr_code = models.ImageField(upload_to='qr_codes/', blank=True)

    class Meta:
        unique_together = [('event', 'user')]

    def __str__(self):
        return f"{self.user} — {self.event}"

    @classmethod
    def claim(cls, event, user):
        """Atomically claim one seat. Raises SoldOut if at capacity."""
        with transaction.atomic():
            locked_event = Event.objects.select_for_update().get(pk=event.pk)
            if locked_event.capacity > 0 and locked_event.tickets.count() >= locked_event.capacity:
                raise SoldOut(f"{locked_event.title} is sold out")
            ticket, _ = cls.objects.get_or_create(event=locked_event, user=user)
            return ticket
