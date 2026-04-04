# T01e — CI + quality gates

**Fase:** Trasversale — Qualità  
**Complessità:** Media  
**Dipendenze:** T01  
**Blocca:** T28, T29

---

## Obiettivo

Costruire una pipeline CI minima ma rigorosa per evitare regressioni architetturali, di sicurezza e di qualità del codice prima del deploy.

## Scope

- GitHub Actions o equivalente CI
- Matrix minima: Python 3.12 e 3.13
- Servizi CI: PostgreSQL per test Django
- Step obbligatori: `ruff`, `mypy`, `pytest`, `pytest --cov`, build frontend Vite, `python manage.py check --deploy`
- Fail fast se coverage sotto soglia o type check fallisce

## Workflow suggerito

```yaml
name: ci

on:
  push:
    branches: [main]
  pull_request:

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:17
        env:
          POSTGRES_DB: djafatt_test
          POSTGRES_USER: djafatt
          POSTGRES_PASSWORD: djafatt
        ports: ["5432:5432"]
        options: >-
          --health-cmd="pg_isready -U djafatt"
          --health-interval=10s
          --health-timeout=5s
          --health-retries=5

    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - uses: actions/setup-node@v4
        with:
          node-version: '22'
      - run: pip install -e .[dev]
      - run: npm ci
      - run: npm run build
      - run: ruff check .
      - run: mypy apps djafatt
      - run: python manage.py check --deploy --settings=djafatt.settings.test
      - run: pytest --cov=apps --cov-report=term-missing --cov-fail-under=85
```

## File da creare

- `.github/workflows/ci.yml`
- `mypy.ini` o sezione in `pyproject.toml`
- `ruff.toml` o sezione in `pyproject.toml`
- Badge stato CI nel README principale progetto

## Criteri di accettazione

- [ ] Ogni PR esegue lint, type check, test e coverage
- [ ] Coverage fail-under impostato ad almeno 85%
- [ ] `manage.py check --deploy` incluso nella pipeline
- [ ] Build frontend validata in CI
- [ ] Log CI sufficienti per capire rapidamente il failure point