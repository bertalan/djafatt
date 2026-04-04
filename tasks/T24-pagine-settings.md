# T24 — Pagine Settings (Azienda, Fatturazione, SDI)

**Fase:** 6 — Dashboard, Settings, Deploy  
**Complessità:** Media  
**Dipendenze:** T04, T05  
**Blocca:** Nessuno

---

## Obiettivo

Implementare 3 tab di impostazioni: dati azienda, parametri fatturazione, configurazione SDI. Usa `django-constance` per storage dinamico dei parametri non sensibili.

I segreti non devono essere persi in chiaro nel database configurazioni.

## URL

```python
path("settings/", SettingsView.as_view(), name="settings"),
path("settings/company/", CompanySettingsView.as_view(), name="settings-company"),
path("settings/invoicing/", InvoicingSettingsView.as_view(), name="settings-invoicing"),
path("settings/sdi/", SdiSettingsView.as_view(), name="settings-sdi"),
```

## Tab 1: Azienda

| Campo | Constance key | Tipo |
|---|---|---|
| Ragione sociale | COMPANY_NAME | CharField |
| Partita IVA | COMPANY_VAT_NUMBER | CharField |
| Codice fiscale | COMPANY_TAX_CODE | CharField |
| Indirizzo | COMPANY_ADDRESS | CharField |
| Città | COMPANY_CITY | CharField |
| CAP | COMPANY_POSTAL_CODE | CharField |
| Provincia | COMPANY_PROVINCE | CharField(2) |
| Paese | COMPANY_COUNTRY | CharField |
| PEC | COMPANY_PEC | EmailField |
| Codice SDI | COMPANY_SDI_CODE | CharField(7) |
| Regime fiscale | COMPANY_FISCAL_REGIME | Select (RF01-RF19) |

### Regimi fiscali

```python
FISCAL_REGIME_CHOICES = [
    ("RF01", "Ordinario"),
    ("RF02", "Contribuenti minimi"),
    ("RF04", "Agricoltura"),
    ("RF05", "Pesca"),
    ("RF06", "Commercio all'ingrosso"),
    ("RF07", "Commercio al dettaglio"),
    ("RF08", "Agriturismo"),
    ("RF09", "Alberghi e ristoranti"),
    ("RF10", "Vendita a domicilio"),
    ("RF11", "Rivendita beni usati"),
    ("RF12", "Agenzie di viaggio"),
    ("RF14", "Editoria"),
    ("RF15", "Gestione giochi"),
    ("RF16", "Tabaccai"),
    ("RF17", "Commercio fuochi d'artificio"),
    ("RF18", "Vendita sali e tabacchi"),
    ("RF19", "Forfettario"),
]
```

## Tab 2: Fatturazione

| Campo | Constance key | Tipo |
|---|---|---|
| Sequenza default vendita | DEFAULT_SEQUENCE_SALES | FK → Sequence |
| Sequenza default acquisto | DEFAULT_SEQUENCE_PURCHASE | FK → Sequence |
| Sequenza default autofattura | DEFAULT_SEQUENCE_SELF_INVOICE | FK → Sequence |
| Aliquota IVA default | DEFAULT_VAT_RATE | FK → VatRate |
| Ritenuta abilitata | WITHHOLDING_TAX_ENABLED | Boolean |
| % Ritenuta | WITHHOLDING_TAX_PERCENT | Decimal |
| Bollo automatico | AUTO_STAMP_DUTY | Boolean |
| Soglia bollo | STAMP_DUTY_THRESHOLD | Integer (cent) |
| Metodo pagamento default | DEFAULT_PAYMENT_METHOD | Select |
| Termini pagamento default | DEFAULT_PAYMENT_TERMS | Select |
| Esigibilità IVA | DEFAULT_VAT_PAYABILITY | Select (I/D/S) |
| Split payment | DEFAULT_SPLIT_PAYMENT | Boolean |
| Nome banca | DEFAULT_BANK_NAME | CharField |
| IBAN | DEFAULT_BANK_IBAN | CharField |
| Note default | DEFAULT_NOTES | TextField |
| Reset numerazione annuale | YEARLY_NUMBERING_RESET | Boolean |

## Tab 3: SDI

| Campo | Constance key | Tipo |
|---|---|---|
| Token API OpenAPI | — | Campo write-only, salvato in env o secret store cifrato |
| Modalità sandbox | OPENAPI_SDI_SANDBOX | Boolean |
| URL webhook | — | Calcolato (read-only display) |
| Stato attivazione | — | Check API (read-only) |

### Azioni SDI

- Bottone "Testa connessione" → verifica token API
- Bottone "Ruota token" → sostituisce il secret esistente senza mostrarlo in chiaro
- Bottone "Registra azienda" → chiama `register_business()`
- Bottone "Configura webhook" → chiama `configure_webhooks()`
- Display stato attivazione (attivo / non attivo / errore)

## Validazioni obbligatorie

- P.IVA: 11 cifre
- Codice fiscale: regex valida
- Codice SDI: 7 caratteri alfanumerici
- IBAN: checksum e formato
- Percentuali e soglie monetarie: range validi

## File da creare

- `apps/core/views_settings.py`
- `apps/core/forms_settings.py`
- `apps/common/validators.py`
- `apps/core/secrets.py` — provider per lettura/scrittura secret SDI
- `templates/settings/base.html` — Layout con tab
- `templates/settings/company.html`
- `templates/settings/invoicing.html`
- `templates/settings/sdi.html`
- `djafatt/settings/base.py` — Aggiornare CONSTANCE_CONFIG

## Criteri di accettazione

- [ ] 3 tab funzionanti con salvataggio
- [ ] Dati azienda persistono in Constance
- [ ] Sequenze default selezionabili da dropdown
- [ ] Regime fiscale con select di tutti i codici
- [ ] Token SDI write-only e mai riesposto in chiaro
- [ ] Test connessione SDI funzionante
- [ ] IBAN validato (formato)
- [ ] Audit log creato quando viene aggiornato un secret SDI
