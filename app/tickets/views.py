import stripe
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from .models import Event, Ticket, StripeWebhookLog

stripe.api_key = settings.STRIPE_SECRET_KEY

@login_required
def create_stripe_checkout_session(request, event_id):
    event = get_object_or_404(Event, pk=event_id)
    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[{
            'price_data': {
                'currency': 'hkd',
                'product_data': {'name': event.title},
                'unit_amount': event.price_hkd_cents,
            },
            'quantity': 1,
        }],
        mode='payment',
        success_url=f'https://{settings.SPSHK_DOMAIN}/dashboard/?payment=success',
        cancel_url=f'https://{settings.SPSHK_DOMAIN}/tickets/checkout/{event_id}/',
        metadata={'event_id': event_id, 'user_id': request.user.pk},
    )
    return JsonResponse({'url': session.url})

@csrf_exempt
@require_POST
def stripe_webhook_handler(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE', '')
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except (ValueError, stripe.error.SignatureVerificationError):
        return HttpResponse(status=400)

    if event['type'] == 'checkout.session.completed':
        _handle_checkout_completed(event)

    return HttpResponse(status=200)

def _handle_checkout_completed(stripe_event):
    # Rule B: get_or_create is atomic — concurrent duplicate deliveries are safe
    log, created = StripeWebhookLog.objects.get_or_create(
        stripe_event_id=stripe_event['id'],
        defaults={'event_type': stripe_event['type']},
    )
    if not created:
        return

    session = stripe_event['data']['object']
    payment_intent_id = session.get('payment_intent', '')
    event_id = session['metadata'].get('event_id')
    user_id = session['metadata'].get('user_id')
    if not event_id or not user_id:
        return

    User = get_user_model()
    try:
        user = User.objects.get(pk=user_id)
        ticket, ticket_created = Ticket.claim(event_id, user, payment_intent_id)
    except (Ticket.SoldOut, User.DoesNotExist, Event.DoesNotExist):
        return

    if ticket_created:
        from tickets.tasks import generate_ticket_qr_task
        generate_ticket_qr_task.delay(ticket.pk)
