from django.urls import path
from . import views

app_name = 'pages'

urlpatterns = [
    path('privacy-policy/', views.privacy_policy, name='privacy_policy'),
    path('refund-policy/', views.refund_policy, name='refund_policy'),
    path('terms/', views.terms, name='terms'),
    path('shipping/', views.shipping_policy, name='shipping_policy'),
    path('contact/', views.contact, name='contact'),
]
