"""
TDD — members registration views
"""
import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

User = get_user_model()


# ── GET /members/register/ ────────────────────────────────────────────────────

def test_register_get_returns_200(client):
    url = reverse('members:register')
    response = client.get(url)
    assert response.status_code == 200


def test_register_get_renders_register_template(client):
    url = reverse('members:register')
    response = client.get(url)
    assert 'members/register.html' in [t.name for t in response.templates]


# ── POST /members/register/ — success ─────────────────────────────────────────

def test_register_post_valid_creates_user(client, db):
    url = reverse('members:register')
    client.post(url, {'first_name': 'Seán', 'last_name': 'Murphy', 'email': 'sean@example.com', 'password': 'Secure123!', 'confirm_password': 'Secure123!'})
    assert User.objects.filter(email='sean@example.com').exists()


def test_register_post_valid_redirects_to_checkout(client, db):
    url = reverse('members:register')
    response = client.post(url, {'first_name': 'Seán', 'last_name': 'Murphy', 'email': 'sean@example.com', 'password': 'Secure123!', 'confirm_password': 'Secure123!'})
    assert response.status_code == 302
    assert response['Location'] == reverse('members:checkout')


def test_register_post_creates_pending_account(client, db):
    url = reverse('members:register')
    client.post(url, {'first_name': 'Áine', 'last_name': "O'Brien", 'email': 'aine@example.com', 'password': 'Secure123!', 'confirm_password': 'Secure123!'})
    user = User.objects.get(email='aine@example.com')
    assert user.is_green_card_holder is False  # activated by Stripe webhook after payment


def test_register_post_sets_consent_given_at(client, db):
    url = reverse('members:register')
    client.post(url, {'first_name': 'Áine', 'last_name': "O'Brien", 'email': 'aine@example.com', 'password': 'Secure123!', 'confirm_password': 'Secure123!'})
    user = User.objects.get(email='aine@example.com')
    assert user.consent_given_at is not None


def test_register_post_stores_name_correctly(client, db):
    url = reverse('members:register')
    client.post(url, {'first_name': 'Ciarán', 'last_name': 'Ó Murchú', 'email': 'ciaran@example.com', 'password': 'Secure123!', 'confirm_password': 'Secure123!'})
    user = User.objects.get(email='ciaran@example.com')
    assert user.first_name == 'Ciarán'
    assert user.last_name == 'Ó Murchú'


# ── POST /members/register/ — duplicate email ─────────────────────────────────

def test_register_post_duplicate_email_returns_200(client, db):
    User.objects.create_user(username='existing@example.com', email='existing@example.com', password='x')
    url = reverse('members:register')
    response = client.post(url, {'first_name': 'Pat', 'last_name': 'Kelly', 'email': 'existing@example.com', 'password': 'Secure123!', 'confirm_password': 'Secure123!'})
    assert response.status_code == 200


def test_register_post_duplicate_email_does_not_create_second_user(client, db):
    User.objects.create_user(username='existing@example.com', email='existing@example.com', password='x')
    url = reverse('members:register')
    client.post(url, {'first_name': 'Pat', 'last_name': 'Kelly', 'email': 'existing@example.com', 'password': 'Secure123!', 'confirm_password': 'Secure123!'})
    assert User.objects.filter(email='existing@example.com').count() == 1


def test_register_post_duplicate_email_shows_error_message(client, db):
    User.objects.create_user(username='existing@example.com', email='existing@example.com', password='x')
    url = reverse('members:register')
    response = client.post(url, {'first_name': 'Pat', 'last_name': 'Kelly', 'email': 'existing@example.com', 'password': 'Secure123!', 'confirm_password': 'Secure123!'})
    messages = list(response.context['messages'])
    assert any('already exists' in str(m) for m in messages)


# ── POST /members/register/ — missing fields ──────────────────────────────────

@pytest.mark.parametrize('payload', [
    {'first_name': '', 'last_name': 'Murphy', 'email': 'x@x.com', 'password': 'Secure123!', 'confirm_password': 'Secure123!'},
    {'first_name': 'Seán', 'last_name': '', 'email': 'x@x.com', 'password': 'Secure123!', 'confirm_password': 'Secure123!'},
    {'first_name': 'Seán', 'last_name': 'Murphy', 'email': '', 'password': 'Secure123!', 'confirm_password': 'Secure123!'},
    {'first_name': 'Seán', 'last_name': 'Murphy', 'email': 'x@x.com', 'password': '', 'confirm_password': ''},
])
def test_register_post_missing_field_returns_200(client, db, payload):
    url = reverse('members:register')
    response = client.post(url, payload)
    assert response.status_code == 200


@pytest.mark.parametrize('payload', [
    {'first_name': '', 'last_name': 'Murphy', 'email': 'x@x.com', 'password': 'Secure123!', 'confirm_password': 'Secure123!'},
    {'first_name': 'Seán', 'last_name': '', 'email': 'x@x.com', 'password': 'Secure123!', 'confirm_password': 'Secure123!'},
    {'first_name': 'Seán', 'last_name': 'Murphy', 'email': '', 'password': 'Secure123!', 'confirm_password': 'Secure123!'},
    {'first_name': 'Seán', 'last_name': 'Murphy', 'email': 'x@x.com', 'password': '', 'confirm_password': ''},
])
def test_register_post_missing_field_does_not_create_user(client, db, payload):
    url = reverse('members:register')
    client.post(url, payload)
    assert User.objects.count() == 0


# ── GET /members/register/success/ ────────────────────────────────────────────

def test_register_post_logs_user_in(client, db):
    url = reverse('members:register')
    client.post(url, {'first_name': 'Seán', 'last_name': 'Murphy', 'email': 'sean@example.com', 'password': 'Secure123!', 'confirm_password': 'Secure123!'})
    response = client.get(reverse('members:dashboard'))
    assert response.status_code == 200  # would be 302 redirect if not logged in

def test_register_success_returns_200(client):
    url = reverse('members:register_success')
    response = client.get(url)
    assert response.status_code == 200


# ── Authenticated user redirected away from register ──────────────────────────

def test_authenticated_user_register_shows_already_signed_in(client, db):
    user = User.objects.create_user(username='already@example.com', email='already@example.com', password='secret')
    client.login(username='already@example.com', password='secret')
    url = reverse('members:register')
    response = client.get(url)
    assert response.status_code == 200
    assert response.context.get('already_signed_in') is True
