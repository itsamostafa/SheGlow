from django.contrib import admin
from django.utils.html import format_html
from .models import Cart, CartItem, PromoCode, Order, OrderItem, PaymentReceipt


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    readonly_fields = ('product', 'quantity', 'subtotal')

    def subtotal(self, obj):
        return f'{obj.subtotal:,.0f} EGP'


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'item_count', 'subtotal_display', 'created_at', 'updated_at')
    list_filter = ('created_at',)
    search_fields = ('user__email', 'session_key')
    inlines = [CartItemInline]
    readonly_fields = ('created_at', 'updated_at')

    def item_count(self, obj):
        return obj.get_item_count()
    item_count.short_description = 'Items'

    def subtotal_display(self, obj):
        return f'{obj.get_subtotal():,.0f} EGP'
    subtotal_display.short_description = 'Subtotal'


@admin.register(PromoCode)
class PromoCodeAdmin(admin.ModelAdmin):
    list_display = ('code', 'discount_type', 'discount_value', 'min_order_amount',
                    'max_uses', 'times_used', 'is_active', 'valid_from', 'valid_until')
    list_filter = ('discount_type', 'is_active')
    search_fields = ('code',)
    list_editable = ('is_active',)
    readonly_fields = ('times_used',)


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('product', 'product_name', 'price', 'quantity', 'subtotal')


class PaymentReceiptInline(admin.StackedInline):
    model = PaymentReceipt
    extra = 0
    readonly_fields = ('receipt_preview', 'uploaded_at')

    def receipt_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height:150px;max-width:300px;">', obj.image.url)
        return '—'
    receipt_preview.short_description = 'Preview'


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'full_name', 'governorate', 'total_display',
                    'payment_method', 'payment_status', 'status', 'created_at')
    list_filter = ('status', 'payment_method', 'payment_status', 'governorate', 'created_at')
    search_fields = ('order_number', 'full_name', 'email', 'phone')
    list_editable = ('status', 'payment_status')
    readonly_fields = ('order_number', 'created_at', 'updated_at', 'subtotal',
                       'shipping_fee', 'discount_amount', 'total')
    inlines = [OrderItemInline, PaymentReceiptInline]
    fieldsets = (
        ('Order Info', {
            'fields': ('order_number', 'user', 'status', 'created_at', 'updated_at')
        }),
        ('Shipping', {
            'fields': ('full_name', 'email', 'phone', 'address', 'city', 'governorate')
        }),
        ('Payment', {
            'fields': ('payment_method', 'payment_status')
        }),
        ('Financials', {
            'fields': ('subtotal', 'shipping_fee', 'promo_code', 'discount_amount', 'total')
        }),
    )

    def total_display(self, obj):
        return f'{obj.total:,.0f} EGP'
    total_display.short_description = 'Total'
    total_display.admin_order_field = 'total'


@admin.register(PaymentReceipt)
class PaymentReceiptAdmin(admin.ModelAdmin):
    list_display = ('order', 'uploaded_at', 'verified', 'verified_by', 'receipt_preview')
    list_filter = ('verified',)
    search_fields = ('order__order_number',)
    list_editable = ('verified',)
    readonly_fields = ('uploaded_at', 'receipt_preview')

    def receipt_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height:150px;max-width:300px;">', obj.image.url)
        return '—'
    receipt_preview.short_description = 'Receipt'
