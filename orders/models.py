from django.db import models
from django.conf import settings
from django.utils import timezone
from products.models import Product


class Cart(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        null=True, blank=True, related_name='cart'
    )
    session_key = models.CharField(max_length=40, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Cart({'user:' + self.user.email if self.user else 'session:' + self.session_key})"

    def get_subtotal(self):
        return sum(item.subtotal for item in self.items.select_related('product').all())

    def get_item_count(self):
        return sum(item.quantity for item in self.items.all())


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ('cart', 'product')

    def __str__(self):
        return f"{self.quantity}× {self.product.name}"

    @property
    def subtotal(self):
        return self.product.effective_price * self.quantity


class PromoCode(models.Model):
    DISCOUNT_TYPE_CHOICES = [
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount'),
    ]

    code = models.CharField(max_length=50, unique=True)
    discount_type = models.CharField(max_length=20, choices=DISCOUNT_TYPE_CHOICES)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    min_order_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    max_uses = models.IntegerField(null=True, blank=True)
    times_used = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField()

    def __str__(self):
        return self.code

    def save(self, *args, **kwargs):
        self.code = self.code.upper().strip()
        super().save(*args, **kwargs)

    def is_valid(self, order_total=None):
        now = timezone.now()
        if not self.is_active:
            return False, 'This promo code is inactive.'
        if now < self.valid_from:
            return False, 'This promo code is not yet valid.'
        if now > self.valid_until:
            return False, 'This promo code has expired.'
        if self.max_uses is not None and self.times_used >= self.max_uses:
            return False, 'This promo code has reached its usage limit.'
        if self.min_order_amount and order_total and order_total < self.min_order_amount:
            return False, f'Minimum order of {self.min_order_amount} EGP required.'
        return True, 'Valid'

    def calculate_discount(self, subtotal):
        if self.discount_type == 'percentage':
            return round(subtotal * self.discount_value / 100, 2)
        return min(self.discount_value, subtotal)


class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]
    PAYMENT_METHOD_CHOICES = [
        ('cod', 'Cash on Delivery'),
        ('paymob', 'Visa / Card (PayMob)'),
        ('instapay', 'InstaPay'),
        ('vodafone_cash', 'Vodafone Cash'),
    ]
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='orders'
    )
    order_number = models.CharField(max_length=30, unique=True, blank=True)

    # Shipping snapshot
    full_name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    address = models.TextField()
    city = models.CharField(max_length=100)
    governorate = models.CharField(max_length=50)

    # Financials
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    shipping_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    promo_code = models.ForeignKey(
        PromoCode, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders'
    )
    total = models.DecimalField(max_digits=10, decimal_places=2)

    # Payment
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='cod')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')

    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.order_number

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = self._generate_order_number()
        super().save(*args, **kwargs)

    def _generate_order_number(self):
        from datetime import date
        today = date.today().strftime('%Y%m%d')
        prefix = f'SG-{today}-'
        last = Order.objects.filter(order_number__startswith=prefix).order_by('-order_number').first()
        if last:
            try:
                seq = int(last.order_number.split('-')[-1]) + 1
            except (ValueError, IndexError):
                seq = 1
        else:
            seq = 1
        return f'{prefix}{seq:04d}'

    @property
    def status_steps(self):
        steps = ['pending', 'confirmed', 'processing', 'shipped', 'delivered']
        idx = steps.index(self.status) if self.status in steps else 0
        return [(s, i <= idx, s.capitalize()) for i, s in enumerate(steps)]


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True)
    product_name = models.CharField(max_length=200)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField()
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.quantity}× {self.product_name}"


class PaymentReceipt(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='receipt')
    image = models.ImageField(upload_to='receipts/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='verified_receipts'
    )
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"Receipt for {self.order.order_number}"
