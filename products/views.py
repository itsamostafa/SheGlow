from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from django.db.models import Q, Case, When, IntegerField
from .models import Product, Category


def home(request):
    categories = Category.objects.filter(is_active=True)
    new_arrivals = Product.objects.filter(is_active=True).prefetch_related('images')[:12]
    featured_qs = Product.objects.filter(is_active=True, badge__in=['bestseller', 'new']).prefetch_related('images')
    featured = list(featured_qs[:8]) or list(new_arrivals[:8])
    return render(request, 'products/home.html', {
        'categories': categories,
        'new_arrivals': new_arrivals,
        'featured': featured,
    })


def product_list(request, category_slug=None):
    products = Product.objects.filter(is_active=True).prefetch_related('images').select_related('category')
    categories = Category.objects.filter(is_active=True)
    current_category = None

    if category_slug:
        current_category = get_object_or_404(Category, slug=category_slug, is_active=True)
        products = products.filter(category=current_category)

    q = request.GET.get('q', '').strip()
    if q:
        products = products.filter(Q(name__icontains=q) | Q(description__icontains=q) | Q(category__name__icontains=q))

    category_filter = request.GET.get('category', '')
    if category_filter and not category_slug:
        products = products.filter(category__slug=category_filter)

    min_price = request.GET.get('min_price', '')
    max_price = request.GET.get('max_price', '')
    if min_price:
        products = products.filter(price__gte=min_price)
    if max_price:
        products = products.filter(price__lte=max_price)

    badge_filter = request.GET.get('badge', '')
    if badge_filter:
        products = products.filter(badge=badge_filter)

    sort = request.GET.get('sort', 'newest')
    if sort == 'price_asc':
        products = products.order_by('price')
    elif sort == 'price_desc':
        products = products.order_by('-price')
    elif sort == 'bestseller':
        products = products.annotate(
            badge_order=Case(When(badge='bestseller', then=0), default=1, output_field=IntegerField())
        ).order_by('badge_order', '-created_at')
    else:
        products = products.order_by('-created_at')

    paginator = Paginator(products, 12)
    page = request.GET.get('page', 1)
    products_page = paginator.get_page(page)

    badge_choices = [('', 'All'), ('new', 'New'), ('sale', 'Sale'), ('bestseller', 'Bestseller'), ('limited', 'Limited')]

    return render(request, 'products/product_list.html', {
        'products': products_page,
        'categories': categories,
        'current_category': current_category,
        'q': q,
        'sort': sort,
        'min_price': min_price,
        'max_price': max_price,
        'badge_filter': badge_filter,
        'category_filter': category_filter,
        'badge_choices': badge_choices,
    })


def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug, is_active=True)
    images = product.images.all()
    related = Product.objects.filter(
        is_active=True, category=product.category
    ).exclude(pk=product.pk).prefetch_related('images')[:4]
    return render(request, 'products/product_detail.html', {
        'product': product,
        'images': images,
        'related': related,
    })


def search(request):
    q = request.GET.get('q', '').strip()
    products = []
    if q:
        products = Product.objects.filter(
            is_active=True
        ).filter(
            Q(name__icontains=q) | Q(description__icontains=q) | Q(category__name__icontains=q)
        ).prefetch_related('images').select_related('category')
    return render(request, 'products/search.html', {'products': products, 'q': q})


def handler404(request, exception):
    return render(request, '404.html', status=404)
