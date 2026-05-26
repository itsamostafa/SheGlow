from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.http import HttpResponse
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from accounts import views as accounts_views
from products.sitemaps import ProductSitemap, CategorySitemap, StaticSitemap


def favicon(request):
    return HttpResponse(status=204)


def robots_txt(request):
    lines = [
        'User-agent: *',
        'Disallow: /admin/',
        'Disallow: /accounts/',
        'Disallow: /cart/',
        'Disallow: /checkout/',
        'Disallow: /orders/',
        'Disallow: /admin-panel/',
        f'Sitemap: {request.scheme}://{request.get_host()}/sitemap.xml',
    ]
    return HttpResponse('\n'.join(lines), content_type='text/plain')


_sitemaps = {
    'products': ProductSitemap,
    'categories': CategorySitemap,
    'static': StaticSitemap,
}

urlpatterns = [
    path('favicon.ico', favicon),
    path('robots.txt', robots_txt),
    path('sitemap.xml', sitemap, {'sitemaps': _sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
    path('admin/', admin.site.urls),
    path('', include('products.urls')),
    path('accounts/', include('accounts.urls')),
    path('pages/', include('pages.urls')),
    path('', include('orders.urls')),
    path('admin-panel/', include('analytics.urls')),
    path('wishlist/', accounts_views.wishlist_view, name='wishlist'),
    path('wishlist/toggle/<int:product_id>/', accounts_views.wishlist_toggle, name='wishlist_toggle'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler404 = 'products.views.handler404'
