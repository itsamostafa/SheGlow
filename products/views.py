from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Avg, Count, Q, Case, When, IntegerField
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from django.views.decorators.http import require_POST
from .models import Product, Category, Review


def home(request):
    from pages.models import Banner
    categories = Category.objects.filter(is_active=True)
    new_arrivals = Product.objects.filter(is_active=True).prefetch_related('images')[:12]
    featured_qs = Product.objects.filter(is_active=True, badge__in=['bestseller', 'new']).prefetch_related('images')
    featured = list(featured_qs[:8]) or list(new_arrivals[:8])
    hero_banner = Banner.objects.filter(is_active=True).first()
    return render(request, 'products/home.html', {
        'categories': categories,
        'new_arrivals': new_arrivals,
        'featured': featured,
        'hero_banner': hero_banner,
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

    reviews = product.reviews.filter(is_approved=True).select_related('user')
    rating_data = reviews.aggregate(avg=Avg('rating'), count=Count('id'))
    avg_rating = rating_data['avg'] or 0
    review_count = rating_data['count']

    user_review = None
    user_purchased = False
    if request.user.is_authenticated:
        user_review = reviews.filter(user=request.user).first()
        if not user_review:
            user_review = product.reviews.filter(user=request.user, is_approved=False).first()
        from orders.models import OrderItem
        user_purchased = OrderItem.objects.filter(
            order__user=request.user,
            product=product,
            order__status__in=['delivered', 'confirmed'],
        ).exists()

    return render(request, 'products/product_detail.html', {
        'product': product,
        'images': images,
        'related': related,
        'reviews': reviews,
        'avg_rating': avg_rating,
        'review_count': review_count,
        'user_review': user_review,
        'user_purchased': user_purchased,
    })


@login_required
@require_POST
def submit_review(request, slug):
    product = get_object_or_404(Product, slug=slug, is_active=True)
    rating = request.POST.get('rating', '')
    body = request.POST.get('body', '').strip()
    try:
        rating = int(rating)
        assert 1 <= rating <= 5
    except (ValueError, AssertionError):
        messages.error(request, 'Please select a rating.')
        return redirect('product_detail', slug=slug)

    Review.objects.update_or_create(
        product=product, user=request.user,
        defaults={'rating': rating, 'body': body, 'is_approved': False},
    )
    messages.success(request, 'Thanks for your review! It will appear after approval.')
    return redirect('product_detail', slug=slug)


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


def search_api(request):
    q = request.GET.get('q', '').strip()
    if len(q) < 2:
        return JsonResponse({'results': [], 'q': q})
    products = Product.objects.filter(
        is_active=True
    ).filter(
        Q(name__icontains=q) | Q(category__name__icontains=q) | Q(sku__icontains=q)
    ).select_related('category').prefetch_related('images')[:8]

    results = []
    for p in products:
        img = p.primary_image
        results.append({
            'id': p.id,
            'name': p.name,
            'slug': p.slug,
            'price': str(p.effective_price),
            'original_price': str(p.price) if p.is_on_sale else None,
            'image_url': img.image.url if img else None,
            'category': p.category.name if p.category else '',
        })
    return JsonResponse({'results': results, 'q': q})


def handler404(request, exception):
    return render(request, '404.html', status=404)
