import io
from celery import shared_task
from django.core.files.base import ContentFile

@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def generate_ticket_qr_task(self, ticket_pk):
    import segno
    from .models import Ticket
    try:
        ticket = Ticket.objects.get(pk=ticket_pk)
    except Ticket.DoesNotExist:
        return
    if ticket.qr_code:
        return
    try:
        qr = segno.make(
            f"SPSHK-TICKET:{ticket.pk}:{ticket.stripe_payment_intent_id}", error='h'
        )
        buf = io.BytesIO()
        qr.save(buf, kind='png', scale=10)
        ticket.qr_code.save(f"ticket_{ticket.pk}.png", ContentFile(buf.getvalue()), save=True)
    except Exception as exc:
        raise self.retry(exc=exc)
