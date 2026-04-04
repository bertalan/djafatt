# T04 — Autenticazione + Setup Wizard

**Fase:** 1 — Fondamenta  
**Complessità:** Media  
**Dipendenze:** T01  
**Blocca:** T05, T10

---

## Obiettivo

Login/logout, protezione route con middleware, setup wizard al primo avvio (crea utente + dati azienda).

Questo task deve anche definire i vincoli minimi di validazione per dati fiscali e il bootstrap sicuro del primo utente.

---

## Componenti

### 1. Login / Logout

- **URL:** `/login` (GET/POST), `/logout` (POST)
- **View:** `LoginView` (Django `LoginView` built-in o custom)
- **Template:** `templates/auth/login.html` — form email + password, DaisyUI card
- **Redirect:** dopo login → `/dashboard`
- **Sicurezza:** password validator Django attivi, messaggi di errore generici, rate limiting su tentativi di login

### 2. Auth Middleware

- Tutte le route tranne `/login`, `/setup`, `/api/openapi/webhook` richiedono autenticazione
- Pattern: `LoginRequiredMiddleware` o decoratore `@login_required` sulle view

### 3. Setup Wizard

- **URL:** `/setup` (GET/POST)
- **Condizione:** accessibile SOLO se non esiste nessun utente nel DB
- **Middleware/Guard:** se `User.objects.exists()` → redirect a `/login`
- **Form multi-step o singolo:**
  1. Email + Password (crea User)
  2. Dati azienda (salva in Constance settings):
     - Ragione sociale, P.IVA, Codice Fiscale
     - Indirizzo, Città, CAP, Provincia, Paese
     - PEC, Codice SDI, Regime fiscale
- **Al submit:** crea User, salva settings, redirect a `/dashboard`
- **Transazione:** usare `transaction.atomic()` per evitare stato parziale se il salvataggio fallisce

### 3.b Validatori fiscali obbligatori

- P.IVA italiana: 11 cifre
- Codice fiscale: regex alfanumerica italiana
- Codice SDI: 7 caratteri alfanumerici o `0000000` per estero
- IBAN: validazione formale nel task settings
- Email PEC: validazione email + dominio opzionale non bloccante

### 4. Constance Settings per azienda

```python
CONSTANCE_CONFIG = {
    "COMPANY_NAME": ("", "Ragione sociale"),
    "COMPANY_VAT_NUMBER": ("", "Partita IVA"),
    "COMPANY_TAX_CODE": ("", "Codice fiscale"),
    "COMPANY_ADDRESS": ("", "Indirizzo"),
    "COMPANY_CITY": ("", "Città"),
    "COMPANY_POSTAL_CODE": ("", "CAP"),
    "COMPANY_PROVINCE": ("", "Provincia"),
    "COMPANY_COUNTRY": ("Italia", "Paese"),
    "COMPANY_PEC": ("", "PEC"),
    "COMPANY_SDI_CODE": ("", "Codice SDI"),
    "COMPANY_FISCAL_REGIME": ("RF01", "Regime fiscale"),
}
```

---

## File da creare/modificare

| File | Azione |
|---|---|
| `apps/core/views.py` | SetupView, redirect logic |
| `apps/core/forms.py` | SetupForm (user + company) |
| `apps/core/middleware.py` | SetupRequiredMiddleware |
| `apps/common/validators.py` | P.IVA, CF, codice SDI |
| `apps/core/urls.py` | /login, /logout, /setup |
| `templates/auth/login.html` | Form login DaisyUI |
| `templates/core/setup.html` | Wizard setup |
| `djafatt/settings/base.py` | Auth settings, CONSTANCE_CONFIG |

---

## Criteri di accettazione

- [ ] Primo avvio: `/` redirect a `/setup`
- [ ] `/setup` mostra form se 0 utenti
- [ ] `/setup` redirect a `/login` se utente già esiste
- [ ] Submit setup → crea utente + salva dati azienda → redirect `/dashboard`
- [ ] `/login` funziona con email + password
- [ ] Route protette redirect a `/login` se non autenticato
- [ ] `/logout` disconnette e redirect a `/login`
- [ ] Webhook SDI (`/api/openapi/webhook`) accessibile senza auth
- [ ] Setup eseguito in transazione atomica
- [ ] P.IVA, codice fiscale e codice SDI invalidi vengono rifiutati dal form
