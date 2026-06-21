import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    membership_uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    is_green_card_holder = models.BooleanField(default=False)
    membership_activated_at = models.DateTimeField(null=True, blank=True)
    loyalty_points = models.PositiveIntegerField(default=0)
    member_qr = models.ImageField(upload_to='member_qr/', blank=True)
    stripe_customer_id = models.CharField(max_length=255, blank=True)
    # HK-PDPO compliance fields
    consent_given_at = models.DateTimeField(null=True, blank=True)
    data_retention_until = models.DateField(null=True, blank=True)

    def anonymize(self):
        """PDPO erasure: overwrite all PII with non-reversible placeholders."""
        self.username = f"deleted_{self.pk}"
        self.email = f"deleted_{self.pk}@invalid.invalid"
        self.first_name = ''
        self.last_name = ''
        self.is_active = False
        self.set_unusable_password()
        self.member_qr = ''
        self.consent_given_at = None
        self.data_retention_until = None
        self.save(update_fields=[
            'username', 'email', 'first_name', 'last_name',
            'is_active', 'password', 'member_qr',
            'consent_given_at', 'data_retention_until',
        ])
