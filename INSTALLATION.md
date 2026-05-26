# SheGlow — Hostinger VPS Deployment Guide

This guide takes you from a fresh Hostinger VPS to a fully running production store.
Estimated time: **45–60 minutes**.

---

## What You Need Before Starting

| Item | Where to get it |
|---|---|
| Hostinger VPS (KVM 2 or higher) | hostinger.com → VPS Hosting |
| A domain name | Hostinger or any registrar |
| A Gmail account for sending order emails | gmail.com |
| Your SheGlow project files | This folder, or a Git repo |

> **Which VPS plan?** KVM 2 (2 vCPU, 8 GB RAM, 100 GB NVMe) is plenty for launch.
> KVM 1 will work but may feel slow under load.

---

## Part 1 — Hostinger VPS Initial Setup

### 1.1 Create the VPS

1. In hPanel → **VPS** → **Create VPS**
2. Choose **Ubuntu 22.04** as the OS
3. Set a strong root password (save it)
4. Note your server's **IP address**

### 1.2 Point Your Domain to the VPS

In hPanel → **Domains** → select your domain → **DNS / Nameservers**:

Add two A records:

```
Type  Name   Value           TTL
A     @      <YOUR_VPS_IP>   3600
A     www    <YOUR_VPS_IP>   3600
```

DNS changes take up to 24 h but usually propagate in 5–15 minutes.

### 1.3 SSH Into the Server

From your local machine:

```bash
ssh root@<YOUR_VPS_IP>
```

### 1.4 Create a Non-Root User

Running the app as root is a security risk. Create a dedicated user:

```bash
adduser sheglow
usermod -aG sudo sheglow
```

### 1.5 Configure the Firewall

```bash
ufw allow OpenSSH
ufw allow 80
ufw allow 443
ufw enable
```

Log in as the new user for the rest of this guide:

```bash
su - sheglow
```

---

## Part 2 — Install Server Dependencies

```bash
sudo apt update && sudo apt upgrade -y

# Python 3.13
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt install -y python3.13 python3.13-venv python3.13-dev

# PostgreSQL
sudo apt install -y postgresql postgresql-contrib

# Nginx
sudo apt install -y nginx

# Build tools for psycopg2
sudo apt install -y libpq-dev gcc

# Certbot (SSL)
sudo apt install -y certbot python3-certbot-nginx

# Git (to pull your code)
sudo apt install -y git
```

---

## Part 3 — Set Up the Database

```bash
sudo -u postgres psql
```

Inside the Postgres prompt, run:

```sql
CREATE DATABASE sheglow;
CREATE USER sheglowuser WITH PASSWORD 'choose_a_strong_password_here';
ALTER ROLE sheglowuser SET client_encoding TO 'utf8';
ALTER ROLE sheglowuser SET default_transaction_isolation TO 'read committed';
ALTER ROLE sheglowuser SET timezone TO 'Africa/Cairo';
GRANT ALL PRIVILEGES ON DATABASE sheglow TO sheglowuser;
\q
```

> Save the password — you will need it in the `.env` file.

---

## Part 4 — Upload the Project

### Option A — Git (recommended)

If you pushed the project to GitHub/GitLab:

```bash
cd /home/sheglow
git clone https://github.com/YOUR_USERNAME/SheGlow.git
cd SheGlow
```

### Option B — Upload via SCP/SFTP

From your local machine, upload the project folder:

```bash
scp -r /Users/mostafa/Projects/SheGlow sheglow@<YOUR_VPS_IP>:/home/sheglow/
```

Then on the server:

```bash
cd /home/sheglow/SheGlow
```

---

## Part 5 — Python Virtual Environment

```bash
cd /home/sheglow/SheGlow

python3.13 -m venv venv
source venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt
```

---

## Part 6 — Gmail Setup for Transactional Emails

SheGlow sends order confirmation emails and password reset links. The easiest email
provider for a small store is **Gmail with an App Password**.

