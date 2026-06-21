from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser

@admin.action(description='Anonymise selected members (PDPO erasure)')
def anonymize_members(modeladmin, request, queryset):
    for user in queryset:
        user.anonymize()

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    actions = [anonymize_members]
    fieldsets = UserAdmin.fieldsets + (
        ('Membership', {'fields': (
            'membership_uuid', 'is_green_card_holder',
            'membership_activated_at', 'loyalty_points', 'member_qr',
        )}),
        ('HK-PDPO', {'fields': ('consent_given_at', 'data_retention_until')}),
    )
    readonly_fields = ('membership_uuid', 'membership_activated_at', 'member_qr')
