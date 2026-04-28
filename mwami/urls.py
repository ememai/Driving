"""
URL configuration for mwami project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
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

urlpatterns = [ 
    path('admin/', admin.site.urls),
    path('', include('app.urls')),
    path("__reload__/", include("django_browser_reload.urls")),
    path('auth/', include('social_django.urls', namespace='social')),
    # path('ckeditor/', include('ckeditor_uploader.urls')),
    path('login/admin/', include('dashboard.urls')),
    path('dashboard/', include('dashboard.urls')),
]

# Serve media files from the persistent volume with proper headers
if settings.MEDIA_ROOT:
    from django.views.static import serve
    from django.urls import re_path

    def serve_media(request, path):
        """Serve media files with proper content-type headers"""
        return serve(request, path, document_root=settings.MEDIA_ROOT)

    urlpatterns += [
        re_path(r'^media/(?P<path>.*)$', serve_media, name='media'),
    ]
# urlpatterns += path('pptx/', include('record.urls')), 

handler404 = 'app.views.custom_page_not_found'
