"""
URL configuration for attendance_system project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

def health_check(request):
    """Health check endpoint for production monitoring"""
    return JsonResponse({
        'status': 'healthy',
        'message': 'Django API is running',
        'environment': getattr(settings, 'ENVIRONMENT', 'development')
    })

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
    path('health/', health_check, name='health_check'),
]

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
else:
    # In production, static files should be served by the web server (nginx/apache)
    # But we'll keep the media files serving for now
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Custom 404 and 500 error handlers for production
handler404 = 'core.views.custom_404'
handler500 = 'core.views.custom_500'
