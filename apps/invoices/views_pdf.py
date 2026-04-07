"""PDF and XML views for invoices."""
import weasyprint
from django.contrib.auth.decorators import login_required, permission_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string

from constance import config

from .models import Invoice


@login_required
@permission_required("invoices.view_invoice", raise_exception=True)
def invoice_preview_pdf(request, pk):
    """Generate a PDF preview of the invoice."""
    invoice = get_object_or_404(
        Invoice.all_types.select_related("contact", "sequence").prefetch_related("payment_dues"),
        pk=pk,
    )
    lines = invoice.lines.select_related("vat_rate").all()

    company = {
        "name": config.COMPANY_NAME,
        "vat_number": config.COMPANY_VAT_NUMBER,
        "tax_code": config.COMPANY_TAX_CODE,
        "address": config.COMPANY_ADDRESS,
        "city": config.COMPANY_CITY,
        "postal_code": config.COMPANY_POSTAL_CODE,
        "province": config.COMPANY_PROVINCE,
        "pec": config.COMPANY_PEC,
        "sdi_code": config.COMPANY_SDI_CODE,
        "phone": getattr(config, "COMPANY_PHONE", ""),
        "email": getattr(config, "COMPANY_EMAIL", ""),
        "bank_name": config.COMPANY_BANK_NAME,
        "bank_iban": config.COMPANY_BANK_IBAN,
    }

    html = render_to_string("invoices/pdf/invoice.html", {
        "invoice": invoice,
        "lines": lines,
        "company": company,
    })

    pdf = weasyprint.HTML(string=html).write_pdf()

    response = HttpResponse(pdf, content_type="application/pdf")
    filename = f"fattura_{invoice.number.replace('/', '-')}.pdf"
    response["Content-Disposition"] = f'inline; filename="{filename}"'
    return response


@login_required
@permission_required("invoices.view_invoice", raise_exception=True)
def invoice_download_xml(request, pk):
    """Generate and download the FatturaPA XML for an invoice."""
    from apps.sdi.services.xml_generator import InvoiceXmlGenerator

    invoice = get_object_or_404(
        Invoice.all_types.select_related("contact", "sequence"), pk=pk,
    )
    xml_content = InvoiceXmlGenerator().generate(invoice)

    tax_code = config.COMPANY_TAX_CODE or config.COMPANY_VAT_NUMBER
    progressive = str(invoice.sequential_number or 0).zfill(5)
    filename = f"IT{tax_code}_{progressive}.xml"

    response = HttpResponse(xml_content, content_type="application/xml; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
