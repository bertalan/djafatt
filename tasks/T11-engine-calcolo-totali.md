# T11 — Engine calcolo totali fattura

**Fase:** 3 — Fatture Attive  
**Complessità:** Alta  
**Dipendenze:** T03  
**Blocca:** T10, T12, T13, T14, T17

---

## Obiettivo

Implementare `Invoice.calculate_totals()` con logica completa italiana: netto da righe, IVA per aliquota, ritenuta d'acconto, bollo automatico, split payment.

Per manutenibilita' la logica non deve vivere tutta nel model: il model delega a un servizio puro, facilmente testabile.

## Design consigliato

- `InvoiceCalculationService.calculate(invoice) -> CalculationResult`
- `Invoice.calculate_totals()` come thin wrapper
- Policy isolate per bollo, split payment e ritenuta
- Nessun accesso a `request`, form o template nel motore di calcolo

## Logica originale (da `Invoice.php`)

```python
def calculate_totals(self):
    """Ricalcola tutti i totali dalla somma delle righe."""
    lines = self.lines.select_related("vat_rate").all()
    
    # 1. Totale netto = somma righe.total
    total_net = sum(line.total for line in lines)
    
    # 2. Totale IVA = somma per aliquota (riga.total * aliquota.percent / 100)
    total_vat = 0
    for line in lines:
        if line.vat_rate and line.vat_rate.percent > 0:
            vat = round(line.total * line.vat_rate.percent / 100)
            total_vat += vat
    
    # 3. Ritenuta d'acconto (se abilitata)
    withholding_amount = 0
    if self.withholding_tax_enabled and self.withholding_tax_percent > 0:
        withholding_amount = round(total_net * self.withholding_tax_percent / 100)
    
    # 4. Bollo automatico (€2 se totale esente IVA > €77.47)
    stamp_duty = 0
    if self.type == "sales":  # Solo fatture vendita
        exempt_total = sum(
            line.total for line in lines 
            if line.vat_rate and line.vat_rate.nature  # Ha codice natura = esente
        )
        if exempt_total > 7747:  # €77.47 in centesimi
            stamp_duty = 200  # €2.00 in centesimi
            self.stamp_duty_applied = True
        else:
            stamp_duty = 0
            self.stamp_duty_applied = False
        self.stamp_duty_amount = stamp_duty
    
    # 5. Totale lordo
    total_gross = total_net + total_vat - withholding_amount + stamp_duty
    
    # 6. Salva
    self.total_net = total_net
    self.total_vat = total_vat
    self.total_gross = total_gross
    self.withholding_tax_amount = withholding_amount
    self.save(update_fields=[
        "total_net", "total_vat", "total_gross",
        "withholding_tax_amount",
        "stamp_duty_applied", "stamp_duty_amount",
    ])
```

## Regole business

### Importi in centesimi

Tutti i calcoli in centesimi (intero). Nessun float/Decimal nei calcoli intermedi.

```
InvoiceLine.unit_price = 1000  → €10.00
InvoiceLine.quantity = 2.00
InvoiceLine.total = 2000       → €20.00
```

### Ritenuta d'acconto

- Abilitata da checkbox in fattura
- Percentuale configurabile (default da settings: 20%)
- Calcolata sul totale netto
- Sottratta dal totale lordo (il cliente paga meno, la ritenuta va allo Stato)

### Bollo automatico

- Soglia: €77.47 (7747 centesimi)
- Si applica solo a righe con aliquota IVA che ha `nature` (esente/non imponibile)
- Importo fisso: €2.00 (200 centesimi)
- Solo su fatture vendita (non su acquisto/autofattura)

### Split payment

- Se abilitato: l'IVA non è a carico del cliente
- Il totale lordo cambia: `total_gross = total_net + stamp_duty - withholding`
- L'IVA viene comunque calcolata e mostrata ma non pagata dal cliente

### Riepilogo IVA per XML

Per la generazione XML (T17) serve anche il riepilogo raggruppato per aliquota:

```python
def get_vat_summary(self) -> list[dict]:
    """Raggruppa per aliquota IVA per il riepilogo XML."""
    summary = {}
    for line in self.lines.select_related("vat_rate").all():
        rate_id = line.vat_rate_id
        if rate_id not in summary:
            summary[rate_id] = {
                "vat_rate": line.vat_rate,
                "taxable": 0,
                "vat": 0,
            }
        summary[rate_id]["taxable"] += line.total
        summary[rate_id]["vat"] += round(line.total * line.vat_rate.percent / 100)
    return list(summary.values())
```

## File da creare/modificare

- `apps/invoices/models.py` — Implementare `calculate_totals()` e `get_vat_summary()`
- `apps/invoices/services/calculations.py` — Logica pura di calcolo
- `tests/test_calculations.py` — Test calcolo con vari scenari

## Test necessari

```python
def test_simple_invoice_totals():
    """Una riga, IVA 22%: netto 1000, iva 220, lordo 1220."""

def test_multiple_lines_different_vat():
    """Righe con aliquote diverse."""

def test_withholding_tax():
    """Ritenuta 20% su netto 10000: ritenuta 2000, lordo = 10000 + 2200 - 2000."""

def test_stamp_duty_auto():
    """Riga esente > 77.47€: bollo 200 cent aggiunto."""

def test_stamp_duty_not_applied_below_threshold():
    """Riga esente < 77.47€: nessun bollo."""

def test_stamp_duty_not_on_purchase():
    """Bollo non applicato su fatture acquisto."""

def test_split_payment():
    """IVA calcolata ma non nel totale lordo."""

def test_signal_recalculation():
    """Salvataggio InvoiceLine triggera ricalcolo."""
```

## Criteri di accettazione

- [ ] Totale netto = somma righe
- [ ] IVA calcolata per aliquota
- [ ] Ritenuta d'acconto sottratta da lordo
- [ ] Bollo automatico €2 se esente > €77.47 (solo vendita)
- [ ] Split payment esclude IVA dal lordo
- [ ] Tutti gli importi in centesimi (zero errori arrotondamento)
- [ ] Signal `post_save`/`post_delete` su InvoiceLine triggera ricalcolo
- [ ] `get_vat_summary()` raggruppa correttamente per aliquota
- [ ] Logica di calcolo principale testabile senza ORM completo
