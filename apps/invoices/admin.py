from django.contrib import admin

from .models import Invoice, InvoiceLine, Sequence, VatRate


class InvoiceLineInline(admin.TabularInline):
    model = InvoiceLine
    extra = 0


@admin.register(VatRate)
class VatRateAdmin(admin.ModelAdmin):
    list_display = ["name", "percent", "nature", "is_system"]


@admin.register(Sequence)
class SequenceAdmin(admin.ModelAdmin):
    list_display = ["name", "type", "pattern", "is_system"]


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ["number", "type", "date", "contact", "total_gross", "sdi_status"]
    list_filter = ["type", "sdi_status"]
    search_fields = ["number", "contact__name"]
    inlines = [InvoiceLineInline]
