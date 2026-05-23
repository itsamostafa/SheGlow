from django import template
from products.models import Category

register = template.Library()


@register.inclusion_tag('products/partials/nav_categories.html')
def load_categories():
    return {'categories': Category.objects.filter(is_active=True)}


@register.inclusion_tag('products/partials/nav_categories_mobile.html')
def load_categories_mobile():
    return {'categories': Category.objects.filter(is_active=True)}


@register.filter
def currency(value):
    try:
        return f"{float(value):,.0f} EGP"
    except (ValueError, TypeError):
        return value
