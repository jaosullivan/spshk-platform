from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from .models import CustomUser

@receiver(post_save, sender=CustomUser)
def stamp_membership_activation(sender, instance, created, **kwargs):
    if not created and instance.is_green_card_holder and instance.membership_activated_at is None:
        CustomUser.objects.filter(pk=instance.pk).update(membership_activated_at=timezone.now())

@receiver(post_save, sender=CustomUser)
def dispatch_member_qr(sender, instance, **kwargs):
    if instance.is_green_card_holder and not instance.member_qr:
        from members.tasks import generate_member_qr_task
        generate_member_qr_task.delay(instance.pk)
