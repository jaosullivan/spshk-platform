from django.contrib.auth.decorators import login_required
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
