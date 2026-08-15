# VPS nginx + gunicorn setup notes (historical)

> The deployed, reusable runbook is now
> [`multi-app-vps-runbook.md`](multi-app-vps-runbook.md). These original notes
> are retained for context; do not copy their inline-secret examples for new
> deployments.

Target server: `167.233.147.146`

Project checkout:

```bash
/home/mcaay/lesson-scheduling
```

Current project virtual environment:

```bash
/home/mcaay/lesson-scheduling/.venv
```

Verified on 2026-07-09:

```bash
cd /home/mcaay/lesson-scheduling
.venv/bin/python --version
# Python 3.14.4

.venv/bin/python manage.py check
# System check identified no issues

.venv/bin/python -m pytest -q
# 74 passed
```

## Important production settings first

Before exposing the app through nginx, fix the Django production settings.

Current `lesson_scheduling/settings.py` is still development-only:

```python
SECRET_KEY = "dev-secret-key"
DEBUG = True
ALLOWED_HOSTS = []
```

Root Codex should either add environment-variable based settings or create a small production settings module. Minimum requirements:

```python
import os

SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]
DEBUG = os.environ.get("DJANGO_DEBUG", "False") == "True"
ALLOWED_HOSTS = os.environ["DJANGO_ALLOWED_HOSTS"].split(",")
CSRF_TRUSTED_ORIGINS = os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",")
STATIC_ROOT = BASE_DIR / "staticfiles"
```

Use the real domain when known. Until then, use the server IP in `ALLOWED_HOSTS` only for a temporary smoke test.

SQLite is expected and should stay in the project directory unless deliberately changed:

```bash
/home/mcaay/lesson-scheduling/db.sqlite3
```

The service should run as user `mcaay`, not as root, even if root Codex performs the setup.

## Python environment

The venv already exists and has the app/test dependencies installed. For gunicorn, either add it to the project dependencies or install it explicitly into the venv:

```bash
cd /home/mcaay/lesson-scheduling
sudo -u mcaay .venv/bin/python -m pip install "gunicorn>=23,<24"
```

After production settings are fixed, run:

```bash
cd /home/mcaay/lesson-scheduling
sudo -u mcaay .venv/bin/python manage.py check --deploy
sudo -u mcaay .venv/bin/python manage.py migrate
sudo -u mcaay .venv/bin/python manage.py collectstatic --noinput
```

## Gunicorn systemd service

Create `/etc/systemd/system/lesson-scheduling.service`:

```ini
[Unit]
Description=lesson-scheduling Django app
After=network.target

[Service]
Type=notify
User=mcaay
Group=www-data
WorkingDirectory=/home/mcaay/lesson-scheduling
RuntimeDirectory=lesson-scheduling
RuntimeDirectoryMode=0755
Environment=DJANGO_SETTINGS_MODULE=lesson_scheduling.settings
Environment=DJANGO_SECRET_KEY=replace-me
Environment=DJANGO_DEBUG=False
Environment=DJANGO_ALLOWED_HOSTS=167.233.147.146
Environment=DJANGO_CSRF_TRUSTED_ORIGINS=http://167.233.147.146
ExecStart=/home/mcaay/lesson-scheduling/.venv/bin/gunicorn \
    lesson_scheduling.wsgi:application \
    --bind unix:/run/lesson-scheduling/gunicorn.sock \
    --workers 2 \
    --access-logfile - \
    --error-logfile -
ExecReload=/bin/kill -s HUP $MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Then:

```bash
systemctl daemon-reload
systemctl enable --now lesson-scheduling
systemctl status lesson-scheduling --no-pager
journalctl -u lesson-scheduling -n 100 --no-pager
```

If `Type=notify` causes startup issues with the packaged gunicorn version, change it to:

```ini
Type=simple
```

and reload systemd again.

## nginx

Install nginx:

```bash
apt update
apt install -y nginx
```

Create `/etc/nginx/sites-available/lesson-scheduling`:

```nginx
server {
    listen 80;
    listen [::]:80;

    server_name 167.233.147.146;

    client_max_body_size 10M;

    location /static/ {
        alias /home/mcaay/lesson-scheduling/staticfiles/;
        access_log off;
        expires 30d;
    }

    location / {
        include proxy_params;
        proxy_pass http://unix:/run/lesson-scheduling/gunicorn.sock;
    }
}
```

Enable it:

```bash
ln -sf /etc/nginx/sites-available/lesson-scheduling /etc/nginx/sites-enabled/lesson-scheduling
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx
```

Smoke test locally on the VPS:

```bash
curl -I http://127.0.0.1/
curl -I http://167.233.147.146/
```

## Firewall

If `ufw` is used:

```bash
ufw allow OpenSSH
ufw allow "Nginx Full"
ufw status verbose
```

Do not enable `ufw` until SSH key login has been verified in a second session.

## Later when a domain is known

Update:

- nginx `server_name`
- `DJANGO_ALLOWED_HOSTS`
- `DJANGO_CSRF_TRUSTED_ORIGINS`

Then add TLS with certbot or another ACME client.

Do not leave `DJANGO_SECRET_KEY=replace-me` in production.
