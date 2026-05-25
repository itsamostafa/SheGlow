from django.urls import path
from . import views

app_name = 'analytics'

urlpatterns = [
    path('analytics/sales/', views.sales_dashboard, name='sales'),
    path('analytics/inventory/', views.inventory_dashboard, name='inventory'),
]
