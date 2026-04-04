"""Seed database with demo data: company, contacts, invoices, payments."""
from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from constance import config

from apps.contacts.models import Contact
from apps.invoices.models import (
    Invoice,
    InvoiceLine,
    InvoiceType,
    PaymentDue,
    PurchaseInvoice,
    SelfInvoice,
    Sequence,
    VatRate,
)

User = get_user_model()


class Command(BaseCommand):
    help = "Seed database with demo data for a forfettario <5y company."

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write("=== Seeding djafatt demo data ===\n")

        self._create_admin()
        self._setup_company()
        self._create_vat_rates()
        self._create_sequences()
        self._create_contacts()
        self._create_sales_invoices()
        self._create_purchase_invoices()
        self._create_self_invoices()
        self._create_payments()

        self.stdout.write(self.style.SUCCESS("\n✓ Seed completato con successo!"))

    # ── Admin user ──────────────────────────────────────────────
    def _create_admin(self):
        if User.objects.filter(username="admin").exists():
            self.stdout.write("  admin user already exists, skipping")
            return
        User.objects.create_superuser("admin", "admin@example.com", "admin")
        self.stdout.write(self.style.SUCCESS("  ✓ Admin user created (admin/admin)"))

    # ── Company settings (Constance) ────────────────────────────
    def _setup_company(self):
        config.COMPANY_NAME = "ROSSI MARIO"
        config.COMPANY_VAT_NUMBER = "01234567890"
        config.COMPANY_TAX_CODE = "RSSMRA80A01H501Z"
        config.COMPANY_ADDRESS = "VIA ROMA 1"
        config.COMPANY_CITY = "TORINO"
        config.COMPANY_POSTAL_CODE = "10100"
        config.COMPANY_PROVINCE = "TO"
        config.COMPANY_COUNTRY_CODE = "IT"
        config.COMPANY_FISCAL_REGIME = "RF19"  # Forfettario
        config.COMPANY_ATECO_CODE = "62.01.00"
        config.COMPANY_ATECO_CODE_2 = "63.11.00"
        config.COMPANY_PEC = "demo@pec.example.com"
        config.COMPANY_SDI_CODE = "0000000"
        config.COMPANY_PHONE = ""
        config.COMPANY_EMAIL = ""
        config.COMPANY_BANK_NAME = "Banca Demo"
        config.COMPANY_BANK_IBAN = "IT60X0542811101000000123456"
        config.DEFAULT_PAYMENT_METHOD = "MP05"  # Bonifico
        config.DEFAULT_PAYMENT_TERMS = "TP02"  # Pagamento completo
        config.SETUP_COMPLETED = True
        self.stdout.write(self.style.SUCCESS(
            "  ✓ Azienda: ROSSI MARIO — P.IVA 01234567890 — RF19 forfettario"
        ))

    # ── Aliquote IVA ────────────────────────────────────────────
    def _create_vat_rates(self):
        self.iva22, _ = VatRate.objects.get_or_create(
            percent=Decimal("22.00"), defaults={"name": "IVA 22%"},
        )
        self.iva10, _ = VatRate.objects.get_or_create(
            percent=Decimal("10.00"), defaults={"name": "IVA 10%"},
        )
        self.iva4, _ = VatRate.objects.get_or_create(
            percent=Decimal("4.00"), defaults={"name": "IVA 4%"},
        )
        # Forfettari non addebitano IVA: N2.2 = non soggetti ad IVA
        self.esente_n2, _ = VatRate.objects.get_or_create(
            percent=Decimal("0.00"), nature="N2.2",
            defaults={"name": "Escluso art. 1 c. 54-89 L.190/2014 (N2.2)"},
        )
        self.stdout.write(self.style.SUCCESS("  ✓ 4 aliquote IVA create"))

    # ── Sequenze numerazione ────────────────────────────────────
    def _create_sequences(self):
        self.seq_sales, _ = Sequence.objects.get_or_create(
            type="sales", defaults={"name": "Fatture vendita", "pattern": "{SEQ}/{ANNO}"},
        )
        self.seq_purchase, _ = Sequence.objects.get_or_create(
            type="purchase", defaults={"name": "Fatture acquisto", "pattern": "{SEQ}/{ANNO}"},
        )
        self.seq_self_invoice, _ = Sequence.objects.get_or_create(
            type="self_invoice", defaults={"name": "Autofatture", "pattern": "{SEQ}/{ANNO}"},
        )
        self.stdout.write(self.style.SUCCESS("  ✓ 3 sequenze create (vendita + acquisto + autofatture)"))

    # ── Contatti ────────────────────────────────────────────────
    def _create_contacts(self):
        self.c_infobyte = Contact.objects.get_or_create(
            vat_number="IT04567890123",
            defaults={
                "name": "InfoByte SRL",
                "tax_code": "04567890123",
                "address": "Corso Buenos Aires 18",
                "city": "Milano",
                "postal_code": "20124",
                "province": "MI",
                "country_code": "IT",
                "sdi_code": "SUBM70N",
                "email": "admin@infobyte.it",
                "is_customer": True,
            },
        )[0]

        self.c_studio = Contact.objects.get_or_create(
            vat_number="IT07654321098",
            defaults={
                "name": "Studio Legale Verdi & Associati",
                "tax_code": "07654321098",
                "address": "Piazza della Repubblica 3",
                "city": "Firenze",
                "postal_code": "50123",
                "province": "FI",
                "country_code": "IT",
                "sdi_code": "5RUO82D",
                "email": "segreteria@studioverdi.it",
                "is_customer": True,
            },
        )[0]

        self.c_amazon = Contact.objects.get_or_create(
            vat_number="IT12400780964",
            defaults={
                "name": "Amazon EU S.à r.l.",
                "address": "Viale Monte Grappa 3/5",
                "city": "Milano",
                "postal_code": "20124",
                "province": "MI",
                "country_code": "IT",
                "sdi_code": "USAL8PV",
                "is_supplier": True,
            },
        )[0]

        self.c_aruba = Contact.objects.get_or_create(
            vat_number="IT01573850516",
            defaults={
                "name": "Aruba S.p.A.",
                "tax_code": "01573850516",
                "address": "Via San Clemente 53",
                "city": "Arezzo",
                "postal_code": "52100",
                "province": "AR",
                "country_code": "IT",
                "sdi_code": "BL6EP11",
                "email": "commerciale@aruba.it",
                "is_supplier": True,
            },
        )[0]

        self.c_brt = Contact.objects.get_or_create(
            vat_number="IT04507990150",
            defaults={
                "name": "BRT S.p.A.",
                "tax_code": "04507990150",
                "address": "Via E. Mattei 42",
                "city": "Bologna",
                "postal_code": "40138",
                "province": "BO",
                "country_code": "IT",
                "sdi_code": "KRRH6B9",
                "is_supplier": True,
            },
        )[0]

        self.c_gmbh = Contact.objects.get_or_create(
            vat_number="DE987654321",
            defaults={
                "name": "Müller IT-Service GmbH",
                "address": "Berliner Str. 25",
                "city": "Berlin",
                "postal_code": "10115",
                "country_code": "DE",
                "email": "kontakt@mueller-it.de",
                "is_customer": True,
            },
        )[0]

        self.stdout.write(self.style.SUCCESS(
            "  ✓ 6 contatti creati (3 clienti, 3 fornitori)"
        ))

    # ── Fatture di vendita ──────────────────────────────────────
    def _create_sales_invoices(self):
        # Forfettario: NO IVA (N2.2), imposta sostitutiva 5% (non in fattura,
        # si calcola in dichiarazione). Marca da bollo se > €77.47.
        rate = self.esente_n2

        # FV 0001/2026 — InfoByte: contratto manutenzione trimestrale
        fv1 = self._create_invoice(
            inv_type=InvoiceType.SALES, seq=self.seq_sales,
            contact=self.c_infobyte, dt=date(2026, 1, 15),
            doc_type="TD01", payment_method="MP05", payment_terms="TP02",
            lines=[
                ("Manutenzione trimestrale server (gen-mar 2026)", 1, 45000, rate),
                ("Monitoraggio remoto h24 — trimestre", 1, 15000, rate),
            ],
            status="sent",  # Inviata, pagamento completo ricevuto
        )

        # FV 0002/2026 — Studio Verdi: installazione + consulenza
        fv2 = self._create_invoice(
            inv_type=InvoiceType.SALES, seq=self.seq_sales,
            contact=self.c_studio, dt=date(2026, 2, 3),
            doc_type="TD01", payment_method="MP05", payment_terms="TP01",
            lines=[
                ("Installazione rete LAN 12 postazioni", 1, 120000, rate),
                ("Configurazione firewall + VPN", 1, 35000, rate),
                ("Formazione personale (4h)", 4, 8000, rate),
            ],
            status="sent",  # Inviata, pagamento parziale (acconto)
        )

        # FV 0003/2026 — Müller GmbH (estero): consulenza remota
        # Per clienti extra-UE: N2.1 (non soggetto art. 7-ter)
        rate_estero, _ = VatRate.objects.get_or_create(
            percent=Decimal("0.00"), nature="N2.1",
            defaults={"name": "Non sogg. art. 7-ter (N2.1)"},
        )
        fv3 = self._create_invoice(
            inv_type=InvoiceType.SALES, seq=self.seq_sales,
            contact=self.c_gmbh, dt=date(2026, 2, 28),
            doc_type="TD01", payment_method="MP05", payment_terms="TP02",
            lines=[
                ("Remote IT consulting — Feb 2026 (20h)", 20, 5000, rate_estero),
            ],
            status="draft",  # Bozza, non ancora inviata
        )

        # FV 0004/2026 — InfoByte: riparazione urgente
        fv4 = self._create_invoice(
            inv_type=InvoiceType.SALES, seq=self.seq_sales,
            contact=self.c_infobyte, dt=date(2026, 3, 10),
            doc_type="TD01", payment_method="MP05", payment_terms="TP02",
            lines=[
                ("Intervento emergenza server — fuori orario", 1, 25000, rate),
                ("Sostituzione alimentatore rack", 1, 8500, rate),
                ("Cavo Cat6 (5m) + connettori", 3, 1200, rate),
            ],
            status="draft",
        )

        self.stdout.write(self.style.SUCCESS(
            "  ✓ 4 fatture vendita create:\n"
            f"    FV 0001/2026 — {fv1.contact.name} — €{fv1.total_gross/100:.2f} [inviata, pagata]\n"
            f"    FV 0002/2026 — {fv2.contact.name} — €{fv2.total_gross/100:.2f} [inviata, acconto]\n"
            f"    FV 0003/2026 — {fv3.contact.name} — €{fv3.total_gross/100:.2f} [bozza]\n"
            f"    FV 0004/2026 — {fv4.contact.name} — €{fv4.total_gross/100:.2f} [bozza]"
        ))

    # ── Fatture di acquisto ─────────────────────────────────────
    def _create_purchase_invoices(self):
        # Le fatture di acquisto hanno IVA normale (il fornitore la addebita)
        iva22 = self.iva22
        iva10 = self.iva10

        # FA 0001/2026 — Amazon: componenti hardware
        fa1 = self._create_invoice(
            inv_type=InvoiceType.PURCHASE, seq=self.seq_purchase,
            contact=self.c_amazon, dt=date(2026, 1, 20),
            doc_type="TD01", payment_method="MP08", payment_terms="TP02",
            lines=[
                ("SSD Samsung 870 EVO 1TB", 3, 8900, iva22),
                ("RAM DDR5 32GB Corsair", 2, 12500, iva22),
                ("Cavo HDMI 2.1 3m", 5, 1200, iva22),
            ],
            status="received",  # Ricevuta, pagata con carta
        )

        # FA 0002/2026 — Aruba: hosting + PEC annuale
        fa2 = self._create_invoice(
            inv_type=InvoiceType.PURCHASE, seq=self.seq_purchase,
            contact=self.c_aruba, dt=date(2026, 1, 31),
            doc_type="TD01", payment_method="MP05", payment_terms="TP01",
            lines=[
                ("Hosting Linux Advanced — anno 2026", 1, 11900, iva22),
                ("PEC standard — rinnovo annuale", 1, 500, iva22),
                ("Dominio .it — rinnovo annuale", 1, 990, iva22),
            ],
            status="received",  # Ricevuta, pagamento parziale (rata 1 di 2)
        )

        # FA 0003/2026 — BRT: spedizioni gennaio
        fa3 = self._create_invoice(
            inv_type=InvoiceType.PURCHASE, seq=self.seq_purchase,
            contact=self.c_brt, dt=date(2026, 2, 5),
            doc_type="TD01", payment_method="MP05", payment_terms="TP02",
            lines=[
                ("Spedizioni nazionali gennaio (14 colli)", 14, 850, iva22),
                ("Supplemento isole", 2, 350, iva22),
            ],
            status="received",
        )

        self.stdout.write(self.style.SUCCESS(
            "  ✓ 3 fatture acquisto create:\n"
            f"    FA 0001/2026 — {fa1.contact.name} — €{fa1.total_gross/100:.2f} [ricevuta, pagata]\n"
            f"    FA 0002/2026 — {fa2.contact.name} — €{fa2.total_gross/100:.2f} [ricevuta, parziale]\n"
            f"    FA 0003/2026 — {fa3.contact.name} — €{fa3.total_gross/100:.2f} [ricevuta, pagata]"
        ))

    # ── Helper per creare fattura + righe + totali ──────────────
    def _create_invoice(self, *, inv_type, seq, contact, dt, doc_type,
                        payment_method, payment_terms, lines, status):
        year = dt.year
        seq_num = seq.get_next_number(year)
        number = seq.pattern.replace("{SEQ}", str(seq_num).zfill(4)).replace("{ANNO}", str(year))

        if inv_type == InvoiceType.PURCHASE:
            model_class = PurchaseInvoice
        elif inv_type == InvoiceType.SELF_INVOICE:
            model_class = SelfInvoice
        else:
            model_class = Invoice

        inv = model_class(
            number=number,
            sequential_number=seq_num,
            date=dt,
            document_type=doc_type,
            status=status,
            contact=contact,
            sequence=seq,
            payment_method=payment_method,
            payment_terms=payment_terms,
            bank_name=config.COMPANY_BANK_NAME,
            bank_iban=config.COMPANY_BANK_IBAN,
        )
        inv.save()

        for desc, qty, price_cents, vat_rate in lines:
            InvoiceLine.objects.create(
                invoice=inv,
                description=desc,
                quantity=Decimal(str(qty)),
                unit_price=price_cents,
                vat_rate=vat_rate,
                total=price_cents * qty,
            )

        inv.calculate_totals()

        # Bollo: forfettari esenti > €77.47
        if inv.total_gross > 7747 and inv_type == InvoiceType.SALES:
            inv.stamp_duty_applied = True
            inv.stamp_duty_amount = 200  # €2.00
            inv.save(update_fields=["stamp_duty_applied", "stamp_duty_amount"])

        return inv

    # ── Autofatture ─────────────────────────────────────────────
    def _create_self_invoices(self):
        # Autofatture per reverse charge su acquisti da soggetti esteri
        # Si usa IVA 22% perché l'autofattura integra l'IVA non addebitata
        iva22 = self.iva22

        # Contatto fornitore estero (aggiungiamo Google Ireland)
        self.c_google, _ = Contact.objects.get_or_create(
            vat_number="IE6388047V",
            defaults={
                "name": "Google Ireland Ltd",
                "address": "Gordon House, Barrow Street",
                "city": "Dublin",
                "postal_code": "D04 E5W5",
                "country_code": "IE",
                "email": "billing@google.com",
                "is_supplier": True,
            },
        )

        # AF 0001/2026 — Google Ads: reverse charge intracomunitario (TD17)
        af1 = self._create_invoice(
            inv_type=InvoiceType.SELF_INVOICE, seq=self.seq_self_invoice,
            contact=self.c_google, dt=date(2026, 1, 31),
            doc_type="TD17", payment_method="MP05", payment_terms="TP02",
            lines=[
                ("Google Ads — campagna gennaio 2026", 1, 32000, iva22),
            ],
            status="sent",
        )

        # AF 0002/2026 — Müller GmbH: servizi ricevuti da UE (TD17)
        af2 = self._create_invoice(
            inv_type=InvoiceType.SELF_INVOICE, seq=self.seq_self_invoice,
            contact=self.c_gmbh, dt=date(2026, 2, 15),
            doc_type="TD17", payment_method="MP05", payment_terms="TP02",
            lines=[
                ("Consulenza tecnica remota — febbraio", 1, 50000, iva22),
                ("Licenza software gestionale (annuale)", 1, 24000, iva22),
            ],
            status="draft",
        )

        self.stdout.write(self.style.SUCCESS(
            "  ✓ 2 autofatture create:\n"
            f"    AF 0001/2026 — {af1.contact.name} — €{af1.total_gross/100:.2f} [inviata]\n"
            f"    AF 0002/2026 — {af2.contact.name} — €{af2.total_gross/100:.2f} [bozza]"
        ))

        self._af1 = af1
        self._af2 = af2

    # ── Pagamenti (PaymentDue) ──────────────────────────────────
    def _create_payments(self):
        # Recupera le fatture create
        fv1 = Invoice.objects.filter(sequence=self.seq_sales, sequential_number=1).first()
        fv2 = Invoice.objects.filter(sequence=self.seq_sales, sequential_number=2).first()
        fa1 = PurchaseInvoice.objects.filter(sequence=self.seq_purchase, sequential_number=1).first()
        fa2 = PurchaseInvoice.objects.filter(sequence=self.seq_purchase, sequential_number=2).first()
        fa3 = PurchaseInvoice.objects.filter(sequence=self.seq_purchase, sequential_number=3).first()
        af1 = self._af1

        payments_created = 0

        if fv1 and not fv1.payment_dues.exists():
            # FV1 — pagata interamente
            PaymentDue.objects.create(
                invoice=fv1, due_date=date(2026, 2, 15),
                amount=fv1.total_gross, payment_method="MP05",
                paid=True, paid_at=date(2026, 2, 12),
            )
            fv1.sync_paid_status()
            payments_created += 1

        if fv2 and not fv2.payment_dues.exists():
            # FV2 — pagamento parziale (acconto 50%)
            half = fv2.total_gross // 2
            PaymentDue.objects.create(
                invoice=fv2, due_date=date(2026, 2, 15),
                amount=half, payment_method="MP05",
                paid=True, paid_at=date(2026, 2, 14),
            )
            PaymentDue.objects.create(
                invoice=fv2, due_date=date(2026, 3, 15),
                amount=fv2.total_gross - half, payment_method="MP05",
                paid=False,
            )
            fv2.sync_paid_status()
            payments_created += 1

        if fa1 and not fa1.payment_dues.exists():
            # FA1 — pagata con carta
            PaymentDue.objects.create(
                invoice=fa1, due_date=date(2026, 1, 20),
                amount=fa1.total_gross, payment_method="MP08",
                paid=True, paid_at=date(2026, 1, 20),
            )
            fa1.sync_paid_status()
            payments_created += 1

        if fa2 and not fa2.payment_dues.exists():
            # FA2 — rata 1 di 2 pagata
            half = fa2.total_gross // 2
            PaymentDue.objects.create(
                invoice=fa2, due_date=date(2026, 1, 31),
                amount=half, payment_method="MP05",
                paid=True, paid_at=date(2026, 1, 30),
            )
            PaymentDue.objects.create(
                invoice=fa2, due_date=date(2026, 7, 31),
                amount=fa2.total_gross - half, payment_method="MP05",
                paid=False,
            )
            fa2.sync_paid_status()
            payments_created += 1

        if fa3 and not fa3.payment_dues.exists():
            # FA3 — pagata
            PaymentDue.objects.create(
                invoice=fa3, due_date=date(2026, 3, 5),
                amount=fa3.total_gross, payment_method="MP05",
                paid=True, paid_at=date(2026, 3, 3),
            )
            fa3.sync_paid_status()
            payments_created += 1

        if af1 and not af1.payment_dues.exists():
            # AF1 — pagata
            PaymentDue.objects.create(
                invoice=af1, due_date=date(2026, 2, 28),
                amount=af1.total_gross, payment_method="MP05",
                paid=True, paid_at=date(2026, 2, 25),
            )
            af1.sync_paid_status()
            payments_created += 1

        self.stdout.write(self.style.SUCCESS(
            f"  ✓ {payments_created} fatture con scadenze di pagamento\n"
            "    FV 0001 → pagata | FV 0002 → parziale\n"
            "    FA 0001 → pagata | FA 0002 → parziale | FA 0003 → pagata\n"
            "    AF 0001 → pagata\n"
            "    FV 0003, FV 0004, AF 0002 → senza scadenze (non pagate)"
        ))
