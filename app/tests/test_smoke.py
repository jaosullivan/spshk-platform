"""
Smoke tests — high-level sanity checks for SPSHK critical paths.
Run in isolation: pytest -m smoke
Skip in fast TDD loop: pytest -m "not smoke"
"""
import pytest
from django.urls import reverse


@pytest.mark.smoke
def test_health_endpoint_returns_ok(client):
    """Deployment gate: /healthz/ must respond 200 with status:ok."""
    response = client.get('/healthz/')
    assert response.status_code == 200
    assert response.json() == {'status': 'ok'}


@pytest.mark.smoke
def test_register_page_loads(client):
    """Critical path: public registration form must render without error."""
    response = client.get(reverse('members:register'))
    assert response.status_code == 200


@pytest.mark.smoke
def test_register_success_page_loads(client):
    """Critical path: post-registration confirmation page must render."""
    response = client.get(reverse('members:register_success'))
    assert response.status_code == 200


@pytest.mark.smoke
def test_database_is_reachable(db):
    """Deployment gate: ORM can query the user table without error."""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    count = User.objects.count()
    assert isinstance(count, int)


@pytest.mark.smoke
def test_custom_user_model_fields_exist(db):
    """Sanity: CustomUser has the SPSHK-specific fields expected by the platform."""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    required_fields = {'membership_uuid', 'is_green_card_holder', 'loyalty_points',
                       'consent_given_at', 'data_retention_until'}
    model_fields = {f.name for f in User._meta.get_fields()}
    assert required_fields.issubset(model_fields)


@pytest.mark.smoke
def test_tickets_app_models_are_importable():
    """Sanity: tickets models load without import errors."""
    from tickets.models import Event, Ticket, StripeWebhookLog, SoldOut  # noqa: F401
