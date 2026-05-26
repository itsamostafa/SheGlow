import io
import json
import hashlib
import hmac
import urllib.request
from decimal import Decimal

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import F
from django.core.mail import EmailMultiAlternatives
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from products.models import Product
from accounts.models import Customer, EGYPTIAN_GOVERNORATES
from .models import Cart, CartItem, PromoCode, Order, OrderItem, PaymentReceipt, ShippingZone


# ─────────────────────────── CART HELPERS ───────────────────────────────────

def get_or_create_cart(request):
    """Return the active Cart object for this request (user or session)."""
    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=request.user)
        return cart
    if not request.session.session_key:
        request.session.create()
    cart, _ = Cart.objects.get_or_create(
        session_key=request.session.session_key,
        user=None,
    )
    return cart


def merge_carts(user, session_key):
    """Merge a guest session cart into a user cart. Called on login."""
    try:
        guest_cart = Cart.objects.get(session_key=session_key, user=None)
    except Cart.DoesNotExist:
        return
    user_cart, _ = Cart.objects.get_or_create(user=user)
    for item in guest_cart.items.select_related('product').all():
        existing = user_cart.items.filter(product=item.product).first()
        if existing:
            existing.quantity = min(existing.quantity + item.quantity, item.product.stock)
            existing.save()
        else:
            CartItem.objects.create(cart=user_cart, product=item.product, quantity=item.quantity)
    guest_cart.delete()


def cart_item_count(request):
    """Return total cart item count for this request."""
    try:
        cart = get_or_create_cart(request)
        return cart.get_item_count()
    except Exception:
        return 0


# ─────────────────────────── CART VIEWS ─────────────────────────────────────

def cart_view(request):
    cart = get_or_create_cart(request)
    items = list(cart.items.select_related('product__category').prefetch_related('product__images').all())
    subtotal = sum(item.subtotal for item in items)
    shipping_fee = Decimal(str(settings.DEFAULT_SHIPPING_FEE)) if subtotal > 0 else Decimal('0')

    cart_items_data = []
    for item in items:
        img = item.product.primary_image
        cart_items_data.append({
            'id': item.product.id,
            'name': item.product.name,
            'slug': item.product.slug,
            'category': item.product.category.name if item.product.category else '',
            'price': float(item.product.effective_price),
            'qty': item.quantity,
            'stock': item.product.stock,
            'image': img.image.url if img else '',
        })

    return render(request, 'orders/cart.html', {
        'cart': cart,
        'items': items,
        'subtotal': subtotal,
        'shipping_fee': shipping_fee,
        'total': subtotal + shipping_fee,
        'cart_items_json': json.dumps(cart_items_data),
    })


@require_POST
def add_to_cart(request, product_id):
    try:
        product = Product.objects.get(pk=product_id, is_active=True)
    except Product.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Product not found.'}, status=404)

    if product.stock <= 0:
        return JsonResponse({'success': False, 'message': 'This product is out of stock.'})

    try:
        body = json.loads(request.body)
        qty = int(body.get('quantity', 1))
    except (json.JSONDecodeError, ValueError, TypeError):
        qty = 1
    qty = max(1, min(qty, product.stock))

    cart = get_or_create_cart(request)
    item, created = CartItem.objects.get_or_create(cart=cart, product=product, defaults={'quantity': qty})
    if not created:
        item.quantity = min(item.quantity + qty, product.stock)
        item.save()

    return JsonResponse({
        'success': True,
        'message': f'"{product.name}" added to cart!',
        'cart_count': cart.get_item_count(),
    })


@require_POST
def remove_from_cart(request, product_id):
    cart = get_or_create_cart(request)
    cart.items.filter(product_id=product_id).delete()
    return JsonResponse({'success': True, 'cart_count': cart.get_item_count()})


@require_POST
def update_cart(request, product_id):
    try:
        body = json.loads(request.body)
        qty = int(body.get('quantity', 1))
    except (json.JSONDecodeError, ValueError, TypeError):
        qty = 1

    cart = get_or_create_cart(request)
    if qty <= 0:
        cart.items.filter(product_id=product_id).delete()
    else:
        item = cart.items.filter(product_id=product_id).first()
        if item:
            item.quantity = min(qty, item.product.stock)
            item.save()

    return JsonResponse({'success': True, 'cart_count': cart.get_item_count()})


