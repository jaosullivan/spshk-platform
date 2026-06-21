from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy
from . import views

app_name = 'members'

urlpatterns = [
    path('', views.member_dashboard_view, name='dashboard'),
    path('register/', views.register_view, name='register'),
    path('register/success/', views.register_success_view, name='register_success'),
    path('dashboard/', views.member_dashboard_view, name='dashboard'),
    path('calendar/', views.calendar_view, name='calendar'),
    path('profile/', views.profile_view, name='profile'),
    path('api/events/', views.api_event_feed, name='api_events'),
    path('api/events/feed/', views.calendar_event_feed, name='calendar_feed'),

    # Stripe payment flow
    path('checkout/', views.checkout_view, name='checkout'),
    path('payment/success/', views.payment_success_view, name='payment_success'),
    path('payment/cancel/', views.payment_cancel_view, name='payment_cancel'),
    path('webhook/stripe/', views.stripe_webhook_view, name='stripe_webhook'),

    # Authentication
    path('login/', auth_views.LoginView.as_view(
        template_name='members/login.html',
        redirect_authenticated_user=True,
        next_page='members:dashboard',
    ), name='login'),

    # Password reset flow
    path('password/reset/', auth_views.PasswordResetView.as_view(
        template_name='members/password_reset.html',
        email_template_name='members/email/password_reset.txt',
        subject_template_name='members/email/password_reset_subject.txt',
        success_url=reverse_lazy('members:password_reset_done'),
    ), name='password_reset'),
    path('password/reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='members/password_reset_done.html',
    ), name='password_reset_done'),
    path('password/reset/confirm/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='members/password_reset_confirm.html',
        success_url=reverse_lazy('members:password_reset_complete'),
    ), name='password_reset_confirm'),
    path('password/reset/complete/', auth_views.PasswordResetCompleteView.as_view(
        template_name='members/password_reset_complete.html',
    ), name='password_reset_complete'),
]
