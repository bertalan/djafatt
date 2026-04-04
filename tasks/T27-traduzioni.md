# T27 — Traduzioni it/en

**Fase:** 6 — Dashboard, Settings, Deploy  
**Complessità:** Bassa  
**Dipendenze:** T05  
**Blocca:** Nessuno

---

## Obiettivo

Creare file di traduzione Django (`.po`) per italiano e inglese. ~200 stringhe.

## Struttura file

```
locale/
├── it/
│   └── LC_MESSAGES/
│       ├── django.po
│       └── django.mo
└── en/
    └── LC_MESSAGES/
        ├── django.po
        └── django.mo
```

## Categorie stringhe

### Navigazione (~15)

```
Dashboard, Fatturazione, Fatture vendita, Fatture acquisto, Autofatture,
Configurazione, Contatti, Prodotti, Sequenze, Aliquote IVA, 
Importazioni, Impostazioni, Fatture fornitori, Logout
```

### Azioni comuni (~15)

```
Cerca, Crea, Modifica, Elimina, Salva, Annulla, Filtri, Reset, Fatto,
Conferma eliminazione, Torna alla lista, Chiudi, Importa, Esporta, Invia
```

### Fatture (~40)

```
Numero, Data, Cliente, Fornitore, Totale, Stato, Sequenza, Righe,
Descrizione, Quantità, Prezzo unitario, Unità misura, Aliquota IVA,
Imponibile, IVA, Lordo, Ritenuta d'acconto, Bollo, Metodo pagamento,
Termini pagamento, Banca, IBAN, Note, Esigibilità IVA, Split payment,
Bozza, Generata, Inviata, Ricevuta, Anno fiscale, Solo lettura,
Fattura creata, Fattura aggiornata, Fattura eliminata,
Impossibile eliminare: inviata al SDI, Tipo documento,
Numero fattura originale, Data fattura originale
```

### Contatti (~20)

```
Nome, P.IVA, Codice fiscale, Indirizzo, Città, CAP, Provincia,
Paese, Codice paese, Codice SDI, PEC, Email, Telefono, Cellulare,
Note, Cliente, Fornitore, Contatto creato, Contatto aggiornato,
Impossibile eliminare: ha fatture collegate
```

### SDI (~20)

```
Stato SDI, UUID, ID, Messaggio, Inviato il, In attesa, Inviato,
Consegnato, Rifiutato, Accettato, Errore, Scaduto, Log SDI,
Testa connessione, Registra azienda, Configura webhook,
Connessione riuscita, Errore connessione
```

### Import (~15)

```
Importa XML vendita, Importa XML acquisto, Importa XML autofattura,
Importa contatti Fattura24, Seleziona file, Formati accettati,
Import completato, Fatture importate, Contatti creati, Errori,
Aggiorna esistenti, Nessuna sequenza disponibile
```

### Settings (~20)

```
Impostazioni, Azienda, Fatturazione, SDI, Ragione sociale,
Partita IVA, Codice fiscale, Regime fiscale, Ordinario, Forfettario,
Sequenza default, Aliquota default, Bollo automatico, Soglia bollo,
Token API, Modalità sandbox, URL webhook, Salvato con successo
```

### Dashboard (~15)

```
Fatturato mese, Fatturato anno, Fatture emesse, Clienti attivi,
Valore medio fattura, Variazione mensile, Ritenute anno, IVA anno,
Top clienti, Fatture recenti, Nessuna fattura
```

## Workflow

```bash
# Estrai stringhe
python manage.py makemessages -l it -l en

# Compila traduzioni
python manage.py compilemessages
```

## Uso nei template

```html
{% load i18n %}
<h1>{% trans "Fatture vendita" %}</h1>
<th>{% trans "Numero" %}</th>
```

## Uso nelle view

```python
from django.utils.translation import gettext_lazy as _

class InvoiceForm(forms.ModelForm):
    class Meta:
        labels = {
            "number": _("Numero"),
            "date": _("Data"),
        }
```

## File da creare

- `locale/it/LC_MESSAGES/django.po`
- `locale/en/LC_MESSAGES/django.po`
- Compilazione `.mo` via `compilemessages`

## Criteri di accettazione

- [ ] Tutte le stringhe UI traducibili con `{% trans %}`
- [ ] File `.po` italiano completo (~200 stringhe)
- [ ] File `.po` inglese completo
- [ ] `compilemessages` genera `.mo` senza errori
- [ ] Switch lingua funzionante (it ↔ en)