# ─────────────────────────── PROMO CODE ──────────────────────────────────────

@require_POST
def apply_promo(request):
    try:
        body = json.loads(request.body)
        code = body.get('code', '').upper().strip()
        subtotal = Decimal(str(body.get('subtotal', 0)))
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'success': False, 'message': 'Invalid request.'})

    if not code:
        return JsonResponse({'success': False, 'message': 'Please enter a promo code.'})

    try:
        promo = PromoCode.objects.get(code=code)
    except PromoCode.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Invalid promo code.'})

    valid, msg = promo.is_valid(subtotal)
    if not valid:
        return JsonResponse({'success': False, 'message': msg})

    discount = promo.calculate_discount(subtotal)
    return JsonResponse({
        'success': True,
        'message': f'Code applied! You save {discount} EGP.',
        'discount_amount': str(discount),
        'code': promo.code,
        'discount_type': promo.discount_type,
        'discount_value': str(promo.discount_value),
    })


# ─────────────────────────── EMAIL ───────────────────────────────────────────

def send_order_confirmation_email(order, request):
    recipient = order.email or (order.user.email if order.user else None)
    if not recipient:
        return
    ctx = {
        'order': order,
        'protocol': request.scheme,
        'domain': request.get_host(),
    }
    subject = f'Order Confirmed — {order.order_number}'
    text_body = render_to_string('accounts/emails/order_confirmation.txt', ctx)
    html_body = render_to_string('accounts/emails/order_confirmation_html.html', ctx)
    try:
        msg = EmailMultiAlternatives(subject, text_body, settings.DEFAULT_FROM_EMAIL, [recipient])
        msg.attach_alternative(html_body, 'text/html')
        msg.send()
    except Exception:
        pass  # Never block order creation due to email failure


# ─────────────────────────── SHIPPING FEES ───────────────────────────────────

def get_shipping_fee(governorate):
    """Return the shipping fee for a governorate, falling back to settings default."""
    if governorate:
        try:
            zone = ShippingZone.objects.get(governorate=governorate, is_active=True)
            return zone.shipping_fee
        except ShippingZone.DoesNotExist:
            pass
    return Decimal(str(settings.DEFAULT_SHIPPING_FEE))


def shipping_fee_api(request):
    governorate = request.GET.get('governorate', '').strip()
    fee = get_shipping_fee(governorate)
    delivery_days = None
    if governorate:
        try:
            zone = ShippingZone.objects.get(governorate=governorate, is_active=True)
            delivery_days = zone.delivery_days
        except ShippingZone.DoesNotExist:
            pass
    return JsonResponse({'fee': str(fee), 'delivery_days': delivery_days})


# ─────────────────────────── CHECKOUT ────────────────────────────────────────

def checkout_view(request):
    cart = get_or_create_cart(request)
    items = list(cart.items.select_related('product').prefetch_related('product__images').all())

    if not items:
        messages.warning(request, 'Your cart is empty.')
        return redirect('orders:cart')

    # Check stock availability
    out_of_stock = [i for i in items if i.product.stock < i.quantity]
    if out_of_stock:
        names = ', '.join(i.product.name for i in out_of_stock)
        messages.error(request, f'Some items are out of stock: {names}. Please update your cart.')
        return redirect('orders:cart')

    subtotal = sum(item.subtotal for item in items)

    # Pre-fill from customer profile
    values = {
        'full_name': '', 'email': '', 'phone': '',
        'address': '', 'city': '', 'governorate': '',
        'payment_method': 'cod', 'promo_code': '', 'save_address': False,
    }
    if request.user.is_authenticated:
        values['full_name'] = request.user.get_full_name()
        values['email'] = request.user.email or ''
        values['phone'] = request.user.phone or ''
        try:
            c = request.user.customer
            values['address'] = c.address or ''
            values['city'] = c.city or ''
            values['governorate'] = c.governorate or ''
        except Exception:
            pass

    shipping_fee = get_shipping_fee(values['governorate'])

    if request.method == 'POST':
        return _process_checkout(request, cart, items, subtotal)

    return render(request, 'orders/checkout.html', {
        'items': items,
        'subtotal': subtotal,
        'shipping_fee': shipping_fee,
        'total': subtotal + shipping_fee,
        'values': values,
        'errors': {},
        'governorates': EGYPTIAN_GOVERNORATES,
        'paymob_enabled': settings.PAYMOB_ENABLED,
        'instapay_id': settings.INSTAPAY_ID,
        'vodafone_cash_number': settings.VODAFONE_CASH_NUMBER,
    })


