import json
import logging

import stripe
from django.conf import settings
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from tickets.models import Event

logger = logging.getLogger(__name__)

@login_required
def member_dashboard_view(request):
    tickets = request.user.tickets.select_related('event').order_by('-purchased_at')
    return render(request, 'members/dashboard.html', {'tickets': tickets})

@login_required
def calendar_view(request):
    return render(request, 'members/calendar.html')

@login_required
def profile_view(request):
    return render(request, 'members/dashboard.html', {})

def register_view(request):
    if request.user.is_authenticated:
        return render(request, 'members/register.html', {
            'already_signed_in': True,
            'signed_in_name': request.user.first_name or request.user.username,
        })

    if request.method == 'POST':
        first_name       = request.POST.get('first_name', '').strip()
        last_name        = request.POST.get('last_name', '').strip()
        email            = request.POST.get('email', '').strip().lower()
        password         = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')

        errors = []
        if not (first_name and last_name and email and password):
            errors.append('Please fill in all fields.')
        if password and len(password) < 8:
            errors.append('Password must be at least 8 characters.')
        if password and password != confirm_password:
            errors.append('Passwords do not match.')

        if errors:
            for error in errors:
                messages.error(request, error)
            return render(request, 'members/register.html', {'post': request.POST})

        from django.contrib.auth import get_user_model
        User = get_user_model()

        if User.objects.filter(email=email).exists():
            messages.error(request, 'An account with that email already exists. Please sign in.')
            return render(request, 'members/register.html', {'post': request.POST})

        user = User.objects.create_user(
            username=email,
            email=email,
            first_name=first_name,
            last_name=last_name,
            password=password,
            is_green_card_holder=False,  # activated by Stripe webhook after payment
            consent_given_at=timezone.now(),
        )
        login(request, user)
        return redirect('members:checkout')

    return render(request, 'members/register.html', {})


def register_success_view(request):
    return render(request, 'members/register_success.html', {})


@login_required
def checkout_view(request):
    stripe.api_key = settings.STRIPE_SECRET_KEY
    user = request.user
    domain = request.build_absolute_uri('/').rstrip('/')

    # Create or reuse a Stripe Customer so receipts carry the member's name
    if not user.stripe_customer_id:
        customer = stripe.Customer.create(
            email=user.email,
            name=f"{user.first_name} {user.last_name}".strip(),
            metadata={'membership_uuid': str(user.membership_uuid)},
        )
        user.stripe_customer_id = customer.id
        user.save(update_fields=['stripe_customer_id'])
    else:
        customer = stripe.Customer.retrieve(user.stripe_customer_id)

    session = stripe.checkout.Session.create(
        customer=customer.id,
        payment_method_types=['card'],
        line_items=[{
            'price_data': {
                'currency': 'hkd',
                'unit_amount': 88800,  # HKD $888 in cents
                'product_data': {
                    'name': 'SPSHK Green Card — Lifetime Membership',
                    'description': 'Event invitations, monthly newsletter, and local discounts.',
                },
            },
            'quantity': 1,
        }],
        mode='payment',
        success_url=f"{domain}/members/payment/success/?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{domain}/members/payment/cancel/",
        metadata={'user_pk': user.pk},
    )
    return redirect(session.url, permanent=False)


@login_required
def payment_success_view(request):
    return render(request, 'members/payment_success.html', {
        'membership_uuid': request.user.membership_uuid,
        'is_active': request.user.is_green_card_holder,
    })


@login_required
def payment_cancel_view(request):
    messages.warning(request, 'Payment was cancelled. Complete payment to activate your Green Card.')
    return redirect('members:checkout')


@csrf_exempt
@require_POST
def stripe_webhook_view(request):
    stripe.api_key = settings.STRIPE_SECRET_KEY
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE', '')

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except (ValueError, stripe.error.SignatureVerificationError) as exc:
        logger.warning("Stripe webhook rejected: %s", exc)
        return HttpResponse(status=400)

    from tickets.models import StripeWebhookLog
    from django.db import IntegrityError
    try:
        StripeWebhookLog.objects.create(
            stripe_event_id=event['id'],
            event_type=event['type'],
        )
    except IntegrityError:
        return HttpResponse(status=200)  # already processed

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        user_pk = session.get('metadata', {}).get('user_pk')
        if user_pk:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            User.objects.filter(pk=user_pk, is_green_card_holder=False).update(
                is_green_card_holder=True,
                membership_activated_at=timezone.now(),
            )
            from members.tasks import send_welcome_email_task
            send_welcome_email_task.delay(int(user_pk))

    return HttpResponse(status=200)


def api_event_feed(request):
    events = list(
        Event.objects.order_by('date').values(
            'id', 'title', 'description', 'date', 'venue', 'capacity', 'price_hkd_cents'
        )
    )
    return JsonResponse({'events': events})

def calendar_event_feed(request):
    data = [
        {
            'id': e.pk,
            'title': e.title,
            'start': e.date.isoformat(),
            'extendedProps': {
                'venue': e.venue,
                'price_hkd_cents': e.price_hkd_cents,
            },
        }
        for e in Event.objects.order_by('date')
    ]
    return JsonResponse(data, safe=False)
