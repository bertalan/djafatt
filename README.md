# djafatt

Sistema leggero per l'emissione e la gestione delle fatture elettroniche italiane, conforme al formato **FatturaPA** dello SDI.

Pensato per professionisti e piccole imprese — in particolare regimi forfettari — che vogliono un'applicazione propria, senza dipendere da servizi SaaS a canone, per gestire l'intero ciclo di fatturazione: emissione, ricezione, invio allo SDI e archiviazione.

## Perché djafatt

| Problema | Soluzione |
|---|---|
| I gestionali cloud costano 10–30 €/mese anche per poche fatture | djafatt gira in locale o su un VPS da 5 €/mese |
| I servizi SaaS chiudono, cambiano prezzo, perdono dati | I tuoi dati restano nel tuo database PostgreSQL |
| Le alternative self-hosted sono sovradimensionate (ERP interi) | djafatt fa solo fatturazione, bene |
| Generare XML FatturaPA a mano è tedioso e soggetto a errori | XML generato automaticamente dalla libreria `a38`, validato |

## Funzionalità

### Fatture di vendita
Creazione, modifica e numerazione automatica delle fatture attive. Supporto per aliquote IVA multiple, nature di esenzione (N1–N7), ritenuta d'acconto, bollo virtuale e split payment. Ogni fattura può avere più righe e più rate di pagamento.

### Fatture di acquisto
Registrazione delle fatture passive ricevute dai fornitori, con import automatico da file XML FatturaPA (singoli o archivi ZIP). Il sistema crea automaticamente contatti e aliquote IVA mancanti.

### Autofatture
Gestione delle autofatture per reverse charge (TD17, TD18, TD19) con collegamento alla fattura del fornitore originale.

### Note di credito
Emissione di note di credito (TD04) collegate alla fattura originale.

### Generazione XML FatturaPA
Generazione automatica del file XML conforme allo standard SDI, inclusi tutti i blocchi obbligatori: DatiTrasmissione, CedentePrestatore, CessionarioCommittente, DatiBeniServizi, DatiPagamento. Naming convention conforme (`IT{P.IVA}_{progressivo}.xml`).

### Invio allo SDI
Integrazione con il servizio [OpenAPI](https://www.openapi.it/) per l'invio delle fatture allo SDI, il monitoraggio dello stato (inviata, consegnata, scartata) e la ricezione dei webhook di notifica.

### Anagrafica contatti
Gestione clienti e fornitori con tutti i campi necessari per la fatturazione italiana: P.IVA, codice fiscale, codice SDI, PEC, coordinate bancarie di default.

### Rate di pagamento
Tracciamento delle scadenze di pagamento per ogni fattura: data scadenza desiderata, importo, metodo di pagamento, stato (pagata/non pagata) e data dell'effettivo incasso. Le rate finiscono nel blocco `DatiPagamento` dell'XML.

### PDF e anteprima
Generazione PDF delle fatture tramite WeasyPrint, per anteprima o stampa.

### Report e export
Report filtrabili per periodo, tipo documento, contatto e stato pagamento. Export in CSV e PDF.

### Sequenze di numerazione
Sequenze configurabili con pattern personalizzabili (`{SEQ}/{ANNO}`) per vendite, acquisti e autofatture.

### Impostazioni aziendali
Configurazione di tutti i dati aziendali (ragione sociale, P.IVA, regime fiscale, coordinate bancarie, codice SDI) tramite interfaccia web, senza toccare file di configurazione.

## Stack tecnico

| Componente | Tecnologia |
|---|---|
| Backend | Django 6.0, Python 3.12 |
| Database | PostgreSQL 17 |
| Frontend | htmx 2.0, TailwindCSS 4, DaisyUI 5 |
| Asset bundling | Vite 7 |
| XML FatturaPA | a38 + defusedxml |
| PDF | WeasyPrint |
| Task queue | Celery + Redis |
| SDI | OpenAPI.it (httpx) |

## Avvio rapido in locale

### Prerequisiti

- [Docker](https://docs.docker.com/get-docker/) e Docker Compose
- Git

### 1. Clona il repository

```bash
git clone https://github.com/bertalan/djafatt.git
cd djafatt
```

### 2. Configura l'ambiente

```bash
cp .env.example .env
```

Modifica `.env` con i tuoi dati. Per lo sviluppo locale i valori di default funzionano già. Per l'invio allo SDI servono:

- `OPENAPI_SDI_TOKEN` — token API di [openapi.it](https://www.openapi.it/)
- `OPENAPI_SDI_WEBHOOK_SECRET` — secret per i webhook di notifica

### 3. Avvia i container

```bash
docker compose up -d
```

Questo avvia quattro servizi:
- **db** — PostgreSQL 17
- **redis** — Redis 7 (cache e broker Celery)
- **web** — Django dev server sulla porta 8000
- **node** — Vite in watch mode per la compilazione degli asset

### 4. Primo setup

```bash
# Installa le dipendenze Node e compila gli asset
docker compose exec node npm install
docker compose exec node npm run build

# Applica le migrazioni
docker compose exec web python manage.py migrate

# Crea i gruppi/permessi base
docker compose exec web python manage.py seed_groups

# Colleziona i file statici
docker compose exec web python manage.py collectstatic --noinput
```

### 5. Crea un utente admin

```bash
docker compose exec web python manage.py createsuperuser
```

### 6. (Opzionale) Carica dati demo

```bash
docker compose exec web python manage.py seed_demo
```

Crea un'azienda di esempio, contatti, aliquote IVA, sequenze e fatture di prova.

### 7. Apri l'applicazione

Vai su [http://localhost:8000](http://localhost:8000) e accedi con le credenziali appena create.

La prima cosa da fare è configurare i dati aziendali in **Impostazioni**.

### Test

```bash
docker compose exec web pytest tests/ -v
```

## Struttura del progetto

```
apps/
  common/        # Eccezioni, helpers, validatori condivisi
  contacts/      # Anagrafica clienti/fornitori
  core/          # Auth, settings aziendali, middleware
  invoices/      # Fatture, righe, rate, aliquote, sequenze
  notifications/ # (in sviluppo)
  products/      # Catalogo prodotti/servizi
  sdi/           # Servizi SDI: generazione XML, import, client OpenAPI
templates/       # Template Django + partials htmx
static/src/      # Sorgenti CSS/JS (Vite)
tests/           # 211+ test (pytest)
```

## Licenza

Questo progetto è distribuito con licenza MIT. Vedi [LICENSE](LICENSE) per i dettagli.
