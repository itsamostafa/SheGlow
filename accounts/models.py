from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils.translation import gettext_lazy as _
import re


def validate_egyptian_phone(phone):
    """Return True if phone looks like an Egyptian mobile number."""
    digits = re.sub(r'\D', '', phone)
    return len(digits) == 11 and digits.startswith('01')


class UserManager(BaseUserManager):
    def create_user(self, phone, password=None, **extra_fields):
        if not phone:
            raise ValueError('Phone number is required')
        extra_fields.setdefault('is_active', True)
        user = self.model(phone=phone, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(phone, password, **extra_fields)


EGYPTIAN_GOVERNORATES = [
    ('Cairo', 'Cairo'),
    ('Giza', 'Giza'),
    ('Alexandria', 'Alexandria'),
    ('Qalyubia', 'Qalyubia'),
    ('Dakahlia', 'Dakahlia'),
    ('Sharqia', 'Sharqia'),
    ('Gharbia', 'Gharbia'),
    ('Monufia', 'Monufia'),
    ('Beheira', 'Beheira'),
    ('Kafr El Sheikh', 'Kafr El Sheikh'),
    ('Damietta', 'Damietta'),
    ('Port Said', 'Port Said'),
    ('Ismailia', 'Ismailia'),
    ('Suez', 'Suez'),
    ('North Sinai', 'North Sinai'),
    ('South Sinai', 'South Sinai'),
    ('Red Sea', 'Red Sea'),
    ('New Valley', 'New Valley'),
    ('Matrouh', 'Matrouh'),
    ('Fayoum', 'Fayoum'),
    ('Beni Suef', 'Beni Suef'),
    ('Minya', 'Minya'),
    ('Assiut', 'Assiut'),
    ('Sohag', 'Sohag'),
    ('Qena', 'Qena'),
    ('Luxor', 'Luxor'),
    ('Aswan', 'Aswan'),
]


class User(AbstractUser):
    username = None
    phone = models.CharField(_('phone number'), max_length=20, unique=True)
    email = models.EmailField(_('email address'), blank=True, null=True)

    USERNAME_FIELD = 'phone'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    objects = UserManager()

    def __str__(self):
        return self.phone

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip() or self.phone

    @property
    def display_email(self):
        return self.email or ''


class Customer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='customer')
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    governorate = models.CharField(max_length=50, choices=EGYPTIAN_GOVERNORATES, blank=True)

    def __str__(self):
        return f"Customer: {self.user.phone}"


class Wishlist(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='wishlist'
    )
    product = models.ForeignKey(
        'products.Product', on_delete=models.CASCADE, related_name='wishlisted_by'
    )
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'product')
        ordering = ['-added_at']

    def __str__(self):
        return f"{self.user.phone} → {self.product.name}"