def _process_checkout(request, cart, items, subtotal):
    """Handle checkout form POST — validate, create order, clear cart."""
    post = request.POST
    errors = {}

    # Validate required fields (email is optional)
    required = ['full_name', 'phone', 'address', 'city', 'governorate', 'payment_method']
    for field in required:
        if not post.get(field, '').strip():
            errors[field] = 'This field is required.'

    payment_method = post.get('payment_method', 'cod')
    valid_methods = ['cod', 'instapay', 'vodafone_cash']
    if settings.PAYMOB_ENABLED:
        valid_methods.append('paymob')
    if payment_method not in valid_methods:
        errors['payment_method'] = 'Invalid payment method.'

    receipt_file = request.FILES.get('receipt_image')
    if payment_method in ('instapay', 'vodafone_cash') and not receipt_file:
        errors['receipt_image'] = 'Please upload your payment receipt.'

    # Compute shipping fee from governorate (live update)
    shipping_fee = get_shipping_fee(post.get('governorate', '').strip())

    if errors:
        all_items = list(cart.items.select_related('product').prefetch_related('product__images').all())
        values = {
            'full_name': post.get('full_name', ''),
            'email': post.get('email', ''),
            'phone': post.get('phone', ''),
            'address': post.get('address', ''),
            'city': post.get('city', ''),
            'governorate': post.get('governorate', ''),
            'payment_method': post.get('payment_method', 'cod'),
            'promo_code': post.get('promo_code', ''),
            'save_address': bool(post.get('save_address')),
        }
        return render(request, 'orders/checkout.html', {
            'items': all_items,
            'subtotal': subtotal,
            'shipping_fee': shipping_fee,
            'total': subtotal + shipping_fee,
            'errors': errors,
            'values': values,
            'governorates': EGYPTIAN_GOVERNORATES,
            'paymob_enabled': settings.PAYMOB_ENABLED,
            'instapay_id': settings.INSTAPAY_ID,
            'vodafone_cash_number': settings.VODAFONE_CASH_NUMBER,
        })

    # Apply promo code
    discount_amount = Decimal('0')
    promo_obj = None
    promo_code_str = post.get('promo_code', '').upper().strip()
    if promo_code_str:
        try:
            promo_obj = PromoCode.objects.get(code=promo_code_str)
            valid, _ = promo_obj.is_valid(subtotal)
            if valid:
                discount_amount = promo_obj.calculate_discount(subtotal)
        except PromoCode.DoesNotExist:
            pass

    total = subtotal + shipping_fee - discount_amount

    # Final stock check before order creation
    for item in items:
        item.product.refresh_from_db()
        if item.product.stock < item.quantity:
            messages.error(request, f'"{item.product.name}" only has {item.product.stock} left.')
            return redirect('orders:cart')

    # Create order
    order = Order.objects.create(
        user=request.user if request.user.is_authenticated else None,
        full_name=post['full_name'].strip(),
        email=post['email'].strip(),
        phone=post['phone'].strip(),
        address=post['address'].strip(),
        city=post['city'].strip(),
        governorate=post['governorate'].strip(),
        subtotal=subtotal,
        shipping_fee=shipping_fee,
        discount_amount=discount_amount,
        promo_code=promo_obj,
        total=total,
        payment_method=payment_method,
        payment_status='pending',
        status='pending',
    )

    # Create order items & decrement stock
    for item in items:
        OrderItem.objects.create(
            order=order,
            product=item.product,
            product_name=item.product.name,
            price=item.product.effective_price,
            quantity=item.quantity,
            subtotal=item.subtotal,
        )
        Product.objects.filter(pk=item.product.pk).update(stock=F('stock') - item.quantity)

    # Increment promo usage
    if promo_obj:
        PromoCode.objects.filter(pk=promo_obj.pk).update(times_used=F('times_used') + 1)

    # Handle receipt upload
    if receipt_file:
        PaymentReceipt.objects.create(order=order, image=receipt_file)

    # Save address to profile if requested
    if request.user.is_authenticated and post.get('save_address'):
        customer, _ = Customer.objects.get_or_create(user=request.user)
        customer.address = post['address'].strip()
        customer.city = post['city'].strip()
        customer.governorate = post['governorate'].strip()
        customer.save()

    # Clear cart
    cart.items.all().delete()

    # Send confirmation email (non-blocking)
    send_order_confirmation_email(order, request)

    # PayMob redirect if applicable
    if payment_method == 'paymob' and settings.PAYMOB_ENABLED:
        return _initiate_paymob(request, order)

    return redirect('orders:order_confirmation', order_number=order.order_number)


