import os

project_files = {
    # ----------------------------------------------------
    # CI/CD
    # ----------------------------------------------------
    ".github/workflows/deploy.yml": """name: SPSHK GitOps Continuous Integration & Deployment

on:
  push:
    branches:
      - main
    paths:
      - 'app/**'
      - '.github/workflows/deploy.yml'

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}/spshk-web
  GITOPS_DIR: k8s-gitops/environments/production

jobs:
  test-and-lint:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Codebase
        uses: actions/checkout@v4

      - name: Initialize Python Environment
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'

      - name: Install Application Dependencies
        run: |
          python -m pip install --upgrade pip
          pip install flake8 pytest -r app/requirements.txt

      - name: Execute Code Linting Check
        run: |
          flake8 app/ --count --select=E9,F63,F7,F82 --show-source --statistics
          flake8 app/ --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics

  build-and-push:
    needs: test-and-lint
    runs-on: ubuntu-latest
    permissions:
      contents: write
      packages: write
    outputs:
      short_sha: ${{ steps.meta.outputs.version }}
    steps:
      - name: Checkout Codebase
        uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Authenticate with GitHub Container Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Extract Metadata for Docker
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
          tags: |
            type=sha,format=short,prefix=
            type=raw,value=latest

      - name: Compile and Push Production Image
        uses: docker/build-push-action@v5
        with:
          context: ./app
          file: ./app/Dockerfile
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

  deploy-gitops:
    needs: build-and-push
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Codebase
        uses: actions/checkout@v4
        with:
          token: ${{ secrets.SPSHK_GITHUB_PAT || secrets.GITHUB_TOKEN }}

      - name: Install Kustomize
        uses: azure/setup-kustomize@v1

      - name: Update Target Image Tag using Kustomize
        run: |
          cd ${{ env.GITOPS_DIR }}
          kustomize edit set image ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}=${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ needs.build-and-push.outputs.short_sha }}

      - name: Commit and Push Changes back to Source GitOps Repo
        run: |
          git config --global user.name "SPSHK GitOps Automation"
          git config --global user.email "devops@stpatrickshk.org"
          git add ${{ env.GITOPS_DIR }}/kustomization.yaml
          if git diff --staged --quiet; then
            echo "No changes detected. Skipping."
          else
            git commit -m "chore(gitops): update image tag to ${{ needs.build-and-push.outputs.short_sha }} [skip ci]"
            git push origin main
          fi
""",

    # ----------------------------------------------------
    # DOCKER
    # ----------------------------------------------------
    "app/Dockerfile": """FROM python:3.11-slim AS builder
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
WORKDIR /build
RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --upgrade pip && pip wheel --no-cache-dir --no-deps --wheel-dir /build/wheels -r requirements.txt

FROM python:3.11-slim AS runner
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libpq5 && rm -rf /var/lib/apt/lists/*
COPY --from=builder /build/wheels /wheels
COPY --from=builder /build/requirements.txt .
RUN pip install --no-cache-dir /wheels/*
COPY . /app
RUN useradd -u 8888 django-user && chown -R django-user:django-user /app
USER django-user
EXPOSE 8000
CMD ["gunicorn", "spshk.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
""",

    # ----------------------------------------------------
    # KUBERNETES
    # Fix 4: secretGenerator added to production overlay.
    # secrets.env must exist locally (see secrets.env.example) and is gitignored.
    # Fix 5: migrate-job.yaml added to base with ArgoCD PreSync hook.
    # IMAGE_NAME expands to github.repository/spshk-web; images.name must match exactly.
    # ----------------------------------------------------
    "k8s-gitops/environments/production/kustomization.yaml": """apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

resources:
  - ../../base

namespace: spshk-prod

configMapGenerator:
  - name: spshk-production-env
    literals:
      - DJANGO_SETTINGS_MODULE=spshk.settings
      - ALLOWED_HOSTS=stpatrickshk.com,www.stpatrickshk.com
      - SPSHK_DOMAIN=stpatrickshk.com

secretGenerator:
  - name: spshk-secrets
    envs:
      - secrets.env

images:
  - name: ghcr.io/your-org/spshk-platform/spshk-web
    newTag: initial-bootstrap-placeholder
""",

    "k8s-gitops/environments/production/secrets.env.example": """DJANGO_SECRET_KEY=replace-with-a-strong-random-key
STRIPE_SECRET_KEY=sk_live_replace_me
STRIPE_WEBHOOK_SECRET=whsec_replace_me
DB_NAME=spshk
DB_USER=spshk
DB_PASSWORD=replace-with-strong-password
AWS_STORAGE_BUCKET_NAME=spshk-media
REDIS_URL=redis://redis:6379/0
""",

    "k8s-gitops/base/kustomization.yaml": """apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

resources:
  - deployment.yaml
  - service.yaml
  - migrate-job.yaml
""",

    "k8s-gitops/base/deployment.yaml": """apiVersion: apps/v1
kind: Deployment
metadata:
  name: spshk-web
spec:
  replicas: 2
  selector:
    matchLabels:
      app: spshk-web
  template:
    metadata:
      labels:
        app: spshk-web
    spec:
      containers:
        - name: spshk-web
          image: ghcr.io/your-org/spshk-platform/spshk-web:latest
          ports:
            - containerPort: 8000
          envFrom:
            - configMapRef:
                name: spshk-production-env
            - secretRef:
                name: spshk-secrets
          readinessProbe:
            httpGet:
              path: /healthz/
              port: 8000
            initialDelaySeconds: 10
            periodSeconds: 10
          livenessProbe:
            httpGet:
              path: /healthz/
              port: 8000
            initialDelaySeconds: 30
            periodSeconds: 30
""",

    "k8s-gitops/base/service.yaml": """apiVersion: v1
kind: Service
metadata:
  name: spshk-web
spec:
  selector:
    app: spshk-web
  ports:
    - protocol: TCP
      port: 80
      targetPort: 8000
""",

    # Fix 5: Migrations run as an isolated Job with ArgoCD PreSync hook.
    # ArgoCD runs this Job to completion before syncing any other resources.
    # HookSucceeded deletes the Job pod after a clean run.
    "k8s-gitops/base/migrate-job.yaml": """apiVersion: batch/v1
kind: Job
metadata:
  name: spshk-migrate
  annotations:
    argocd.argoproj.io/hook: PreSync
    argocd.argoproj.io/hook-delete-policy: HookSucceeded
spec:
  backoffLimit: 2
  template:
    spec:
      restartPolicy: Never
      containers:
        - name: migrate
          image: ghcr.io/your-org/spshk-platform/spshk-web:latest
          command: ["python", "manage.py", "migrate", "--noinput"]
          envFrom:
            - configMapRef:
                name: spshk-production-env
            - secretRef:
                name: spshk-secrets
""",

    # ----------------------------------------------------
    # ARGOCD
    # ----------------------------------------------------
    "argocd/application.yaml": """apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: spshk-production-app
  namespace: argocd
  finalizers:
    - resources-finalizer.argocd.argoproj.io
spec:
  project: default
  source:
    repoURL: 'https://github.com/your-org/spshk-platform'
    targetRevision: main
    path: k8s-gitops/environments/production
  destination:
    server: 'https://kubernetes.default.svc'
    namespace: spshk-prod
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
      - ApplyOutOfSyncOnly=true
    retry:
      limit: 5
""",

    # ----------------------------------------------------
    # GITIGNORE
    # ----------------------------------------------------
    ".gitignore": """# Secrets — never commit
secrets.env
*.env
.env

# Python
*.pyc
__pycache__/
*.pyo
*.egg-info/
dist/
build/
.venv/
venv/

# Django
staticfiles/
media/

# Editor
.vscode/
.idea/
*.swp
""",

    # ----------------------------------------------------
    # DJANGO — REQUIREMENTS
    # ----------------------------------------------------
    "app/requirements.txt": """django>=5.0,<5.1
psycopg2-binary>=2.9,<3.0
stripe>=8.0,<9.0
segno>=1.6,<2.0
pillow>=10.0,<11.0
gunicorn>=21.0,<22.0
celery>=5.3,<5.4
redis>=5.0,<6.0
django-storages[boto3]>=1.14,<1.15
django-prometheus>=2.3,<2.4
""",

    # ----------------------------------------------------
    # DJANGO — SPSHK CORE APP
    # ----------------------------------------------------
    "app/manage.py": """#!/usr/bin/env python
import os
import sys

def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'spshk.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)

if __name__ == '__main__':
    main()
""",

    "app/spshk/__init__.py": """from .celery import app as celery_app

__all__ = ('celery_app',)
""",

    "app/spshk/celery.py": """import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'spshk.settings')

app = Celery('spshk')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
""",

    "app/spshk/wsgi.py": """import os
from django.core.wsgi import get_wsgi_application
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'spshk.settings')
application = get_wsgi_application()
""",

    "app/spshk/urls.py": """from django.contrib import admin
from django.http import JsonResponse
from django.urls import path, include

def healthz(request):
    return JsonResponse({'status': 'ok'})

urlpatterns = [
    path('admin/', admin.site.urls),
    path('healthz/', healthz, name='healthz'),
    path('', include('members.urls', namespace='members')),
    path('tickets/', include('tickets.urls', namespace='tickets')),
]
""",

    "app/spshk/settings.py": """import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'fallback-unsafe-key-for-dev')
DEBUG = False
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '*').split(',')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_prometheus',
    'members',
    'tickets',
]

MIDDLEWARE = [
    'django_prometheus.middleware.PrometheusBeforeMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_prometheus.middleware.PrometheusAfterMiddleware',
]

ROOT_URLCONF = 'spshk.urls'
AUTH_USER_MODEL = 'members.CustomUser'
LOGIN_URL = '/admin/login/'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

DATABASES = {
    'default': {
        'ENGINE': 'django_prometheus.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME', 'spshk'),
        'USER': os.environ.get('DB_USER', 'postgres'),
        'PASSWORD': os.environ.get('DB_PASSWORD', ''),
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '5432'),
    }
}

DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
AWS_STORAGE_BUCKET_NAME = os.environ.get('AWS_STORAGE_BUCKET_NAME', 'spshk-media')
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY', '')
STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET', '')
SPSHK_DOMAIN = os.environ.get('SPSHK_DOMAIN', 'stpatrickshk.com')

CELERY_BROKER_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
""",

    # ----------------------------------------------------
    # DJANGO — MEMBERS APP
    # Fix 2: price_pence → price_hkd_cents throughout
    # Fix 3: signals dispatch Celery tasks (non-blocking)
    # Fix 6: anonymize() + admin action for PDPO erasure
    # ----------------------------------------------------
    "app/members/__init__.py": "",

    "app/members/apps.py": """from django.apps import AppConfig

class MembersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'members'

    def ready(self):
        import members.signals
""",

    "app/members/models.py": """import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    membership_uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    is_green_card_holder = models.BooleanField(default=False)
    membership_activated_at = models.DateTimeField(null=True, blank=True)
    loyalty_points = models.PositiveIntegerField(default=0)
    member_qr = models.ImageField(upload_to='member_qr/', blank=True)
    # HK-PDPO compliance fields
    consent_given_at = models.DateTimeField(null=True, blank=True)
    data_retention_until = models.DateField(null=True, blank=True)

    def anonymize(self):
        \"\"\"PDPO erasure: overwrite all PII with non-reversible placeholders.\"\"\"
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
""",

    # Fix 3: signals dispatch async Celery tasks — web workers never block on I/O
    "app/members/signals.py": """from django.db.models.signals import post_save
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
""",

    # Fix 3: async Celery task for member QR — isolated from the request cycle
    "app/members/tasks.py": """import io
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
""",

    "app/members/views.py": """from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from tickets.models import Event

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
""",

    "app/members/urls.py": """from django.urls import path
from . import views

app_name = 'members'

urlpatterns = [
    path('dashboard/', views.member_dashboard_view, name='dashboard'),
    path('calendar/', views.calendar_view, name='calendar'),
    path('profile/', views.profile_view, name='profile'),
    path('api/events/', views.api_event_feed, name='api_events'),
    path('api/events/feed/', views.calendar_event_feed, name='calendar_feed'),
]
""",

    # Fix 6: custom admin with PDPO anonymize bulk action
    "app/members/admin.py": """from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser

@admin.action(description='Anonymise selected members (PDPO erasure)')
def anonymize_members(modeladmin, request, queryset):
    for user in queryset:
        user.anonymize()

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    actions = [anonymize_members]
    fieldsets = UserAdmin.fieldsets + (
        ('Membership', {'fields': (
            'membership_uuid', 'is_green_card_holder',
            'membership_activated_at', 'loyalty_points', 'member_qr',
        )}),
        ('HK-PDPO', {'fields': ('consent_given_at', 'data_retention_until')}),
    )
    readonly_fields = ('membership_uuid', 'membership_activated_at', 'member_qr')
""",

    # ----------------------------------------------------
    # DJANGO — TICKETS APP
    # Fix 1: StripeWebhookLog model for Rule B idempotency
    # Fix 2: price_pence → price_hkd_cents
    # Fix 3: webhook dispatches Celery task for QR
    # ----------------------------------------------------
    "app/tickets/__init__.py": "",

    "app/tickets/apps.py": """from django.apps import AppConfig

class TicketsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'tickets'
""",

    "app/tickets/models.py": """from django.conf import settings
from django.db import models, transaction

class StripeWebhookLog(models.Model):
    \"\"\"Rule B: deduplicate incoming Stripe events by their unique event ID.\"\"\"
    stripe_event_id = models.CharField(max_length=255, unique=True)
    event_type = models.CharField(max_length=255)
    received_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=['stripe_event_id'])]

class Event(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    date = models.DateTimeField()
    venue = models.CharField(max_length=255, blank=True)
    capacity = models.PositiveIntegerField(default=0)
    # HKD stored as integer cents: HK$888 → 88800
    price_hkd_cents = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.title

class Ticket(models.Model):
    event = models.ForeignKey(Event, on_delete=models.PROTECT, related_name='tickets')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='tickets')
    stripe_payment_intent_id = models.CharField(max_length=255, unique=True)
    purchased_at = models.DateTimeField(auto_now_add=True)
    qr_code = models.ImageField(upload_to='qr_codes/', blank=True)

    class Meta:
        unique_together = [('event', 'user')]

    def __str__(self):
        return f"{self.user} — {self.event}"

    class SoldOut(Exception):
        pass

    @classmethod
    def claim(cls, event_id, user, payment_intent_id):
        \"\"\"Atomically claim one seat. Raises SoldOut if at capacity.\"\"\"
        with transaction.atomic():
            event = Event.objects.select_for_update().get(pk=event_id)
            if event.capacity > 0 and event.tickets.count() >= event.capacity:
                raise cls.SoldOut(f"{event.title} is sold out")
            return cls.objects.get_or_create(
                event=event,
                user=user,
                defaults={'stripe_payment_intent_id': payment_intent_id},
            )
""",

    "app/tickets/views.py": """import stripe
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
""",

    # Fix 3: async Celery task for ticket QR
    "app/tickets/tasks.py": """import io
from celery import shared_task
from django.core.files.base import ContentFile

@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def generate_ticket_qr_task(self, ticket_pk):
    import segno
    from .models import Ticket
    try:
        ticket = Ticket.objects.get(pk=ticket_pk)
    except Ticket.DoesNotExist:
        return
    if ticket.qr_code:
        return
    try:
        qr = segno.make(
            f"SPSHK-TICKET:{ticket.pk}:{ticket.stripe_payment_intent_id}", error='h'
        )
        buf = io.BytesIO()
        qr.save(buf, kind='png', scale=10)
        ticket.qr_code.save(f"ticket_{ticket.pk}.png", ContentFile(buf.getvalue()), save=True)
    except Exception as exc:
        raise self.retry(exc=exc)
""",

    "app/tickets/urls.py": """from django.urls import path
from . import views

app_name = 'tickets'

urlpatterns = [
    path('checkout/<int:event_id>/', views.create_stripe_checkout_session, name='checkout'),
    path('webhook/', views.stripe_webhook_handler, name='webhook'),
]
""",

    # ----------------------------------------------------
    # TEMPLATES
    # Fix 2: price_pence → price_hkd_cents in calendar modal
    # ----------------------------------------------------
    "app/templates/base.html": """<!doctype html>
<html lang="en" class="h-full">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{% block title %}SPSHK{% endblock %} — St Patrick's Society Hong Kong</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script>
    tailwind.config = {
      theme: {
        extend: {
          colors: {
            irish: {
              50:  '#f0fdf4',
              100: '#dcfce7',
              500: '#22c55e',
              600: '#009A44',
              700: '#15803d',
              800: '#166534',
              900: '#14532d',
            }
          }
        }
      }
    }
  </script>
  {% block extra_head %}{% endblock %}
</head>
<body class="h-full bg-gray-50 text-gray-900">

  <nav class="bg-irish-800 text-white shadow-lg">
    <div class="max-w-6xl mx-auto px-4 py-3 flex items-center justify-between">
      <a href="{% url 'members:dashboard' %}" class="flex items-center gap-2 font-bold text-xl tracking-tight">
        <span>&#9752;</span> SPSHK
      </a>
      <div class="flex items-center gap-6 text-sm font-medium">
        {% if user.is_authenticated %}
          <a href="{% url 'members:calendar' %}" class="hover:text-irish-100 transition-colors">Events</a>
          <a href="{% url 'members:dashboard' %}" class="hover:text-irish-100 transition-colors">Dashboard</a>
          <a href="/admin/logout/" class="bg-irish-600 hover:bg-irish-700 px-3 py-1.5 rounded-lg transition-colors">Sign out</a>
        {% else %}
          <a href="/admin/login/" class="bg-irish-600 hover:bg-irish-700 px-3 py-1.5 rounded-lg transition-colors">Sign in</a>
        {% endif %}
      </div>
    </div>
  </nav>

  <main class="max-w-6xl mx-auto px-4 py-8">
    {% if messages %}
      {% for message in messages %}
        <div class="mb-4 p-4 rounded-lg {% if message.tags == 'error' %}bg-red-50 text-red-800 border border-red-200{% else %}bg-irish-50 text-irish-800 border border-irish-200{% endif %}">
          {{ message }}
        </div>
      {% endfor %}
    {% endif %}
    {% block content %}{% endblock %}
  </main>

  <footer class="mt-16 border-t border-gray-200 py-6 text-center text-sm text-gray-400">
    &copy; {% now "Y" %} St Patrick's Society Hong Kong. All rights reserved.
  </footer>

</body>
</html>
""",

    "app/templates/members/calendar.html": """{% extends 'base.html' %}
{% block title %}Events Calendar{% endblock %}

{% block extra_head %}
<link href='https://cdn.jsdelivr.net/npm/fullcalendar@6.1.11/index.global.min.css' rel='stylesheet'>
<script src='https://cdn.jsdelivr.net/npm/fullcalendar@6.1.11/index.global.min.js'></script>
<style>
  .fc-toolbar-title { color: #166534; font-weight: 700; }
  .fc-button-primary { background-color: #009A44 !important; border-color: #166534 !important; }
  .fc-button-primary:hover { background-color: #15803d !important; }
  .fc-day-today { background-color: #f0fdf4 !important; }
</style>
{% endblock %}

{% block content %}
<div class="flex items-center justify-between mb-6">
  <h1 class="text-2xl font-bold text-irish-800">Events Calendar</h1>
  <span class="text-sm text-gray-500">Click an event to book tickets</span>
</div>

<div class="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
  <div id="calendar"></div>
</div>

<div id="event-modal" class="hidden fixed inset-0 bg-black/40 z-50 flex items-center justify-center">
  <div class="bg-white rounded-2xl shadow-xl p-6 max-w-sm w-full mx-4">
    <h2 id="modal-title" class="text-xl font-bold text-irish-800 mb-2"></h2>
    <p id="modal-venue" class="text-sm text-gray-500 mb-1"></p>
    <p id="modal-price" class="text-sm font-medium text-irish-700 mb-4"></p>
    <div class="flex gap-3">
      <a id="modal-book" href="#"
         class="flex-1 text-center bg-irish-600 hover:bg-irish-700 text-white font-medium py-2 rounded-lg transition-colors">
        Book Now
      </a>
      <button onclick="document.getElementById('event-modal').classList.add('hidden')"
              class="flex-1 border border-gray-300 hover:bg-gray-50 py-2 rounded-lg transition-colors">
        Close
      </button>
    </div>
  </div>
</div>

<script>
document.addEventListener('DOMContentLoaded', function () {
  const calendar = new FullCalendar.Calendar(document.getElementById('calendar'), {
    initialView: 'dayGridMonth',
    headerToolbar: { left: 'prev,next today', center: 'title', right: 'dayGridMonth,listMonth' },
    height: 'auto',
    eventColor: '#009A44',
    events: {
      url: "{% url 'members:calendar_feed' %}",
      failure: function () { alert('Could not load events.'); }
    },
    eventClick: function (info) {
      const ep = info.event.extendedProps;
      document.getElementById('modal-title').textContent = info.event.title;
      document.getElementById('modal-venue').textContent = ep.venue || 'Venue TBC';
      document.getElementById('modal-price').textContent = ep.price_hkd_cents
        ? 'HK$' + (ep.price_hkd_cents / 100).toFixed(2)
        : 'Free';
      document.getElementById('modal-book').href = '/tickets/checkout/' + info.event.id + '/';
      document.getElementById('event-modal').classList.remove('hidden');
    }
  });
  calendar.render();
});
</script>
{% endblock %}
""",

    "app/templates/members/dashboard.html": """{% extends 'base.html' %}
{% block title %}Member Dashboard{% endblock %}

{% block content %}
<div class="grid grid-cols-1 lg:grid-cols-3 gap-6">

  <div class="lg:col-span-1">
    <div class="bg-irish-800 text-white rounded-2xl p-6 shadow-lg">
      <div class="text-xs uppercase tracking-widest text-irish-200 mb-1">Member Pass</div>
      <h2 class="text-xl font-bold mb-0.5">{{ user.get_full_name|default:user.username }}</h2>
      <p class="text-irish-300 text-xs font-mono mb-4">{{ user.membership_uuid }}</p>

      {% if user.is_green_card_holder %}
        <span class="inline-block bg-irish-600 text-white text-xs font-semibold px-3 py-1 rounded-full mb-4">
          &#10003; Green Card Member
        </span>
        {% if user.membership_activated_at %}
          <p class="text-xs text-irish-200">Since {{ user.membership_activated_at|date:"d M Y" }}</p>
        {% endif %}
      {% endif %}

      <div class="mt-4 flex items-center gap-2">
        <span class="text-2xl font-bold">{{ user.loyalty_points }}</span>
        <span class="text-irish-300 text-sm">loyalty points</span>
      </div>

      {% if user.member_qr %}
        <div class="mt-5 bg-white rounded-xl p-2 inline-block">
          <img src="{{ user.member_qr.url }}" alt="Member QR" class="w-32 h-32">
        </div>
      {% endif %}
    </div>
  </div>

  <div class="lg:col-span-2">
    <div class="flex items-center justify-between mb-4">
      <h3 class="text-lg font-bold text-irish-800">Your Tickets</h3>
      <a href="{% url 'members:calendar' %}"
         class="text-sm text-irish-700 hover:text-irish-900 font-medium">Browse events &rarr;</a>
    </div>

    {% if tickets %}
      <div class="space-y-4">
        {% for ticket in tickets %}
          <div class="bg-white border border-gray-100 rounded-2xl shadow-sm p-4 flex items-center gap-4">
            {% if ticket.qr_code %}
              <img src="{{ ticket.qr_code.url }}" alt="Ticket QR" class="w-20 h-20 rounded-lg flex-shrink-0">
            {% else %}
              <div class="w-20 h-20 bg-gray-100 rounded-lg flex-shrink-0 flex items-center justify-center text-gray-300 text-2xl">&#9752;</div>
            {% endif %}
            <div class="min-w-0">
              <p class="font-semibold text-gray-900 truncate">{{ ticket.event.title }}</p>
              <p class="text-sm text-gray-500">{{ ticket.event.date|date:"D, d M Y · H:i" }}</p>
              {% if ticket.event.venue %}
                <p class="text-xs text-gray-400 mt-0.5">{{ ticket.event.venue }}</p>
              {% endif %}
            </div>
          </div>
        {% endfor %}
      </div>
    {% else %}
      <div class="bg-white border border-dashed border-gray-200 rounded-2xl p-10 text-center text-gray-400">
        <p class="text-4xl mb-2">&#9752;</p>
        <p class="font-medium">No tickets yet</p>
        <a href="{% url 'members:calendar' %}" class="mt-3 inline-block text-sm text-irish-700 hover:underline">
          Browse upcoming events
        </a>
      </div>
    {% endif %}
  </div>

</div>
{% endblock %}
""",
}

for path, content in project_files.items():
    dirpath = os.path.dirname(path)
    if dirpath:
        os.makedirs(dirpath, exist_ok=True)
    with open(path, "w") as f:
        f.write(content)
    print(f"  created: {path}")

print("\nBootstrap complete.")
