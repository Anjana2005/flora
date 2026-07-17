"""
URL configuration for Flora project.
"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static

from shop.media_storage import serve_media

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('shop.urls', namespace='shop')),
    path('cart/', include('cart.urls', namespace='cart')),
]

# Serve uploaded media from disk OR Postgres MediaBlob (survives Render redeploys)
urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', serve_media, name='serve_media'),
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
