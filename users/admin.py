from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

User = get_user_model()


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('names', 'phone_number', 'user_class', 'shop', 'is_active', 'date_joined')
    list_filter = ('user_class', 'is_active', 'shop')
    fieldsets = (
        (None, {
            'fields': ('phone_number', 'password'),
        }),
        ('Personal info', {
            'fields': ('names', 'shop', 'user_class', 'is_active'),
        }),
        ('Permissions', {
            'fields': ('is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Important dates', {
            'fields': ('last_login',),
        }),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('names', 'phone_number', 'password1', 'password2', 'user_class', 'shop'),
        }),
    )
    search_fields = ('names', 'phone_number')
    ordering = ('phone_number',)
    readonly_fields = ('date_joined', 'last_login')
