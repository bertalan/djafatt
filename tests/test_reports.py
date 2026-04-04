"""Tests for report views and fiscal year permission restriction."""
from datetime import date

import pytest
from django.contrib.auth.models import Group, User
from django.core.management import call_command
from django.test import Client

from apps.contacts.models import Contact
from apps.invoices.models import Invoice, Sequence


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def groups(db):
    call_command("seed_groups", verbosity=0)
    return {
        "admin": Group.objects.get(name="Amministratore"),
        "contabile": Group.objects.get(name="Contabile"),
        "operatore": Group.objects.get(name="Operatore"),
    }


def _make_client(groups, group_name):
    user = User.objects.create_user(f"{group_name}_r@test.com", password="testpass123")
    user.groups.add(groups[group_name])
    client = Client()
    client.login(username=f"{group_name}_r@test.com", password="testpass123")
    client.user = user
    return client


@pytest.fixture
def report_data(db):
    """Create contacts and invoices for report tests."""
    contact = Contact.objects.create(
        name="Acme SRL", vat_number="IT12345678901", tax_code="12345678901",
        address="Via Roma 1", city="Roma", postal_code="00100",
        province="RM", country_code="IT", is_customer=True,
    )
    seq = Sequence.objects.create(
        name="Vendite", type="sales", pattern="{SEQ}/{ANNO}",
    )
    inv = Invoice.all_types.create(
        type="sales", number="0001/2026", sequential_number=1,
        date=date(2026, 3, 15), contact=contact, sequence=seq,
        document_type="TD01", total_net=10000, total_vat=2200,
        total_gross=12200,
    )
    return {"contact": contact, "sequence": seq, "invoice": inv}


# ---------------------------------------------------------------------------
# Fiscal year permission
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestFiscalYearPermission:
    def test_admin_can_change_fiscal_year(self, groups):
        client = _make_client(groups, "admin")
        resp = client.post("/set-fiscal-year/", {"year": "2025"})
        assert resp.status_code == 302

    def test_contabile_can_change_fiscal_year(self, groups):
        client = _make_client(groups, "contabile")
        resp = client.post("/set-fiscal-year/", {"year": "2025"})
        assert resp.status_code == 302

    def test_operatore_cannot_change_fiscal_year(self, groups):
        client = _make_client(groups, "operatore")
        resp = client.post("/set-fiscal-year/", {"year": "2025"})
        # Should redirect back with error message, not set session
        assert resp.status_code == 302
        # Verify fiscal year was NOT changed
        session = client.session
        assert session.get("fiscal_year") != 2025

    def test_manage_fiscal_year_perm_assigned(self, groups):
        assert groups["admin"].permissions.filter(codename="manage_fiscal_year").exists()
        assert groups["contabile"].permissions.filter(codename="manage_fiscal_year").exists()
        assert not groups["operatore"].permissions.filter(codename="manage_fiscal_year").exists()


# ---------------------------------------------------------------------------
# Report views — access
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestReportAccess:
    def test_report_index_requires_login(self):
        client = Client()
        resp = client.get("/reports/")
        assert resp.status_code == 302
        assert "/login/" in resp.url

    def test_report_index_returns_200(self, auth_client, report_data):
        resp = auth_client.get("/reports/")
        assert resp.status_code == 200

    def test_report_csv_returns_csv(self, auth_client, report_data):
        resp = auth_client.get("/reports/csv/")
        assert resp.status_code == 200
        assert "text/csv" in resp["Content-Type"]

    def test_report_pdf_returns_pdf(self, auth_client, report_data, company_settings):
        resp = auth_client.get("/reports/pdf/")
        assert resp.status_code == 200
        assert resp["Content-Type"] == "application/pdf"


