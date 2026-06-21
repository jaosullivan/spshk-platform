"""
TDD — Ticket, Event, StripeWebhookLog models
"""
import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(username='buyer@example.com', email='buyer@example.com', password='x')


@pytest.fixture
def unlimited_event(db):
    from tickets.models import Event
    return Event.objects.create(
        title="St Patrick's Day Gala",
        date=timezone.now() + timezone.timedelta(days=30),
        capacity=0,  # 0 = unlimited
        price_hkd_cents=50000,
    )


@pytest.fixture
def limited_event(db):
    from tickets.models import Event
    return Event.objects.create(
        title='Small Gathering',
        date=timezone.now() + timezone.timedelta(days=14),
        capacity=2,
        price_hkd_cents=20000,
    )


# ── Event ──────────────────────────────────────────────────────────────────────

def test_event_str_contains_title(unlimited_event):
    assert "St Patrick" in str(unlimited_event)


def test_event_is_not_sold_out_when_unlimited(unlimited_event):
    assert unlimited_event.is_sold_out is False


def test_event_is_not_sold_out_when_capacity_not_reached(limited_event, user):
    from tickets.models import Ticket
    Ticket.claim(limited_event, user)
    assert limited_event.is_sold_out is False


def test_event_is_sold_out_when_capacity_reached(limited_event, user, db):
    from tickets.models import Ticket
    u2 = User.objects.create_user(username='second@example.com', password='x')
    Ticket.claim(limited_event, user)
    Ticket.claim(limited_event, u2)
    assert limited_event.is_sold_out is True


# ── Ticket.claim() ────────────────────────────────────────────────────────────

def test_claim_creates_ticket(unlimited_event, user):
    from tickets.models import Ticket
    ticket = Ticket.claim(unlimited_event, user)
    assert ticket.pk is not None


def test_claim_links_user_and_event(unlimited_event, user):
    from tickets.models import Ticket
    ticket = Ticket.claim(unlimited_event, user)
    assert ticket.user == user
    assert ticket.event == unlimited_event


def test_claim_raises_sold_out_when_at_capacity(limited_event, user, db):
    from tickets.models import Ticket, SoldOut
    u2 = User.objects.create_user(username='third@example.com', password='x')
    Ticket.claim(limited_event, user)
    Ticket.claim(limited_event, u2)
    u3 = User.objects.create_user(username='fourth@example.com', password='x')
    with pytest.raises(SoldOut):
        Ticket.claim(limited_event, u3)


def test_claim_is_idempotent_for_same_user(unlimited_event, user):
    """Claiming the same event twice should return the existing ticket, not create a duplicate."""
    from tickets.models import Ticket
    t1 = Ticket.claim(unlimited_event, user)
    t2 = Ticket.claim(unlimited_event, user)
    assert t1.pk == t2.pk


def test_claim_does_not_count_same_user_twice_toward_capacity(limited_event, user):
    from tickets.models import Ticket
    Ticket.claim(limited_event, user)
    Ticket.claim(limited_event, user)  # idempotent — should not count twice
    assert limited_event.is_sold_out is False


# ── StripeWebhookLog ──────────────────────────────────────────────────────────

def test_stripe_webhook_log_stripe_event_id_is_unique(db):
    from tickets.models import StripeWebhookLog
    from django.db import IntegrityError
    StripeWebhookLog.objects.create(stripe_event_id='evt_001', event_type='payment_intent.succeeded')
    with pytest.raises(IntegrityError):
        StripeWebhookLog.objects.create(stripe_event_id='evt_001', event_type='payment_intent.succeeded')