### 6.1 Enable 2-Step Verification on Gmail

1. Go to myaccount.google.com → **Security**
2. Turn on **2-Step Verification** (required before App Passwords work)

### 6.2 Generate an App Password

1. Go to myaccount.google.com → **Security** → **2-Step Verification** → scroll to bottom
2. Click **App passwords**
3. Select app: **Mail**, device: **Other** → type `SheGlow`
4. Click **Generate**
5. Copy the 16-character password (e.g. `abcd efgh ijkl mnop`) — you won't see it again
6. Remove the spaces when pasting into `.env` → `abcdefghijklmnop`

> This is what goes in `EMAIL_HOST_PASSWORD` in the next step.

---

## Part 7 — Create the `.env` File

```bash
nano /home/sheglow/SheGlow/.env
```

Paste and fill in every value:

```ini
# ─── Core ─────────────────────────────────────────────────────────────────────
SECRET_KEY=replace_with_a_long_random_string_50_chars_min
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# ─── Database ─────────────────────────────────────────────────────────────────
DATABASE_URL=postgres://sheglowuser:choose_a_strong_password_here@localhost:5432/sheglow

# ─── Email (Gmail App Password) ───────────────────────────────────────────────
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your_gmail_address@gmail.com
EMAIL_HOST_PASSWORD=abcdefghijklmnop
DEFAULT_FROM_EMAIL=SheGlow <your_gmail_address@gmail.com>

# ─── Business ─────────────────────────────────────────────────────────────────
WHATSAPP_NUMBER=20XXXXXXXXXX
INSTAGRAM_URL=https://instagram.com/sheglow
INSTAPAY_ID=your_instapay_id
VODAFONE_CASH_NUMBER=01XXXXXXXXX
DEFAULT_SHIPPING_FEE=50

# ─── PayMob (leave False until you have credentials) ──────────────────────────
PAYMOB_ENABLED=False
PAYMOB_API_KEY=
PAYMOB_INTEGRATION_ID=
PAYMOB_IFRAME_ID=
PAYMOB_HMAC_SECRET=

# ─── PostgreSQL password (used by docker-compose only, not needed here) ───────
POSTGRES_PASSWORD=choose_a_strong_password_here
```

Save with **Ctrl+O**, exit with **Ctrl+X**.

### Generating a Strong SECRET_KEY

Run this command and copy the output into SECRET_KEY above:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(50))"
```

---

## Part 8 — Django Production Setup

With your virtualenv still active:

```bash
cd /home/sheglow/SheGlow
source venv/bin/activate

# Apply all database migrations
python manage.py migrate

# Collect static files into staticfiles/
python manage.py collectstatic --noinput

# Create the admin superuser (enter your phone number + password)
python manage.py createsuperuser

# Seed product categories and sample products
python manage.py seed_data

# Seed all 27 governorate shipping zones
python manage.py seed_shipping_zones
```

---

## Part 9 — Gunicorn Systemd Service

Create a service file so Gunicorn starts automatically on boot and restarts on crash:

```bash
sudo nano /etc/systemd/system/sheglow.service
```

Paste:

```ini
[Unit]
Description=SheGlow Gunicorn
After=network.target

[Service]
User=sheglow
Group=www-data
WorkingDirectory=/home/sheglow/SheGlow
EnvironmentFile=/home/sheglow/SheGlow/.env
Environment="DJANGO_SETTINGS_MODULE=sheglow.settings.prod"
ExecStart=/home/sheglow/SheGlow/venv/bin/gunicorn \
    sheglow.wsgi:application \
    --bind unix:/run/sheglow.sock \
    --workers 3 \
    --timeout 120 \
    --access-logfile /home/sheglow/sheglow-access.log \
    --error-logfile /home/sheglow/sheglow-error.log
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable sheglow
sudo systemctl start sheglow

