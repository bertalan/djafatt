# T36 — Reverse proxy Nginx + SSL

**Fase:** 6 — Dashboard, Settings, Deploy  
**Complessità:** Media  
**Dipendenze:** T28  
**Blocca:** Nessuno

---

## Obiettivo

Aggiungere Nginx come reverse proxy davanti a Gunicorn per gestire:
- Terminazione SSL/TLS (Let's Encrypt)
- Serving statico efficiente (bypass Gunicorn per `/static/`)
- Rate limiting HTTP a livello infrastrutturale
- Security headers aggiuntivi
- Buffering delle connessioni lente

Senza Nginx, Gunicorn è esposto direttamente su Internet, il che è sconsigliato dalla stessa documentazione Gunicorn.

## Configurazione Nginx (`deploy/nginx/default.conf`)

```nginx
upstream djafatt {
    server web:8000;
}

server {
    listen 80;
    server_name _;

    # Redirect HTTP → HTTPS (in produzione)
    location / {
        return 301 https://$host$request_uri;
    }

    # ACME challenge per Let's Encrypt
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }
}

server {
    listen 443 ssl;
    server_name ${DOMAIN};

    ssl_certificate /etc/letsencrypt/live/${DOMAIN}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/${DOMAIN}/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
    ssl_prefer_server_ciphers off;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # Static files (serviti direttamente da Nginx, no Gunicorn)
    location /static/ {
        alias /app/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Media files
    location /media/ {
        alias /app/media/;
        expires 7d;
    }

    # Rate limiting per webhook SDI
    location /api/openapi/webhook {
        limit_req zone=webhook burst=10 nodelay;
        proxy_pass http://djafatt;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Rate limiting per login
    location /login/ {
        limit_req zone=login burst=5 nodelay;
        proxy_pass http://djafatt;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Applicazione Django
    location / {
        proxy_pass http://djafatt;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;

        # Timeout
        proxy_connect_timeout 30s;
        proxy_read_timeout 120s;
        proxy_send_timeout 120s;

        # Buffering
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 16k;

        # Max upload (per import XML/ZIP)
        client_max_body_size 50M;
    }
}

# Rate limit zones
limit_req_zone $binary_remote_addr zone=webhook:10m rate=30r/m;
limit_req_zone $binary_remote_addr zone=login:10m rate=10r/m;
```

## Docker Compose produzione (`docker-compose.prod.yml` — aggiungere)

```yaml
services:
  nginx:
    image: nginx:1.27-alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./deploy/nginx/default.conf:/etc/nginx/conf.d/default.conf:ro
      - staticfiles:/app/staticfiles:ro
      - mediafiles:/app/media:ro
      - certbot-www:/var/www/certbot:ro
      - certbot-conf:/etc/letsencrypt:ro
    depends_on:
      - web
    restart: unless-stopped

  certbot:
    image: certbot/certbot
    volumes:
      - certbot-www:/var/www/certbot
      - certbot-conf:/etc/letsencrypt
    entrypoint: "/bin/sh -c 'trap exit TERM; while :; do certbot renew; sleep 12h & wait $${!}; done;'"

volumes:
  staticfiles:
  mediafiles:
  certbot-www:
  certbot-conf:
```

## Setup iniziale SSL

Script per primo setup Let's Encrypt:

```bash
#!/bin/bash
# deploy/ssl-init.sh
DOMAIN=${1:?Uso: ssl-init.sh tuodominio.it}

docker compose -f docker-compose.prod.yml run --rm certbot \
    certonly --webroot \
    --webroot-path=/var/www/certbot \
    -d "$DOMAIN" \
    --email admin@"$DOMAIN" \
    --agree-tos --no-eff-email

docker compose -f docker-compose.prod.yml exec nginx nginx -s reload
```

## Settings Django

Aggiornare `prod.py` per fidarsi del proxy:

```python
# Nginx come trusted proxy
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True
USE_X_FORWARDED_PORT = True
```

## Impatto su T28

Il servizio `web` in `docker-compose.prod.yml` NON espone più la porta 8000 all'esterno. Solo Nginx è esposto su 80/443.

```yaml
# T28: rimuovere da web
# ports:
#   - "${APP_PORT:-8000}:8000"  # ← NON PIÙ ESPOSTO
```

## File da creare

- `deploy/nginx/default.conf`
- `deploy/ssl-init.sh`
- Aggiornare `docker-compose.prod.yml`
- Aggiornare `djafatt/settings/prod.py`

## Criteri di accettazione

- [ ] Nginx serve static files senza passare da Gunicorn
- [ ] SSL con Let's Encrypt funzionante
- [ ] Redirect HTTP → HTTPS
- [ ] Rate limiting su webhook (30/min per IP) e login (10/min per IP)
- [ ] Security headers presenti (X-Frame-Options, HSTS, X-Content-Type-Options)
- [ ] Upload fino a 50MB per import XML/ZIP
- [ ] Rinnovo automatico certificati SSL via certbot
- [ ] Gunicorn non esposto direttamente su Internet
