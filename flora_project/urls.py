"""
URL configuration for Flora project.
"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('shop.urls', namespace='shop')),
    path('cart/', include('cart.urls', namespace='cart')),
]

# Always serve uploaded media (admin product images, etc.).
# Required on Render where DEBUG=False — without this, /media/* is 404 for users.
urlpatterns += [
    re_path(
        r'^media/(?P<path>.*)$',
        serve,
        {'document_root': settings.MEDIA_ROOT},
    ),
]

if settings.DEBUG:
    urlpatterns += static(
        settings.STATIC_URL,
        document_root=settings.STATICFILES_DIRS[0]
        if settings.STATICFILES_DIRS
        else settings.STATIC_ROOT,
    )

# Customize admin site
admin.site.site_header = "Flora Admin"
admin.site.site_title = "Flora Admin Portal"
admin.site.index_title = "Welcome to Flora Administration"