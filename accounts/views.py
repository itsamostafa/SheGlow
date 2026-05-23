from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .forms import RegisterForm, LoginForm, ProfileForm
from .models import Customer, Wishlist
from products.models import Product


def register_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.first_name = form.cleaned_data['first_name']
            user.last_name = form.cleaned_data['last_name']
            user.save()
            Customer.objects.get_or_create(
                user=user,
                defaults={'phone': form.cleaned_data.get('phone', '')}
            )
            session_key = request.session.session_key
            login(request, user)
            if session_key:
                from orders.views import merge_carts
                merge_carts(user, session_key)
            messages.success(request, f'Welcome to SheGlow, {user.first_name}!')
            return redirect('home')
    else:
        form = RegisterForm()
    return render(request, 'accounts/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    next_url = request.GET.get('next', '')
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            session_key = request.session.session_key
            user = form.get_user()
            login(request, user)
            if session_key:
                from orders.views import merge_carts
                merge_carts(user, session_key)
            messages.success(request, f'Welcome back, {user.first_name or user.email}!')
            return redirect(next_url or 'home')
    else:
        form = LoginForm()
    return render(request, 'accounts/login.html', {'form': form, 'next': next_url})


def logout_view(request):
    if request.method == 'POST':
        logout(request)
        messages.info(request, 'You have been logged out.')
    return redirect('home')


@login_required
def wishlist_view(request):
    items = Wishlist.objects.filter(user=request.user).select_related('product').prefetch_related('product__images')
    return render(request, 'accounts/wishlist.html', {'items': items})


@require_POST
def wishlist_toggle(request, product_id):
    if not request.user.is_authenticated:
        return JsonResponse({'redirect': f'/accounts/login/?next=/wishlist/'})
    product = get_object_or_404(Product, pk=product_id, is_active=True)
    obj, created = Wishlist.objects.get_or_create(user=request.user, product=product)
    if not created:
        obj.delete()
    wishlist_count = Wishlist.objects.filter(user=request.user).count()
    return JsonResponse({'in_wishlist': created, 'wishlist_count': wishlist_count})


@login_required
def profile_view(request):
    customer, _ = Customer.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=customer)
        if form.is_valid():
            request.user.first_name = form.cleaned_data['first_name']
            request.user.last_name = form.cleaned_data['last_name']
            request.user.save()
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('accounts:profile')
    else:
        form = ProfileForm(instance=customer, initial={
            'first_name': request.user.first_name,
            'last_name': request.user.last_name,
        })
    return render(request, 'accounts/profile.html', {'form': form, 'customer': customer})
