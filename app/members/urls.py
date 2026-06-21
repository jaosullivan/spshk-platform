from django.urls import path
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
]
