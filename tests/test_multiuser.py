"""Tests for multi-user permissions, settings page, and user management."""
import pytest
from django.contrib.auth.models import Group, User
from django.core.management import call_command
from django.test import Client


@pytest.fixture
def groups(db):
    """Seed the 3 groups via management command."""
    call_command("seed_groups", verbosity=0)
    return {
        "admin": Group.objects.get(name="Amministratore"),
        "contabile": Group.objects.get(name="Contabile"),
        "operatore": Group.objects.get(name="Operatore"),
    }


def _make_client(groups, group_name):
    """Create an authenticated client with the given group."""
    user = User.objects.create_user(
        f"{group_name}@test.com", password="testpass123"
    )
    user.groups.add(groups[group_name])
    client = Client()
    client.login(username=f"{group_name}@test.com", password="testpass123")
    client.user = user
    return client


# ---------------------------------------------------------------------------
# seed_groups command
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestSeedGroups:
    def test_creates_three_groups(self, groups):
        assert Group.objects.count() == 3

    def test_idempotent(self, groups):
        call_command("seed_groups", verbosity=0)
        assert Group.objects.count() == 3

    def test_admin_has_manage_settings(self, groups):
        assert groups["admin"].permissions.filter(codename="manage_settings").exists()

    def test_admin_has_manage_users(self, groups):
        assert groups["admin"].permissions.filter(codename="manage_users").exists()

    def test_contabile_no_manage_settings(self, groups):
        assert not groups["contabile"].permissions.filter(codename="manage_settings").exists()

    def test_operatore_cannot_delete_invoice(self, groups):
        assert not groups["operatore"].permissions.filter(codename="delete_invoice").exists()


# ---------------------------------------------------------------------------
# Permission enforcement (views)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestPermissionEnforcement:
    def test_admin_can_access_contacts(self, groups):
        client = _make_client(groups, "admin")
        response = client.get("/contacts/")
        assert response.status_code == 200

    def test_operatore_can_view_contacts(self, groups):
        client = _make_client(groups, "operatore")
        response = client.get("/contacts/")
        assert response.status_code == 200

    def test_operatore_cannot_create_contact(self, groups):
        client = _make_client(groups, "operatore")
        response = client.get("/contacts/create/")
        assert response.status_code == 302  # redirect to dashboard

    def test_operatore_cannot_delete_contact(self, groups):
        from apps.contacts.models import Contact

        c = Contact.objects.create(name="Test", vat_number="IT12345678901")
        client = _make_client(groups, "operatore")
        response = client.post(f"/contacts/{c.pk}/delete/")
        assert response.status_code == 302

    def test_contabile_can_create_contact(self, groups):
        client = _make_client(groups, "contabile")
        response = client.get("/contacts/create/")
        assert response.status_code == 200

    def test_operatore_can_view_products(self, groups):
        client = _make_client(groups, "operatore")
        response = client.get("/products/")
        assert response.status_code == 200

    def test_operatore_cannot_create_product(self, groups):
        client = _make_client(groups, "operatore")
        response = client.get("/products/create/")
        assert response.status_code == 302

    def test_contabile_view_only_vat_rates(self, groups):
        client = _make_client(groups, "contabile")
        response = client.get("/vat-rates/")
        assert response.status_code == 200
        response = client.get("/vat-rates/create/")
        assert response.status_code == 302  # no add_vatrate

    def test_unauthenticated_redirects_to_login(self):
        client = Client()
        response = client.get("/contacts/")
        assert response.status_code == 302
        assert "/login/" in response.url


# ---------------------------------------------------------------------------
# Settings page
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestSettingsPage:
    def test_admin_can_access_settings(self, groups):
        client = _make_client(groups, "admin")
        response = client.get("/settings/")
        assert response.status_code == 200

    def test_contabile_cannot_access_settings(self, groups):
        client = _make_client(groups, "contabile")
        response = client.get("/settings/")
        assert response.status_code == 302  # redirect to dashboard

    def test_save_company_data(self, groups):
        from constance import config

        client = _make_client(groups, "admin")
        response = client.post("/settings/", {
            "_tab": "company",
            "company-company_name": "New SRL",
            "company-vat_number": "01234567890",
            "company-tax_code": "01234567890",
            "company-address": "Via Nuova 1",
            "company-city": "Milano",
            "company-postal_code": "20100",
            "company-province": "MI",
            "company-country_code": "IT",
            "company-fiscal_regime": "RF01",
            "company-bank_name": "Banca Test",
            "company-bank_iban": "IT60X0542811101000000123456",
        })
        assert response.status_code == 302
        assert config.COMPANY_NAME == "New SRL"
        assert config.COMPANY_CITY == "Milano"
        assert config.COMPANY_BANK_NAME == "Banca Test"
        assert config.COMPANY_BANK_IBAN == "IT60X0542811101000000123456"

    def test_save_invoicing_settings(self, groups):
        from constance import config

        client = _make_client(groups, "admin")
        response = client.post("/settings/", {
            "_tab": "invoicing",
            "invoicing-default_payment_method": "MP05",
            "invoicing-default_payment_terms": "TP02",
        })
        assert response.status_code == 302
        assert config.DEFAULT_PAYMENT_METHOD == "MP05"


# ---------------------------------------------------------------------------
# User management
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestUserManagement:
    def test_admin_can_list_users(self, groups):
        client = _make_client(groups, "admin")
        response = client.get("/users/")
        assert response.status_code == 200

    def test_contabile_cannot_list_users(self, groups):
        client = _make_client(groups, "contabile")
        response = client.get("/users/")
        assert response.status_code == 302

    def test_create_user(self, groups):
        client = _make_client(groups, "admin")
        response = client.post("/users/create/", {
            "email": "newuser@test.com",
            "first_name": "Nuovo",
            "last_name": "Utente",
            "group": groups["contabile"].pk,
            "password": "securepass123",
            "password_confirm": "securepass123",
        })
        assert response.status_code == 302
        new_user = User.objects.get(username="newuser@test.com")
        assert new_user.groups.first().name == "Contabile"

    def test_edit_user(self, groups):
        target = User.objects.create_user("target@test.com", password="testpass123")
        target.groups.add(groups["operatore"])
        client = _make_client(groups, "admin")
        response = client.post(f"/users/{target.pk}/edit/", {
            "first_name": "Mario",
            "last_name": "Rossi",
            "group": groups["contabile"].pk,
            "is_active": "on",
        })
        assert response.status_code == 302
        target.refresh_from_db()
        assert target.first_name == "Mario"
        assert target.groups.first().name == "Contabile"

    def test_create_duplicate_email_rejected(self, groups):
        User.objects.create_user("dup@test.com", password="testpass123")
        client = _make_client(groups, "admin")
        response = client.post("/users/create/", {
            "email": "dup@test.com",
            "group": groups["admin"].pk,
            "password": "securepass123",
            "password_confirm": "securepass123",
        })
        assert response.status_code == 200  # re-renders form
        assert "Esiste già" in response.content.decode()

    def test_password_mismatch_rejected(self, groups):
        client = _make_client(groups, "admin")
        response = client.post("/users/create/", {
            "email": "test2@test.com",
            "group": groups["admin"].pk,
            "password": "securepass123",
            "password_confirm": "different123",
        })
        assert response.status_code == 200  # re-renders form
