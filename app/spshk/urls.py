from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import logout
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.urls import path, include
from django.views.decorators.cache import never_cache


def healthz(request):
    return JsonResponse({'status': 'ok'})


def landing(request):
    return render(request, 'landing.html')


@never_cache
def logout_view(request):
    logout(request)
    return redirect('/')


urlpatterns = [
    path('admin/', admin.site.urls),
    path('healthz/', healthz, name='healthz'),
    path('logout/', logout_view, name='logout'),
    path('members/', include('members.urls', namespace='members')),
    path('tickets/', include('tickets.urls', namespace='tickets')),
    path('', landing, name='landing'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
