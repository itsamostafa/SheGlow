from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('shop/', views.product_list, name='product_list'),
    path('shop/category/<slug:category_slug>/', views.product_list, name='category_products'),
    path('product/<slug:slug>/', views.product_detail, name='product_detail'),
    path('search/', views.search, name='search'),
    path('api/search/', views.search_api, name='search_api'),
]