# Verify it started without errors
sudo systemctl status sheglow
```

You should see **active (running)** in green.

---

## Part 10 — Nginx Configuration

```bash
sudo nano /etc/nginx/sites-available/sheglow
```

Paste (replace `yourdomain.com` with your actual domain):

```nginx
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;

    # Redirect all HTTP to HTTPS (Certbot will update this block)
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name yourdomain.com www.yourdomain.com;

    # SSL certs (Certbot will fill these in)
    # ssl_certificate ...
    # ssl_certificate_key ...

    client_max_body_size 10M;

    # Static files served directly by Nginx (faster than Django)
    location /static/ {
        alias /home/sheglow/SheGlow/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Media files (uploaded images, receipts, banners)
    location /media/ {
        alias /home/sheglow/SheGlow/media/;
        expires 7d;
    }

    # Everything else goes to Gunicorn
    location / {
        include proxy_params;
        proxy_pass http://unix:/run/sheglow.sock;
        proxy_read_timeout 300;
        proxy_connect_timeout 300;
    }
}
```

Enable the site and test:

```bash
sudo ln -s /etc/nginx/sites-available/sheglow /etc/nginx/sites-enabled/
sudo nginx -t        # should print: syntax is ok
sudo systemctl reload nginx
```

---

## Part 11 — SSL Certificate (HTTPS)

```bash
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

Follow the prompts — Certbot will:
1. Verify your domain ownership (requires DNS to be pointing to this server)
2. Get a free Let's Encrypt certificate
3. Automatically update the Nginx config with the SSL cert paths
4. Set up auto-renewal (check: `sudo certbot renew --dry-run`)

---

## Part 12 — Fix File Permissions

```bash
# Gunicorn socket needs to be readable by www-data (Nginx)
sudo usermod -aG www-data sheglow

# Media and staticfiles directories
sudo chown -R sheglow:www-data /home/sheglow/SheGlow/media
sudo chown -R sheglow:www-data /home/sheglow/SheGlow/staticfiles
sudo chmod -R 755 /home/sheglow/SheGlow/media
sudo chmod -R 755 /home/sheglow/SheGlow/staticfiles
```

---

## Part 13 — Smoke Test

Open a browser and visit:

| URL | Expected |
|---|---|
| `https://yourdomain.com/` | Homepage with hero section |
| `https://yourdomain.com/shop/` | Product listing |
| `https://yourdomain.com/admin/` | Django admin login |
| `https://yourdomain.com/sitemap.xml` | XML sitemap |
| `https://yourdomain.com/robots.txt` | Robots file |
| `https://yourdomain.com/track/` | Order tracking page |

Log into `/admin/` with the superuser phone + password you created.

---

## Part 14 — Dev vs Production: What Changes

This table shows every setting that differs between local development and Hostinger:

| Setting | Dev (`.env` local) | Production (`.env` on server) |
|---|---|---|
| `DEBUG` | `True` | **`False`** |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | **`yourdomain.com,www.yourdomain.com`** |
| `SECRET_KEY` | any string | **long random string (50+ chars)** |
| `DATABASE_URL` | `sqlite:///db.sqlite3` | **`postgres://sheglowuser:pw@localhost:5432/sheglow`** |
| `EMAIL_BACKEND` | `console` (prints to terminal) | **`smtp.EmailBackend`** |
| `EMAIL_HOST_USER` | *(empty)* | **your Gmail address** |
| `EMAIL_HOST_PASSWORD` | *(empty)* | **Gmail App Password** |
| `DEFAULT_FROM_EMAIL` | `SheGlow <noreply@sheglow.com>` | **`SheGlow <your_gmail@gmail.com>`** |
| `DJANGO_SETTINGS_MODULE` | `sheglow.settings.dev` | **`sheglow.settings.prod`** |
| HTTPS redirect | off | **on** (prod.py: `SECURE_SSL_REDIRECT=True`) |
| HSTS headers | off | **on** (31536000 s) |
| Secure cookies | off | **on** (SESSION_COOKIE_SECURE, CSRF_COOKIE_SECURE) |
| Static files | Django serves them | **Nginx serves `/staticfiles/` directly** |

