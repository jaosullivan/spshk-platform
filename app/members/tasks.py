import io
from celery import shared_task
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.mail import send_mail
from django.conf import settings

@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def generate_member_qr_task(self, user_pk):
    import segno
    from django.contrib.auth import get_user_model
    User = get_user_model()
    try:
        user = User.objects.get(pk=user_pk)
    except User.DoesNotExist:
        return
    if user.member_qr:
        return
    try:
        qr = segno.make(f"SPSHK-MEMBER:{user.membership_uuid}", error='h')
        buf = io.BytesIO()
        qr.save(buf, kind='png', scale=8)
        path = default_storage.save(
            f"member_qr/member_{user_pk}.png",
            ContentFile(buf.getvalue()),
        )
        User.objects.filter(pk=user_pk).update(member_qr=path)
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def send_welcome_email_task(self, user_pk):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    try:
        user = User.objects.get(pk=user_pk)
    except User.DoesNotExist:
        return
    try:
        send_mail(
            subject='Welcome to the St. Patrick\'s Society of Hong Kong',
            message=(
                f"Dear {user.first_name},\n\n"
                f"Your Green Card membership is now active.\n\n"
                f"Membership ID: {user.membership_uuid}\n\n"
                f"You'll receive event invitations, our monthly newsletter, and discounts "
                f"at partner venues across Hong Kong.\n\n"
                f"Sign in at any time: https://stpatrickshk.com/members/login/\n\n"
                f"Warmly,\n"
                f"The SPSHK Committee\n"
                f"info@stpatrickshk.com"
            ),
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'info@stpatrickshk.com'),
            recipient_list=[user.email],
            fail_silently=False,
        )
        generate_member_qr_task.delay(user_pk)
    except Exception as exc:
        raise self.retry(exc=exc)
