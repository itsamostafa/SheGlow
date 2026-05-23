from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from accounts import views as accounts_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('products.urls')),
    path('accounts/', include('accounts.urls')),
    path('pages/', include('pages.urls')),
    path('', include('orders.urls')),
    path('wishlist/', accounts_views.wishlist_view, name='wishlist'),
    path('wishlist/toggle/<int:product_id>/', accounts_views.wishlist_toggle, name='wishlist_toggle'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler404 = 'products.views.handler404'
