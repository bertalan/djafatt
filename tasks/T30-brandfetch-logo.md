# T30 — Brandfetch logo integration

**Fase:** 6 — Dashboard, Settings, Deploy  
**Complessità:** Bassa  
**Dipendenze:** T02, T06  
**Blocca:** Nessuno

---

## Obiettivo

Integrare il servizio Brandfetch per mostrare il logo aziendale dei contatti, estratto dal dominio email.

## Logica (replica da `BrandfetchService.php`)

```python
# apps/contacts/services.py

class BrandfetchService:
    CDN_BASE = "https://cdn.brandfetch.io"
    
    def __init__(self):
        from constance import config
        self.client_id = config.BRANDFETCH_CLIENT_ID
    
    def get_logo_url(self, email: str, size: int = 128) -> str | None:
        """Genera URL logo CDN dal dominio email."""
        if not email or not self.client_id:
            return None
        
        domain = email.split("@")[-1] if "@" in email else None
        if not domain:
            return None
        
        # Escludi provider email generici
        generic = {"gmail.com", "yahoo.com", "hotmail.com", "outlook.com", 
                   "libero.it", "virgilio.it", "alice.it", "tin.it",
                   "pec.it", "legalmail.it", "arubapec.it"}
        if domain.lower() in generic:
            return None
        
        return f"{self.CDN_BASE}/{domain}/w/{size}/h/{size}?c={self.client_id}"
```

## Uso nel modello Contact

```python
class Contact(models.Model):
    # ... campi ...
    
    @property
    def logo_url(self) -> str | None:
        from .services import BrandfetchService
        return BrandfetchService().get_logo_url(self.email)
```

## Uso nei template

```html
{% if contact.logo_url %}
    <img src="{{ contact.logo_url }}" alt="{{ contact.name }}" 
         class="w-8 h-8 rounded-full" loading="lazy" />
{% else %}
    <div class="avatar placeholder">
        <div class="bg-neutral text-neutral-content rounded-full w-8">
            <span>{{ contact.name|first }}</span>
        </div>
    </div>
{% endif %}
```

## Constance setting

```python
"BRANDFETCH_CLIENT_ID": ("", "Brandfetch Client ID per loghi aziendali"),
```

## File da creare/modificare

- `apps/contacts/services.py` — BrandfetchService
- `apps/contacts/models.py` — Property `logo_url`
- Template contatti: avatar con logo o iniziale
- `tests/test_brandfetch.py`

## Criteri di accettazione

- [ ] Logo mostrato in lista contatti per email aziendali
- [ ] Nessun logo per email generiche (gmail, etc.)
- [ ] Nessun logo se Brandfetch non configurato
- [ ] Fallback: cerchio con iniziale nome
- [ ] URL CDN generato correttamente
- [ ] Lazy loading immagini
