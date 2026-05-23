from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils.translation import gettext_lazy as _


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email is required')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra_fields)


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
    email = models.EmailField(_('email address'), unique=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    objects = UserManager()

    def __str__(self):
        return self.email

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip() or self.email


class Customer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='customer')
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    governorate = models.CharField(max_length=50, choices=EGYPTIAN_GOVERNORATES, blank=True)

    def __str__(self):
        return f"Customer: {self.user.email}"


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
        return f"{self.user.email} → {self.product.name}"