# ─────────────────────────── PAYMOB INTEGRATION ──────────────────────────────

def _initiate_paymob(request, order):
    """
    PayMob payment initiation flow.
    To enable: set PAYMOB_ENABLED=True and fill in your PayMob API credentials in .env.

    Steps:
    1. Authenticate → get auth_token
    2. Register order → get order_id
    3. Request payment key → get payment_key
    4. Redirect to PayMob iframe using PAYMOB_IFRAME_ID
    """
    try:
        # Step 1: Authenticate
        auth_resp = _paymob_request('https://accept.paymob.com/api/auth/tokens', {
            'api_key': settings.PAYMOB_API_KEY
        })
        auth_token = auth_resp['token']

        # Step 2: Register order
        amount_cents = int(order.total * 100)
        order_resp = _paymob_request('https://accept.paymob.com/api/ecommerce/orders', {
            'auth_token': auth_token,
            'delivery_needed': False,
            'amount_cents': amount_cents,
            'currency': 'EGP',
            'merchant_order_id': order.order_number,
            'items': [],
        })
        paymob_order_id = order_resp['id']

        # Step 3: Request payment key
        billing = {
            'apartment': 'NA', 'email': order.email,
            'floor': 'NA', 'first_name': order.full_name.split()[0],
            'street': order.address, 'building': 'NA',
            'phone_number': order.phone, 'shipping_method': 'NA',
            'postal_code': 'NA', 'city': order.city,
            'country': 'EG', 'last_name': ' '.join(order.full_name.split()[1:]) or 'NA',
            'state': order.governorate,
        }
        key_resp = _paymob_request('https://accept.paymob.com/api/acceptance/payment_keys', {
            'auth_token': auth_token,
            'amount_cents': amount_cents,
            'expiration': 3600,
            'order_id': paymob_order_id,
            'billing_data': billing,
            'currency': 'EGP',
            'integration_id': settings.PAYMOB_INTEGRATION_ID,
        })
        payment_key = key_resp['token']

        # Step 4: Redirect to PayMob iframe
        iframe_url = f'https://accept.paymob.com/api/acceptance/iframes/{settings.PAYMOB_IFRAME_ID}?payment_token={payment_key}'
        return redirect(iframe_url)

    except Exception as e:
        order.payment_status = 'failed'
        order.save(update_fields=['payment_status'])
        messages.error(request, f'Payment initiation failed: {e}. Please try a different payment method.')
        return redirect('orders:order_confirmation', order_number=order.order_number)


def _paymob_request(url, data):
    payload = json.dumps(data).encode('utf-8')
    req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode('utf-8'))


