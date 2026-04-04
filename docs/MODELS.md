# Modelli Dati — djafatt

## Contact (apps/contacts)

Anagrafica clienti e fornitori.

| Campo | Tipo | Note |
|-------|------|------|
| id | AutoField | PK |
| name | CharField(255) | Denominazione |
| vat_number | CharField(30) | P.IVA (con prefisso IT/paese) |
| tax_code | CharField(30) | Codice Fiscale |
| sdi_code | CharField(7) | Codice destinatario SDI |
| pec | CharField(255) | PEC per SDI |
| address | CharField(255) | Indirizzo |
| city | CharField(100) | Comune |
| province | CharField(5) | Provincia (solo IT) |
| postal_code | CharField(10) | CAP |
| country | CharField(100) | Nome paese |
| country_code | CharField(2) | Codice ISO paese (default: IT) |
| email | EmailField | Email |
| phone | CharField(30) | Telefono |
| mobile | CharField(30) | Cellulare |
| is_customer | BooleanField | Cliente |
| is_supplier | BooleanField | Fornitore |
| default_payment_method | CharField(10) | Metodo pagamento default (MP code) |
| default_payment_terms | CharField(10) | Termini pagamento default (TP code) |
| default_bank_name | CharField(100) | Banca default |
| default_bank_iban | CharField(34) | IBAN default |
| notes | TextField | Note libere |
| created_at | DateTimeField | Auto |
| updated_at | DateTimeField | Auto |

**Metodi:** `is_italian()`, `is_eu()`, `get_sdi_code_for_xml()`, `get_postal_code_for_xml()`, `get_province_for_xml()`, `get_vat_number_clean()`, `logo_url()`

---

## VatRate (apps/invoices)

Aliquote IVA.

| Campo | Tipo | Note |
|-------|------|------|
| id | AutoField | PK |
| percent | IntegerField | Aliquota % (0 = esente) |
| description | CharField(100) | Descrizione |
| nature_code | CharField(6) | Codice natura (N1-N7) per esenti |
| is_system | BooleanField | Non cancellabile |
| created_at | DateTimeField | Auto |

**Vincolo:** `is_system=True` → `delete()` bloccato (raise `SystemRecordError`)
**Vincolo:** In uso su InvoiceLine → `delete()` bloccato (raise `BusinessRuleViolation`)

---

## Sequence (apps/invoices)

Sequenze numerazione fatture.

| Campo | Tipo | Note |
|-------|------|------|
| id | AutoField | PK |
| name | CharField(100) | Nome sequenza |
| prefix | CharField(20) | Prefisso (es. "FV") |
| year | IntegerField | Anno fiscale |
| next_number | IntegerField | Prossimo numero |
| padding | IntegerField | Zeri padding (default: 4) |
| type | CharField(20) | sales / purchase / self_invoice |
| is_system | BooleanField | Non cancellabile |

**Metodi:** `get_next_number()` (con `SELECT FOR UPDATE`), `get_formatted_number()`

---

## Invoice (apps/invoices)

Fattura — modello base con proxy models.

