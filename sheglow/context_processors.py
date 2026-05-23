from django.conf import settings


def site_settings(request):
    return {
        'WHATSAPP_NUMBER': settings.WHATSAPP_NUMBER,
        'INSTAGRAM_URL': settings.INSTAGRAM_URL,
        'SITE_NAME': 'SheGlow',
        'SITE_TAGLINE': 'Glow with every detail',
    }


def cart_count(request):
    count = 0
    try:
        if request.user.is_authenticated:
            cart = request.user.cart
            count = cart.get_item_count()
        elif hasattr(request, 'session') and request.session.session_key:
            from orders.models import Cart
            cart = Cart.objects.filter(session_key=request.session.session_key).first()
            if cart:
                count = cart.get_item_count()
    except Exception:
        pass
    return {'cart_count': count}


def wishlist_context(request):
    if request.user.is_authenticated:
        try:
            from accounts.models import Wishlist
            ids = set(Wishlist.objects.filter(user=request.user).values_list('product_id', flat=True))
            return {'wishlist_ids': ids, 'wishlist_count': len(ids)}
        except Exception:
            pass
    return {'wishlist_ids': set(), 'wishlist_count': 0}