# ---------------------------------------------------------------------------
# Report views — filters
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestReportFilters:
    def test_date_filter_includes_matching(self, auth_client, report_data):
        resp = auth_client.get("/reports/", {"date_from": "2026-01-01", "date_to": "2026-12-31"})
        assert resp.status_code == 200
        assert report_data["invoice"] in resp.context["invoices"]

    def test_date_filter_excludes_outside_range(self, auth_client, report_data):
        resp = auth_client.get("/reports/", {"date_from": "2025-01-01", "date_to": "2025-12-31"})
        assert report_data["invoice"] not in list(resp.context["invoices"])

    def test_type_filter(self, auth_client, report_data):
        resp = auth_client.get("/reports/", {
            "date_from": "2026-01-01", "date_to": "2026-12-31",
            "type": "purchase",
        })
        assert list(resp.context["invoices"]) == []

    def test_contact_filter(self, auth_client, report_data):
        resp = auth_client.get("/reports/", {
            "date_from": "2026-01-01", "date_to": "2026-12-31",
            "contact": str(report_data["contact"].pk),
        })
        assert report_data["invoice"] in resp.context["invoices"]

    def test_summary_aggregation(self, auth_client, report_data):
        resp = auth_client.get("/reports/", {"date_from": "2026-01-01", "date_to": "2026-12-31"})
        summary = resp.context["summary"]
        assert summary["count"] == 1
        assert summary["total_net"] == 10000
        assert summary["total_vat"] == 2200
        assert summary["total_gross"] == 12200


# ---------------------------------------------------------------------------
# CSV content
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestReportCSV:
    def test_csv_has_header_and_data(self, auth_client, report_data):
        resp = auth_client.get("/reports/csv/", {"date_from": "2026-01-01", "date_to": "2026-12-31"})
        content = resp.content.decode("utf-8-sig")
        lines = content.strip().split("\n")
        assert len(lines) == 2  # header + 1 data row
        assert "Numero" in lines[0]
        assert "Acme SRL" in lines[1]

    def test_csv_semicolon_delimiter(self, auth_client, report_data):
        resp = auth_client.get("/reports/csv/", {"date_from": "2026-01-01", "date_to": "2026-12-31"})
        content = resp.content.decode("utf-8-sig")
        header = content.strip().split("\n")[0]
        assert ";" in header

    def test_csv_amounts_formatted(self, auth_client, report_data):
        resp = auth_client.get("/reports/csv/", {"date_from": "2026-01-01", "date_to": "2026-12-31"})
        content = resp.content.decode("utf-8-sig")
        data_row = content.strip().split("\n")[1]
        # 10000 cents = 100,00
        assert "100,00" in data_row

    def test_csv_includes_payment_columns(self, auth_client, report_data):
        resp = auth_client.get("/reports/csv/", {"date_from": "2026-01-01", "date_to": "2026-12-31"})
        content = resp.content.decode("utf-8-sig")
        header = content.strip().split("\n")[0]
        assert "Data Invio SDI" in header
        assert "Data Incasso" in header
        assert "Metodo Incasso" in header


# ---------------------------------------------------------------------------
# Payment status filter
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestPaymentStatusFilter:
    def test_filter_paid(self, auth_client, report_data):
        inv = report_data["invoice"]
        inv.paid_at = date(2026, 3, 20)
        inv.save(update_fields=["paid_at"])
        resp = auth_client.get("/reports/", {
            "date_from": "2026-01-01", "date_to": "2026-12-31",
            "payment_status": "paid",
        })
        assert inv in resp.context["invoices"]

    def test_filter_unpaid(self, auth_client, report_data):
        resp = auth_client.get("/reports/", {
            "date_from": "2026-01-01", "date_to": "2026-12-31",
            "payment_status": "unpaid",
        })
        assert report_data["invoice"] in resp.context["invoices"]

    def test_filter_paid_excludes_unpaid(self, auth_client, report_data):
        resp = auth_client.get("/reports/", {
            "date_from": "2026-01-01", "date_to": "2026-12-31",
            "payment_status": "paid",
        })
        assert list(resp.context["invoices"]) == []

    def test_filter_partial(self, auth_client, report_data):
        """Partially paid invoices returned by partial filter."""
        from apps.invoices.models import PaymentDue

        inv = report_data["invoice"]
        # Pay less than total_gross (12200)
        PaymentDue.objects.create(
            invoice=inv, due_date=date(2026, 3, 20), amount=5000,
            payment_method="MP05", paid=True, paid_at=date(2026, 3, 20),
        )
        inv.sync_paid_status()
        resp = auth_client.get("/reports/", {
            "date_from": "2026-01-01", "date_to": "2026-12-31",
            "payment_status": "partial",
        })
        assert inv in resp.context["invoices"]

    def test_filter_unpaid_excludes_partial(self, auth_client, report_data):
        """Partially paid invoice NOT returned by unpaid filter."""
        from apps.invoices.models import PaymentDue

        inv = report_data["invoice"]
        PaymentDue.objects.create(
            invoice=inv, due_date=date(2026, 3, 20), amount=5000,
            payment_method="MP05", paid=True, paid_at=date(2026, 3, 20),
        )
        inv.sync_paid_status()
        resp = auth_client.get("/reports/", {
            "date_from": "2026-01-01", "date_to": "2026-12-31",
            "payment_status": "unpaid",
        })
        assert inv not in list(resp.context["invoices"])


