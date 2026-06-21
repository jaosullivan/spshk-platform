"""
TDD — CustomUser model
Red: write test → Green: make it pass → Refactor
"""
import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='secret',
        first_name='Seán',
        last_name='Murphy',
    )


@pytest.fixture
def green_card_user(db):
    return User.objects.create_user(
        username='green@example.com',
        email='green@example.com',
        password='secret',
        first_name='Aine',
        last_name="O'Brien",
        is_green_card_holder=True,
        consent_given_at=timezone.now(),
    )


# ── Field defaults ─────────────────────────────────────────────────────────────

def test_membership_uuid_is_auto_generated(user):
    assert user.membership_uuid is not None


def test_two_users_have_different_uuids(db):
    u1 = User.objects.create_user(username='a', password='x')
    u2 = User.objects.create_user(username='b', password='x')
    assert u1.membership_uuid != u2.membership_uuid


def test_new_user_is_not_green_card_holder_by_default(user):
    assert user.is_green_card_holder is False


def test_new_user_loyalty_points_default_to_zero(user):
    assert user.loyalty_points == 0


def test_new_user_consent_is_null_by_default(user):
    assert user.consent_given_at is None


def test_new_user_data_retention_is_null_by_default(user):
    assert user.data_retention_until is None


# ── PDPO anonymize() ───────────────────────────────────────────────────────────

def test_anonymize_clears_first_name(user):
    user.anonymize()
    assert user.first_name == ''


def test_anonymize_clears_last_name(user):
    user.anonymize()
    assert user.last_name == ''


def test_anonymize_replaces_email_with_invalid_placeholder(user):
    pk = user.pk
    user.anonymize()
    assert user.email == f'deleted_{pk}@invalid.invalid'


def test_anonymize_replaces_username_with_deleted_prefix(user):
    pk = user.pk
    user.anonymize()
    assert user.username == f'deleted_{pk}'


def test_anonymize_deactivates_account(user):
    user.anonymize()
    assert user.is_active is False


def test_anonymize_makes_password_unusable(user):
    user.anonymize()
    assert not user.has_usable_password()


def test_anonymize_clears_consent_given_at(green_card_user):
    green_card_user.anonymize()
    assert green_card_user.consent_given_at is None


def test_anonymize_persists_to_database(user):
    pk = user.pk
    user.anonymize()
    refreshed = User.objects.get(pk=pk)
    assert refreshed.email == f'deleted_{pk}@invalid.invalid'
    assert refreshed.is_active is False
