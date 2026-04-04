# T37 — Reportistica ed Export

| Campo        | Valore                            |
| ------------ | --------------------------------- |
| Fase         | 5 – Reportistica                  |
| Complessità  | Media                             |
| Dipendenze   | T03, T04, T25                     |
| File chiave  | `apps/invoices/views_reports.py`, `apps/invoices/urls_reports.py`, `templates/reports/` |

## Obiettivo

Fornire una pagina di reportistica con filtri avanzati e funzionalità di export
CSV e PDF, pensata per la trasmissione periodica dei dati al commercialista.

## Funzionalità

### Pagina Report (`/reports/`)

- Filtri: intervallo date (dal/al), tipo fattura, contatto (cliente/fornitore)
- Date predefinite: 1 gennaio – 31 dicembre dell'anno fiscale corrente
- Riepilogo: conteggio fatture, totale imponibile, IVA, lordo
- Tabella risultati: numero, data, tipo, tipo documento, contatto, imponibile, IVA, lordo, stato

### Export CSV (`/reports/csv/`)

- Formato: UTF-8 con BOM, delimitatore `;` (compatibile Excel italiano)
- 12 colonne: Numero, Data, Tipo, Tipo Documento, Contatto, P.IVA, C.F.,
  Imponibile, IVA, Totale, Metodo Pagamento, Stato
- Importi formattati con virgola decimale (es. `100,50`)

### Export PDF (`/reports/pdf/`)

- Layout A4 landscape con WeasyPrint
- Header: ragione sociale, P.IVA, periodo selezionato
- Riepilogo aggregato + tabella completa
- Footer: timestamp generazione

## Permessi

Tutte le viste richiedono `@login_required` + `@permission_required("invoices.view_invoice")`.
Accessibile a Amministratore, Contabile e Operatore.

## Criteri di accettazione

- [x] Pagina report con filtri data, tipo, contatto
- [x] Filtri passati come query string tra pagina/CSV/PDF
- [x] Export CSV con BOM + delimitatore `;`
- [x] Export PDF A4 landscape con riepilogo
- [x] Importi in centesimi convertiti correttamente
- [x] Link "Reportistica" in sidebar (solo utenti autorizzati)
- [x] Template filter `describe_invoice_type`
- [ ] Test: report_index ritorna 200
- [ ] Test: report_csv ritorna content-type CSV
- [ ] Test: report_pdf ritorna content-type PDF
- [ ] Test: filtri data/tipo/contatto applicati correttamente
- [ ] Test: accesso negato senza permesso

## File creati / modificati

| File | Azione |
| ---- | ------ |
| `apps/invoices/views_reports.py` | Creato |
| `apps/invoices/urls_reports.py` | Creato |
| `templates/reports/index.html` | Creato |
| `templates/reports/pdf_report.html` | Creato |
| `templates/partials/_sidebar.html` | Modificato (link Reportistica) |
| `apps/core/templatetags/djafatt_tags.py` | Modificato (`describe_invoice_type`) |
| `djafatt/urls.py` | Modificato (include urls_reports) |
