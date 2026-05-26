from django.contrib import admin
from .models import Banner, ContactMessage


@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ['title', 'badge_text', 'is_active', 'order']
    list_editable = ['is_active', 'order']
    list_filter = ['is_active']
    fieldsets = (
        (None, {'fields': ('title', 'subtitle', 'badge_text', 'image')}),
        ('Buttons', {'fields': ('button_text', 'button_url', 'secondary_button_text', 'secondary_button_url')}),
        ('Display', {'fields': ('is_active', 'order')}),
    )


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'subject', 'created_at', 'is_read']
    list_filter = ['is_read', 'created_at']
    search_fields = ['name', 'email', 'subject']
    list_editable = ['is_read']
    readonly_fields = ['name', 'email', 'subject', 'message', 'created_at']