@csrf_exempt
def paymob_callback(request):
    """
    PayMob webhook/callback endpoint.
    URL: /payment/paymob-callback/
    Add this URL to your PayMob dashboard under Webhooks.

    Verifies the HMAC signature and updates the order status.
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            obj = data.get('obj', {})
            success = obj.get('success', False)
            merchant_order_id = obj.get('order', {}).get('merchant_order_id', '')

            # Verify HMAC signature (PayMob sends it as ?hmac= query param)
            received_hmac = request.GET.get('hmac', '')
            if settings.PAYMOB_HMAC_SECRET and received_hmac:
                expected = _compute_paymob_hmac(obj, settings.PAYMOB_HMAC_SECRET)
                if not hmac.compare_digest(received_hmac, expected):
                    return HttpResponse('Invalid HMAC', status=403)

            try:
                order = Order.objects.get(order_number=merchant_order_id)
                if success:
                    order.payment_status = 'paid'
                    order.status = 'confirmed'
                else:
                    order.payment_status = 'failed'
                order.save(update_fields=['payment_status', 'status'])
            except Order.DoesNotExist:
                pass
        except Exception:
            pass
    return HttpResponse('OK')


def _compute_paymob_hmac(obj, secret):
    """Compute HMAC for PayMob callback verification."""
    fields = [
        'amount_cents', 'created_at', 'currency', 'error_occured',
        'has_parent_transaction', 'id', 'integration_id', 'is_3d_secure',
        'is_auth', 'is_capture', 'is_refunded', 'is_standalone_payment',
        'is_voided', 'order', 'owner', 'pending', 'source_data_pan',
        'source_data_sub_type', 'source_data_type', 'success',
    ]
    concatenated = ''.join(str(obj.get(f, '')) for f in fields)
    return hmac.new(secret.encode(), concatenated.encode(), hashlib.sha512).hexdigest()


# ─────────────────────────── ORDER VIEWS ─────────────────────────────────────

def order_confirmation(request, order_number):
    order = get_object_or_404(Order, order_number=order_number)
    # Only allow the owner (or admin) to view
    if order.user and request.user.is_authenticated and order.user != request.user and not request.user.is_staff:
        return redirect('home')
    items = order.items.all()
    try:
        receipt = order.receipt
    except PaymentReceipt.DoesNotExist:
        receipt = None
    return render(request, 'orders/order_confirmation.html', {
        'order': order,
        'items': items,
        'receipt': receipt,
    })


@login_required
def order_invoice_pdf(request, order_number):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT

    order = get_object_or_404(Order, order_number=order_number)
    if order.user and order.user != request.user and not request.user.is_staff:
        return redirect('home')

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)

    styles = getSampleStyleSheet()
    rose = colors.HexColor('#F43F5E')
    charcoal = colors.HexColor('#1F2937')
    light_rose = colors.HexColor('#FFF0F3')

    title_style = ParagraphStyle('Title', parent=styles['Normal'],
                                 fontSize=28, textColor=rose,
                                 fontName='Helvetica-Bold', spaceAfter=2)
    subtitle_style = ParagraphStyle('Sub', parent=styles['Normal'],
                                    fontSize=9, textColor=colors.gray)
    label_style = ParagraphStyle('Label', parent=styles['Normal'],
                                 fontSize=8, textColor=colors.gray,
                                 fontName='Helvetica-Bold', spaceBefore=8)
    value_style = ParagraphStyle('Value', parent=styles['Normal'],
                                 fontSize=9, textColor=charcoal)
    right_style = ParagraphStyle('Right', parent=styles['Normal'],
                                 fontSize=9, alignment=TA_RIGHT)
    bold_right = ParagraphStyle('BoldRight', parent=styles['Normal'],
                                fontSize=10, alignment=TA_RIGHT,
                                fontName='Helvetica-Bold', textColor=charcoal)

    story = []

    # Header
    story.append(Paragraph('SheGlow', title_style))
    story.append(Paragraph('Beauty & Skincare', subtitle_style))
    story.append(Spacer(1, 0.4*cm))
    story.append(HRFlowable(width='100%', thickness=1, color=rose))
    story.append(Spacer(1, 0.3*cm))

    # Invoice meta (two-column)
    meta_data = [
        [Paragraph('INVOICE', ParagraphStyle('inv', parent=styles['Normal'],
                                              fontSize=14, fontName='Helvetica-Bold', textColor=charcoal)),
         Paragraph(f'Order: {order.order_number}', right_style)],
        [Paragraph(f'Date: {order.created_at.strftime("%d %B %Y")}', value_style),
         Paragraph(f'Status: {order.get_status_display()}', right_style)],
    ]
    meta_table = Table(meta_data, colWidths=['50%', '50%'])
    meta_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 0.5*cm))

    # Shipping info
    story.append(Paragraph('SHIP TO', label_style))
    story.append(Paragraph(order.full_name, value_style))
    story.append(Paragraph(order.phone, value_style))
    if order.email:
        story.append(Paragraph(order.email, value_style))
    story.append(Paragraph(f'{order.address}, {order.city}, {order.governorate}', value_style))
    story.append(Spacer(1, 0.5*cm))

    # Items table
    story.append(Paragraph('ORDER ITEMS', label_style))
    story.append(Spacer(1, 0.2*cm))
    items = list(order.items.all())
    item_data = [['Product', 'Unit Price', 'Qty', 'Subtotal']]
    for item in items:
        item_data.append([
            item.product_name,
            f'{item.price:,.0f} EGP',
            str(item.quantity),
            f'{item.subtotal:,.0f} EGP',
        ])
    item_table = Table(item_data, colWidths=[9*cm, 3*cm, 2*cm, 3*cm])
    item_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), light_rose),
        ('TEXTCOLOR', (0, 0), (-1, 0), rose),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#FFF8FA')]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#FFE5E5')),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(item_table)
    story.append(Spacer(1, 0.4*cm))

    # Totals
    totals_data = [
        ['Subtotal', f'{order.subtotal:,.0f} EGP'],
        ['Shipping', f'{order.shipping_fee:,.0f} EGP'],
    ]
    if order.discount_amount:
        totals_data.append(['Discount', f'- {order.discount_amount:,.0f} EGP'])
    totals_data.append(['TOTAL', f'{order.total:,.0f} EGP'])
    totals_table = Table(totals_data, colWidths=[13*cm, 4*cm])
    totals_style = [
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('LINEABOVE', (0, -1), (-1, -1), 1, rose),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('TEXTCOLOR', (0, -1), (-1, -1), rose),
        ('FONTSIZE', (0, -1), (-1, -1), 11),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
    ]
    totals_table.setStyle(TableStyle(totals_style))
    story.append(totals_table)
    story.append(Spacer(1, 0.4*cm))

    # Payment info
    story.append(Paragraph('PAYMENT', label_style))
    story.append(Paragraph(f'Method: {order.get_payment_method_display()}', value_style))
    story.append(Paragraph(f'Status: {order.get_payment_status_display()}', value_style))
    story.append(Spacer(1, 1*cm))

    # Footer
    story.append(HRFlowable(width='100%', thickness=0.5, color=colors.HexColor('#FFE5E5')))
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph('Thank you for shopping with SheGlow ✨',
                            ParagraphStyle('footer', parent=styles['Normal'],
                                           fontSize=9, textColor=rose, alignment=TA_CENTER)))

    doc.build(story)
    buf.seek(0)
    response = HttpResponse(buf.read(), content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="invoice-{order.order_number}.pdf"'
    return response


@login_required
@require_POST
def cancel_order(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    if order.status not in ('pending', 'confirmed'):
        messages.error(request, 'This order can no longer be cancelled.')
        return redirect('orders:order_detail', order_number=order_number)
    # Restore stock
    for item in order.items.select_related('product').all():
        if item.product:
            from products.models import Product as Prod
            Prod.objects.filter(pk=item.product.pk).update(stock=F('stock') + item.quantity)
    order.status = 'cancelled'
    order.save(update_fields=['status'])
    messages.success(request, f'Order {order.order_number} has been cancelled.')
    return redirect('orders:order_detail', order_number=order_number)


def track_order(request):
    order = None
    error = None
    if request.method == 'POST':
        order_number = request.POST.get('order_number', '').strip().upper()
        phone = request.POST.get('phone', '').strip()
        if order_number and phone:
            order = Order.objects.filter(order_number=order_number, phone=phone).prefetch_related('items').first()
            if not order:
                error = 'No order found with that order number and phone. Please check and try again.'
        else:
            error = 'Please enter both order number and phone number.'
    return render(request, 'orders/track.html', {'order': order, 'error': error})


@login_required
def order_history(request):
    orders = Order.objects.filter(user=request.user).prefetch_related('items')
    return render(request, 'orders/order_history.html', {'orders': orders})


@login_required
def order_detail(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    items = order.items.select_related('product').all()
    try:
        receipt = order.receipt
    except PaymentReceipt.DoesNotExist:
        receipt = None
    return render(request, 'orders/order_detail.html', {
        'order': order,
        'items': items,
        'receipt': receipt,
    })