# ---------------------------------------------------------------------------
# Mark paid / unpaid
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestMarkPaid:
    def test_mark_paid_sets_date(self, auth_client, report_data):
        inv = report_data["invoice"]
        resp = auth_client.post(f"/reports/mark-paid/{inv.pk}/")
        assert resp.status_code == 302
        inv.refresh_from_db()
        assert inv.paid_at == date.today()

    def test_mark_paid_inherits_payment_method(self, auth_client, report_data):
        inv = report_data["invoice"]
        inv.payment_method = "MP05"
        inv.save(update_fields=["payment_method"])
        auth_client.post(f"/reports/mark-paid/{inv.pk}/")
        inv.refresh_from_db()
        assert inv.paid_via == "MP05"

    def test_record_payment_creates_due(self, auth_client, report_data):
        inv = report_data["invoice"]
        auth_client.post(f"/reports/record-payment/{inv.pk}/", {
            "amount": "50.00",
            "payment_date": "2026-03-20",
            "payment_method": "MP08",
        })
        inv.refresh_from_db()
        due = inv.payment_dues.first()
        assert due is not None
        assert due.amount == 5000
        assert due.paid is True
        assert due.payment_method == "MP08"
        # partial payment -> not fully paid yet (12200 gross)
        assert inv.paid_at is None

    def test_record_payment_marks_fully_paid(self, auth_client, report_data):
        inv = report_data["invoice"]
        auth_client.post(f"/reports/record-payment/{inv.pk}/", {
            "amount": "122.00",
            "payment_date": "2026-04-01",
            "payment_method": "MP05",
        })
        inv.refresh_from_db()
        assert inv.paid_at == date(2026, 4, 1)
        assert inv.paid_via == "MP05"

    def test_payment_form_returns_html(self, auth_client, report_data):
        inv = report_data["invoice"]
        resp = auth_client.get(f"/reports/payment-form/{inv.pk}/")
        assert resp.status_code == 200
        assert b"amount" in resp.content

    def test_mark_unpaid_clears_payment(self, auth_client, report_data):
        inv = report_data["invoice"]
        inv.paid_at = date(2026, 3, 20)
        inv.paid_via = "MP05"
        inv.save(update_fields=["paid_at", "paid_via"])
        resp = auth_client.post(f"/reports/mark-unpaid/{inv.pk}/")
        assert resp.status_code == 302
        inv.refresh_from_db()
        assert inv.paid_at is None
        assert inv.paid_via == ""

    def test_mark_paid_requires_post(self, auth_client, report_data):
        inv = report_data["invoice"]
        resp = auth_client.get(f"/reports/mark-paid/{inv.pk}/")
        assert resp.status_code == 405

    def test_mark_paid_requires_login(self, report_data):
        client = Client()
        resp = client.post(f"/reports/mark-paid/{report_data['invoice'].pk}/")
        assert resp.status_code == 302
        assert "/login/" in resp.url
