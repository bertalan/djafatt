# T23 — Dashboard con metriche

**Fase:** 6 — Dashboard, Settings, Deploy  
**Complessità:** Media  
**Dipendenze:** T10, T13, T06  
**Blocca:** Nessuno

---

## Obiettivo

Implementare la dashboard principale con metriche di fatturazione, replica del `ReportService.php`.

## Metriche da mostrare

### Card statistiche (riga superiore)

| Metrica | Calcolo | Formato |
|---|---|---|
| Fatturato mese | SUM(total_gross) fatture vendita del mese | € X.XXX,XX |
| Fatturato YTD | SUM(total_gross) fatture vendita dell'anno | € X.XXX,XX |
| Fatture mese | COUNT fatture vendita del mese | N |
| Fatture YTD | COUNT fatture vendita dell'anno | N |
| Clienti attivi | COUNT DISTINCT contact_id con fatture nell'anno | N |
| Valore medio fattura | AVG(total_gross) fatture vendita dell'anno | € X.XXX,XX |
| Variazione mensile | (mese corrente - mese precedente) / mese precedente * 100 | +XX% / -XX% |
| Ritenute YTD | SUM(withholding_tax_amount) dell'anno | € X.XXX,XX |
| IVA raccolta YTD | SUM(total_vat) dell'anno | € X.XXX,XX |

### Top clienti (card laterale)

- Top 5 clienti per fatturato anno
- Nome + totale fatturato

### Fatture recenti (tabella)

- Ultime 5 fatture emesse
- Numero, Data, Cliente, Totale, Stato

## Servizio report (`apps/invoices/services/report.py`)

```python
class ReportService:
    """Calcola metriche dashboard."""
    
    def __init__(self, year: int | None = None):
        self.year = year or datetime.now().year
        self._base_qs = Invoice.objects.filter(date__year=self.year)
    
    def revenue_this_month(self) -> int:
        """Fatturato mese corrente (centesimi)."""
        if self.year < datetime.now().year:
            month = 12  # Anno passato: ultimo mese
        else:
            month = datetime.now().month
        return self._base_qs.filter(
            date__month=month
        ).aggregate(total=Sum("total_gross"))["total"] or 0
    
    def revenue_ytd(self) -> int: ...
    def invoices_this_month(self) -> int: ...
    def invoices_ytd(self) -> int: ...
    def active_clients_count(self) -> int: ...
    def average_invoice_value(self) -> int: ...
    def month_change_percent(self) -> float: ...
    def withholding_tax_ytd(self) -> int: ...
    def vat_collected_ytd(self) -> int: ...
    def top_clients(self, limit=5) -> QuerySet: ...
    def recent_invoices(self, limit=5) -> QuerySet: ...
    
    def get_dashboard_stats(self) -> dict:
        """Tutti gli stats in una chiamata."""
        return {
            "revenue_month": self.revenue_this_month(),
            "revenue_ytd": self.revenue_ytd(),
            "invoices_month": self.invoices_this_month(),
            "invoices_ytd": self.invoices_ytd(),
            "active_clients": self.active_clients_count(),
            "avg_invoice": self.average_invoice_value(),
            "month_change": self.month_change_percent(),
            "withholding_ytd": self.withholding_tax_ytd(),
            "vat_ytd": self.vat_collected_ytd(),
            "top_clients": self.top_clients(),
            "recent_invoices": self.recent_invoices(),
        }
```

## URL

```python
path("dashboard/", DashboardView.as_view(), name="dashboard"),
path("", RedirectView.as_view(url="/dashboard/"), name="home"),
```

## Template

- `templates/core/dashboard.html` — Grid di card statistiche + top clienti + fatture recenti
- Stile: DaisyUI stats cards, table per fatture recenti

## File da creare

- `apps/invoices/services/__init__.py`
- `apps/invoices/services/report.py`
- `apps/core/views.py` — DashboardView (aggiungere)
- `templates/core/dashboard.html`
- `tests/test_report.py`

## Criteri di accettazione

- [ ] Dashboard mostra tutte le metriche
- [ ] Importi formattati in euro (centesimi → €)
- [ ] Anno fiscale da sessione
- [ ] Top 5 clienti corretti
- [ ] Ultime 5 fatture con badge stato
- [ ] Variazione mensile mostra + o - con colore
- [ ] Anno passato: mese di riferimento = dicembre