The `sheglow/settings/prod.py` file already applies all the security settings — you
just need the `.env` values to match the table above.

---

## Part 15 — Admin First Steps After Launch

Once the site is live, do these in the Django admin (`/admin/`):

1. **Create a Banner** (`pages → Banners → Add`):
   - Set Title, Subtitle, button text/URL
   - Check **Is active**
   - This replaces the hardcoded hero section

2. **Review shipping zones** (`orders → Shipping zones`):
   - Zones are pre-seeded; adjust fees if your actual rates differ

3. **Add real products** (`products → Products → Add`):
   - Or use the existing seed products as a starting point
   - Add product images, set stock levels, set badges

4. **Create promo codes** (`orders → Promo codes`):
   - Optional: launch discount code for opening day

---

## Part 16 — Updating the App

When you push new code:

```bash
cd /home/sheglow/SheGlow
source venv/bin/activate

git pull origin main                        # pull new code
pip install -r requirements.txt             # in case new packages
python manage.py migrate                    # run any new migrations
python manage.py collectstatic --noinput    # update static files

sudo systemctl restart sheglow             # restart Gunicorn
sudo systemctl reload nginx                # reload Nginx config
```

---

## Part 17 — Troubleshooting

### Site shows 502 Bad Gateway

Gunicorn is not running or crashed:

```bash
sudo systemctl status sheglow
sudo journalctl -u sheglow -n 50 --no-pager
```

### Site shows 500 Internal Server Error

Check the Django error log:

```bash
tail -50 /home/sheglow/sheglow-error.log
```

Also check with DEBUG temporarily on by adding `DEBUG=True` to `.env`, restart
Gunicorn, reproduce the error, then set it back to `False`.

### Emails not sending

Test from the Django shell:

```bash
source venv/bin/activate
python manage.py shell -c "
from django.core.mail import send_mail
send_mail('Test', 'Test body', None, ['your_email@gmail.com'])
print('Sent OK')
"
```

Common causes:
- Wrong `EMAIL_HOST_PASSWORD` — must be the 16-char App Password, no spaces
- 2FA not enabled on Gmail (App Passwords require it)
- Gmail account has "less secure app access" blocked — use App Password instead

### Static files not loading (CSS/JS broken)

```bash
python manage.py collectstatic --noinput
sudo systemctl reload nginx
```

Check that `STATIC_ROOT` in the Nginx config matches `/home/sheglow/SheGlow/staticfiles/`.

### SSL certificate errors

```bash
sudo certbot renew --dry-run
sudo certbot certificates   # check expiry
```

---

## Part 18 — Backup Strategy

### Database backup

```bash
# Run manually or add to cron
pg_dump -U sheglowuser -d sheglow > /home/sheglow/backup_$(date +%Y%m%d).sql
```

### Media files backup

```bash
tar -czf /home/sheglow/media_backup_$(date +%Y%m%d).tar.gz /home/sheglow/SheGlow/media/
```

### Automated daily backup (cron)

```bash
crontab -e
```

Add:

```
0 3 * * * pg_dump -U sheglowuser -d sheglow > /home/sheglow/backups/db_$(date +\%Y\%m\%d).sql
0 3 * * * tar -czf /home/sheglow/backups/media_$(date +\%Y\%m\%d).tar.gz /home/sheglow/SheGlow/media/
```

---

## Quick Reference — All Commands

```bash
# Start/stop/restart app
sudo systemctl start sheglow
sudo systemctl stop sheglow
sudo systemctl restart sheglow

# View live logs
sudo journalctl -u sheglow -f

# Django management
source /home/sheglow/SheGlow/venv/bin/activate
cd /home/sheglow/SheGlow
python manage.py shell
python manage.py createsuperuser
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py seed_data
python manage.py seed_shipping_zones

# Nginx
sudo nginx -t
sudo systemctl reload nginx

# SSL renewal
sudo certbot renew
```
