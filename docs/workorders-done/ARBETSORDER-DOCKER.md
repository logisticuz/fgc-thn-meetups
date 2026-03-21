# Arbetsorder: Docker-setup for meetup-systemet

**Datum:** 2026-03-21
**Syfte:** Skapa Dockerfile + docker-compose.dev.yml sa meetup-appen kor i Docker mot delad Postgres.

---

## Kontext

Meetup-systemet (`fgc-thn-meetups`) ar migrerat till psycopg3/Postgres.
Det ska anslutas till samma Docker-natverk som turneringssystemet (`fgt-dev_fgt-net`)
for att na Postgres och n8n internt.

### Referens: fgt-member-card/docker-compose.dev.yml
```yaml
services:
  backend:
    build: .
    ports: ["8003:8002"]
    env_file: .env
    command: uvicorn backend.main:app --host 0.0.0.0 --port 8002 --reload
    volumes: [./backend:/app/backend]
    networks: [fgt-network]
networks:
  fgt-network:
    external: true
    name: fgt-dev_fgt-net
```

### Miljovaribler (.env)
```
DATABASE_URL=postgresql://fgc:devpassword@postgres:5432/fgc_checkin
ADMIN_PIN=fgcthn2016
SECRET_KEY=change-me
```

---

## Vad som ska goras

### 1. Dockerfile

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 2. docker-compose.dev.yml

- Service: `meetup`
- Port: `8004:8000` (8000 internt, 8004 externt — undvik konflikter med 8001/8002/8003)
- env_file: `.env`
- Volume-mount `./src` for hot-reload
- Command: `uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload`
- Natverk: externt `fgt-dev_fgt-net`

### 3. .dockerignore

```
.venv/
__pycache__/
*.pyc
.git/
.claude/
data/
tests/
docs/
*.md
.env
```

---

## Vad som INTE ska andras

- Ingen kod i src/
- Inga templates eller JS
- Inget i requirements.txt

---

## Testning

1. Se till att turneringssystemets stack kor: `docker compose -p fgt-dev up -d`
2. Starta meetup: `docker compose -p fgt-meetup-dev -f docker-compose.dev.yml up --build`
3. Oppna `http://localhost:8004/kiosk` — ska visa kiosk-sidan
4. Kolla loggar att Postgres-poolen initieras korrekt
