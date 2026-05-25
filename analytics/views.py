import json
from django.contrib.admin.views.decorators import staff_member_required
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Sum, Count, Avg
from django.db.models.functions import TruncDay
from django.shortcuts import render
from django.utils import timezone
from datetime import timedelta

from orders.models import Order, OrderItem
from products.models import Product


# ─── Sales Dashboard ────────────────────────────────────────────────────────

@staff_member_required
def sales_dashboard(request):
    period = request.GET.get('period', '30')
    try:
        days = int(period)
    except ValueError:
        days = 30
    since = timezone.now() - timedelta(days=days)

    orders = Order.objects.filter(created_at__gte=since).exclude(status='cancelled')

    total_revenue = orders.aggregate(t=Sum('total'))['t'] or 0
    total_orders = orders.count()
    avg_order_value = orders.aggregate(a=Avg('total'))['a'] or 0
    total_items = OrderItem.objects.filter(order__in=orders).aggregate(t=Sum('quantity'))['t'] or 0

    daily = list(
        orders
        .annotate(day=TruncDay('created_at'))
        .values('day')
        .annotate(revenue=Sum('total'), count=Count('id'))
        .order_by('day')
    )

    by_payment = list(
        orders
        .values('payment_method')
        .annotate(revenue=Sum('total'), count=Count('id'))
        .order_by('-revenue')
    )

    by_governorate = list(
        orders
        .values('governorate')
        .annotate(revenue=Sum('total'), count=Count('id'))
        .order_by('-revenue')[:10]
    )

    top_products = list(
        OrderItem.objects
        .filter(order__in=orders)
        .values('product_name')
        .annotate(revenue=Sum('subtotal'), units=Sum('quantity'))
        .order_by('-revenue')[:10]
    )

    payment_labels = {
        'cod': 'Cash on Delivery',
        'paymob': 'Visa / Card',
        'instapay': 'InstaPay',
        'vodafone_cash': 'Vodafone Cash',
    }

    return render(request, 'analytics/sales.html', {
        'period': days,
        'since': since,
        'total_revenue': total_revenue,
        'total_orders': total_orders,
        'avg_order_value': avg_order_value,
        'total_items': total_items,
        'daily_json': json.dumps(daily, cls=DjangoJSONEncoder),
        'by_payment_json': json.dumps(by_payment, cls=DjangoJSONEncoder),
        'by_payment': by_payment,
        'by_governorate': by_governorate,
        'top_products': top_products,
        'payment_labels': payment_labels,
        'payment_labels_json': json.dumps(payment_labels),
    })


# ─── Inventory Dashboard ─────────────────────────────────────────────────────

@staff_member_required
def inventory_dashboard(request):
    low_stock_threshold = 10

    all_products = list(Product.objects.select_related('category').filter(is_active=True))
    out_of_stock = [p for p in all_products if p.stock == 0]
    low_stock = [p for p in all_products if 0 < p.stock <= low_stock_threshold]
    in_stock_count = sum(1 for p in all_products if p.stock > low_stock_threshold)

    total_stock_value = sum(p.effective_price * p.stock for p in all_products)

    since = timezone.now() - timedelta(days=60)
    best_sellers = list(
        OrderItem.objects
        .filter(order__created_at__gte=since)
        .exclude(order__status='cancelled')
        .values('product_id', 'product_name')
        .annotate(units_sold=Sum('quantity'))
        .order_by('-units_sold')[:10]
    )
    product_map = {p.id: p.stock for p in all_products}
    for b in best_sellers:
        b['stock'] = product_map.get(b['product_id'], 0)

    return render(request, 'analytics/inventory.html', {
        'out_of_stock': out_of_stock,
        'low_stock': low_stock,
        'in_stock_count': in_stock_count,
        'total_products': len(all_products),
        'total_stock_value': total_stock_value,
        'best_sellers': best_sellers,
        'low_stock_threshold': low_stock_threshold,
    })
