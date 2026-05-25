from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Customer, Wishlist


class CustomerInline(admin.StackedInline):
    model = Customer
    can_delete = False
    verbose_name_plural = 'Customer Profile'


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    fieldsets = (
        (None, {'fields': ('phone', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('phone', 'first_name', 'last_name', 'email', 'password1', 'password2'),
        }),
    )
    list_display = ['phone', 'email', 'first_name', 'last_name', 'is_staff', 'is_active']
    search_fields = ['phone', 'email', 'first_name', 'last_name']
    ordering = ['phone']
    inlines = [CustomerInline]


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ['user', 'get_phone', 'city', 'governorate']
    search_fields = ['user__phone', 'user__email']

    @admin.display(description='Phone')
    def get_phone(self, obj):
        return obj.user.phone


@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ['user', 'product', 'added_at']
    list_filter = ['added_at']
    search_fields = ['user__phone', 'product__name']
    raw_id_fields = ['product']
