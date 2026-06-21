from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.utils import timezone
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

def register_view(request):
    if request.user.is_authenticated:
        return redirect('members:dashboard')

    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name  = request.POST.get('last_name', '').strip()
        email      = request.POST.get('email', '').strip().lower()

        if not (first_name and last_name and email):
            messages.error(request, 'Please fill in all fields.')
            return render(request, 'members/register.html', {'post': request.POST})

        from django.contrib.auth import get_user_model
        User = get_user_model()

        if User.objects.filter(email=email).exists():
            messages.error(request, 'An account with that email already exists. Please sign in.')
            return render(request, 'members/register.html', {'post': request.POST})

        import secrets
        password = secrets.token_urlsafe(16)
        user = User.objects.create_user(
            username=email,
            email=email,
            first_name=first_name,
            last_name=last_name,
            password=password,
            is_green_card_holder=True,
            consent_given_at=timezone.now(),
        )
        messages.success(
            request,
            f'Welcome, {first_name}! Your Green Card membership is active. '
            f'Check your email for sign-in instructions, or contact info@stpatrickshk.com.'
        )
        return redirect('members:register_success')

    return render(request, 'members/register.html', {})


def register_success_view(request):
    return render(request, 'members/register_success.html', {})


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
