from django.contrib import admin
from django.utils.html import format_html
from .models import Category, Product, ProductImage


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 3
    fields = ['image', 'alt_text', 'is_primary', 'order']
    readonly_fields = []


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'is_active', 'order', 'product_count']
    list_editable = ['is_active', 'order']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name']

    def product_count(self, obj):
        return obj.products.filter(is_active=True).count()
    product_count.short_description = 'Active Products'


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'price', 'sale_price', 'stock', 'badge', 'is_active', 'thumbnail']
    list_filter = ['category', 'badge', 'is_active']
    list_editable = ['price', 'sale_price', 'stock', 'badge', 'is_active']
    search_fields = ['name', 'sku', 'description']
    prepopulated_fields = {'slug': ('name',)}
    inlines = [ProductImageInline]
    readonly_fields = ['sku', 'created_at', 'updated_at']
    fieldsets = (
        (None, {'fields': ('name', 'slug', 'category', 'sku')}),
        ('Content', {'fields': ('description',)}),
        ('Pricing & Stock', {'fields': ('price', 'sale_price', 'stock')}),
        ('Display', {'fields': ('badge', 'is_active')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )

    def thumbnail(self, obj):
        img = obj.primary_image
        if img:
            return format_html('<img src="{}" width="50" height="50" style="object-fit:cover;border-radius:4px;" />', img.image.url)
        return '—'
    thumbnail.short_description = 'Image'


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ['product', 'is_primary', 'order']
    list_filter = ['is_primary']
    list_editable = ['is_primary', 'order']
