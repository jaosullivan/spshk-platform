from django.urls import path
from . import views

app_name = 'tickets'

urlpatterns = [
    path('checkout/<int:event_id>/', views.create_stripe_checkout_session, name='checkout'),
    path('webhook/', views.stripe_webhook_handler, name='webhook'),
]
