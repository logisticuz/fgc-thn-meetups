# Arbetsorder: Nginx + SSL för meetup.fgctrollhattan.se

## Mål

Konfigurera nginx reverse proxy och SSL (certbot) så att meetup-systemet
nås via `https://meetup.fgctrollhattan.se` från lokalnätverket och internet.

## Förutsättningar

- DNS A-post skapad: `meetup.fgctrollhattan.se` → `213.89.64.103` (One.com)
- Meetup-containern körs på port **8004** (`docker-compose.prod.yml`)
- Nginx och certbot finns redan installerade (används av checkin/admin)
- Befintliga nginx-siter: `checkin.fgctrollhattan.se`, `admin.fgctrollhattan.se`

## Steg

### 1. Verifiera DNS-propagering

```bash
dig +short meetup.fgctrollhattan.se
# Förväntat: 213.89.64.103
```

Om inte propagerat ännu, vänta och försök igen. Kan ta upp till 1 timme.

### 2. Skapa nginx server block

Skapa filen `/etc/nginx/sites-available/meetup`:

```nginx
server {
    listen 80;
    server_name meetup.fgctrollhattan.se;

    location / {
        proxy_pass http://127.0.0.1:8004;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

**Tips:** Titta på befintlig site-config (t.ex. `/etc/nginx/sites-available/checkin`)
för att matcha eventuella lokala konventioner (buffering, timeouts, etc).

### 3. Aktivera siten

```bash
sudo ln -s /etc/nginx/sites-available/meetup /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 4. Testa HTTP

```bash
curl -I http://meetup.fgctrollhattan.se/kiosk
# Förväntat: HTTP 200
```

### 5. SSL med certbot

```bash
sudo certbot --nginx -d meetup.fgctrollhattan.se
```

Certbot uppdaterar nginx-configen automatiskt med HTTPS-redirect och cert-sökvägar.

### 6. Verifiera HTTPS

```bash
curl -I https://meetup.fgctrollhattan.se/kiosk
# Förväntat: HTTP 200, certificate valid
```

Kontrollera även att HTTP → HTTPS redirect fungerar:
```bash
curl -I http://meetup.fgctrollhattan.se/kiosk
# Förväntat: 301 → https://meetup.fgctrollhattan.se/kiosk
```

## Klart-kriterier

- [ ] `https://meetup.fgctrollhattan.se/kiosk` svarar med 200
- [ ] HTTP redirectar till HTTPS
- [ ] SSL-cert giltigt (certbot/Let's Encrypt)
- [ ] Inga fel i `sudo nginx -t`
