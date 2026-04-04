# T26 — SdiLog modello + audit trail

**Fase:** 6 — Dashboard, Settings, Deploy  
**Complessità:** Bassa  
**Dipendenze:** T03  
**Blocca:** T19, T20

---

## Obiettivo

Modello `SdiLog` per tracciare ogni evento SDI (invio, notifica, errore) e visualizzazione nella pagina edit fattura.

## Modello (`apps/sdi/models.py`)

```python
class SdiLog(models.Model):
    invoice = models.ForeignKey(
        "invoices.Invoice", on_delete=models.CASCADE, related_name="sdi_logs"
    )
    event_type = models.CharField(max_length=50)  # send, notification, error
    status = models.CharField(max_length=30, blank=True, default="")
    message = models.TextField(blank=True, default="")
    raw_payload = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ["-created_at"]
```

## Uso

Creato automaticamente da:
- T19: `send_invoice_to_sdi()` → log invio
- T20: `webhook_handler()` → log notifica
- Errori: log errore con payload

## UI

Nella pagina edit fattura (T10), sezione collapsabile "Log SDI":

```html
{% if invoice.sdi_logs.exists %}
<details class="collapse collapse-arrow bg-base-200">
    <summary class="collapse-title font-medium">
        Log SDI ({{ invoice.sdi_logs.count }})
    </summary>
    <div class="collapse-content">
        <table class="table table-sm">
            <thead>
                <tr><th>Data</th><th>Evento</th><th>Stato</th><th>Messaggio</th></tr>
            </thead>
            <tbody>
                {% for log in invoice.sdi_logs.all %}
                <tr>
                    <td>{{ log.created_at|date:"d/m/Y H:i" }}</td>
                    <td>{{ log.event_type }}</td>
                    <td><span class="badge">{{ log.status }}</span></td>
                    <td>{{ log.message|truncatewords:20 }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</details>
{% endif %}
```

## File da creare

- `apps/sdi/models.py` — SdiLog (aggiungere al file di T22)
- Migrazione `apps/sdi/migrations/0002_sdilog.py`
- Template partial: `templates/invoices/partials/_sdi_logs.html`
- `tests/test_sdi_log.py`

## Criteri di accettazione

- [ ] SdiLog creato ad ogni evento SDI
- [ ] Relazione con Invoice (cascade delete)
- [ ] Log visibile in pagina edit fattura
- [ ] Ordinamento cronologico inverso
- [ ] Raw payload JSON salvato per debug
