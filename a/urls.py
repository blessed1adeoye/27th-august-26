# a/urls.py

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('b.urls', namespace='b'))
]


admin.site.title = "BROWSER TITLE"
admin.site.site_header = "OMOBUWA BLESSED ADEOYE ELECTRONIC HEALTH INFORMATION SYSTEM"
admin.site.index_title = "Welcome to Blessedera GlowTechies 2025 Dashboard"

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)