from django.contrib import admin

from .models import Contact


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ["name", "vat_number", "city", "is_customer", "is_supplier"]
    list_filter = ["is_customer", "is_supplier", "country_code"]
    search_fields = ["name", "vat_number", "tax_code"]
