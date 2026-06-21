import io
from celery import shared_task
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

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