| Campo | Tipo | Note |
|-------|------|------|
| id | UUID | PK auto |
| type | CharField(20) | sales / purchase / self_invoice |
| number | CharField(20) | Numero formattato |
| sequential_number | IntegerField | Numero progressivo |
| date | DateField | Data fattura |
| document_type | CharField(4) | TD01, TD04, TD17, etc. |
| contact | FK(Contact) | Cliente/fornitore |
| sequence | FK(Sequence) | Sequenza numerazione |
| **Totali (centesimi)** | | |
| total_net | IntegerField | Imponibile totale |
| total_vat | IntegerField | IVA totale |
| total_gross | IntegerField | Totale documento |
| **Ritenuta d'acconto** | | |
| withholding_tax_enabled | BooleanField | |
| withholding_tax_percent | DecimalField(5,2) | |
| withholding_tax_amount | IntegerField | Centesimi |
| **Bollo** | | |
| stamp_duty_applied | BooleanField | |
| stamp_duty_amount | IntegerField | Centesimi (200 = €2.00) |
| **Split payment** | | |
| split_payment | BooleanField | |
| vat_payability | CharField(1) | I/D/S |
| **SDI** | | |
| sdi_status | CharField(20) | draft/sent/delivered/accepted/rejected |
| sdi_uuid | CharField(36) | UUID OpenAPI |
| sdi_sent_at | DateTimeField | |
| sdi_delivered_at | DateTimeField | |
| xml_content | TextField | XML FatturaPA |
| xml_content_hash | CharField(64) | SHA-256 per idempotency |
| **Pagamento** | | |
| payment_method | CharField(10) | Codice MP (da form/contact) |
| payment_terms | CharField(10) | Codice TP |
| bank_name | CharField(100) | Nome banca |
| bank_iban | CharField(34) | IBAN |
| paid_at | DateField(null) | Data incasso effettivo |
| paid_via | CharField(10) | Metodo incasso effettivo (MP code) |
| **Meta** | | |
| notes | TextField | |
| created_at | DateTimeField | |
| updated_at | DateTimeField | |

**Proxy Models:**
- `SalesInvoice` — `type="sales"`, manager filtra automaticamente
- `PurchaseInvoice` — `type="purchase"`
- `SelfInvoice` — `type="self_invoice"`

**Proprietà:**
- `payment_status` → `"paid"` / `"partial"` / `"unpaid"` (da annotazione `_paid_total` o query PaymentDue)

**Metodi:** `calculate_totals()`, `get_vat_summary()`, `is_sdi_editable()`, `sync_paid_status()`

---

## InvoiceLine (apps/invoices)

Riga fattura.

| Campo | Tipo | Note |
|-------|------|------|
| id | AutoField | PK |
| invoice | FK(Invoice) | Fattura padre |
| line_number | IntegerField | Ordine riga |
| description | CharField(200) | Descrizione |
| quantity | DecimalField(10,2) | Quantità |
| unit_price | IntegerField | Prezzo unitario (centesimi) |
| discount_percent | DecimalField(5,2) | Sconto % |
| total | IntegerField | Totale riga (centesimi) |
| vat_rate | FK(VatRate) | Aliquota IVA |
| unit_of_measure | CharField(10) | Unità di misura |
| product | FK(Product, null) | Prodotto opzionale |

**Signal:** `post_save` e `post_delete` → `invoice.calculate_totals()` (se `is_sdi_editable()`)

---

## Product (apps/products)

Anagrafica prodotti/servizi.

| Campo | Tipo | Note |
|-------|------|------|
| id | AutoField | PK |
| name | CharField(255) | Nome |
| description | TextField | Descrizione |
| price | IntegerField | Prezzo (centesimi) |
| unit | CharField(10) | Unità di misura |
| vat_rate | FK(VatRate, null) | Aliquota IVA default |

---

## PaymentDue (apps/invoices)

Scadenze e rate di pagamento per fattura.

| Campo | Tipo | Note |
|-------|------|------|
| id | AutoField | PK |
| invoice | FK(Invoice) | Fattura, `related_name="payment_dues"`, CASCADE |
| due_date | DateField | Data scadenza |
| amount | IntegerField | Importo (centesimi) |
| payment_method | CharField(10) | Codice MP |
| paid | BooleanField | Pagata (db_index) |
| paid_at | DateField(null) | Data pagamento effettivo |

**Proprietà:** `is_overdue` → `not self.paid and self.due_date < today`

**Meta:** `ordering = ["due_date"]`

**Relazione con Invoice:** `invoice.sync_paid_status()` è chiamato dopo salvataggio delle rate. Se tutte le rate coprono `total_gross`, imposta `Invoice.paid_at` e `Invoice.paid_via`.

---

## Diagramma Relazioni (aggiornato)

```
Contact ──────────< Invoice >────────── Sequence
                      │  │
                      │  └──< PaymentDue
                      │
                      │ lines
                      ▼
                  InvoiceLine >──────── VatRate
                      │
                      │ (opzionale)
                      ▼
                   Product >──────────── VatRate
```
