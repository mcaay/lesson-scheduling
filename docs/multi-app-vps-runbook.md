# Django apps on the mcaay VPS

This is the deployment convention for independent Django applications on this
VPS. Each application is a direct sibling in `/home/mcaay`, while Nginx routes
requests by hostname to the app's private Gunicorn socket.

## Current deployment

`lesson-scheduling` is live at:

```text
https://dance-lesson-scheduling.duckdns.org/
```

It has one Gunicorn worker, an automatically renewed Let's Encrypt certificate,
and an HTTP-to-HTTPS redirect. The service is enabled at boot; Nginx and UFW
permit ports 80 and 443.

## Layout and naming convention

Use one lowercase, hyphenated *slug* per application. Keep its Python package
name separate when necessary.

```text
/home/mcaay/<slug>/                         application checkout, .venv, SQLite database
/home/mcaay/<slug>/static/                  collected public static files
/etc/mcaay-django/<slug>.env                root-only Django/Gunicorn environment
/run/mcaay-django-<slug>/gunicorn.sock      volatile private Gunicorn socket
/etc/systemd/system/mcaay-django-<slug>.service
/etc/nginx/sites-available/<slug>
/etc/nginx/sites-enabled/<slug>
```

The application source, SQLite database, and collected static files stay under
`/home/mcaay`, as requested. Django's source assets can remain in individual
app directories such as `scheduler/static/`; `collectstatic` copies them into
the project-root `static/` directory served by Nginx.

`/home/mcaay` remains mode `0750`. Nginx receives execute-only ACL access to
the home directory and each project's directory, so it can traverse to a
known public static path without listing private home or project contents.

Every app gets its own virtual environment, secret/config file, static output,
systemd service, Unix socket, Nginx site, hostname, and backup plan.

## Routing rule: one hostname per app

Use a domain or subdomain for each app, for example:

```text
schedule.example.com  -> lesson-scheduling
notes.example.com     -> notes
```

Nginx cannot distinguish several independent Django apps all mounted at `/` on
the same IP address. Hostname-based routing avoids Django path-prefix, URL,
static-file, and CSRF complications. The bare server IP is only a temporary
single-app smoke-test address.

`/etc/nginx/sites-available/00-default-deny` rejects unknown hostnames, so a
new site cannot accidentally serve another application's content.

## Lesson-scheduling reference

The active service is `mcaay-django-lesson-scheduling.service`:

```ini
[Service]
User=mcaay
Group=www-data
WorkingDirectory=/home/mcaay/lesson-scheduling
EnvironmentFile=/etc/mcaay-django/lesson-scheduling.env
RuntimeDirectory=mcaay-django-lesson-scheduling
RuntimeDirectoryMode=0750
UMask=0007
ExecStart=/home/mcaay/lesson-scheduling/.venv/bin/gunicorn lesson_scheduling.wsgi:application \
    --bind unix:/run/mcaay-django-lesson-scheduling/gunicorn.sock \
    --workers 1 --timeout 60 --graceful-timeout 30 \
    --access-logfile - --error-logfile - --capture-output --umask 007
```

The socket is owned by `mcaay:www-data` with mode `0660`, allowing only Nginx
to reach Gunicorn. The shared Nginx proxy headers live in
`/etc/nginx/snippets/mcaay-django-proxy.conf`.

The root-only environment file contains values like:

```ini
DJANGO_SETTINGS_MODULE=lesson_scheduling.settings
DJANGO_SECRET_KEY=<generated-secret>
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=dance-lesson-scheduling.duckdns.org
DJANGO_CSRF_TRUSTED_ORIGINS=https://dance-lesson-scheduling.duckdns.org
DJANGO_STATIC_ROOT=/home/mcaay/lesson-scheduling/static
DJANGO_SECURE_SSL_REDIRECT=True
DJANGO_SESSION_COOKIE_SECURE=True
DJANGO_CSRF_COOKIE_SECURE=True
DJANGO_SECURE_HSTS_SECONDS=86400
```

Never commit this file or put the secret in a systemd unit.

## Add a new app

Assume a new checkout at `/home/mcaay/<slug>`, a WSGI application named
`<python_package>.wsgi:application`, and a hostname `<host>`.

1. Create its own `.venv`, install the application with its committed
   `requirements.lock` constraints (`pip install -c requirements.lock .`), and
   make Django settings read `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`,
   `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS`, and
   `DJANGO_STATIC_ROOT`. The `lesson-scheduling` settings are the reference.

2. Create the project-root static output directory and grant Nginx only
   traversal access through the otherwise-private parent directories:

   ```bash
   sudo -u mcaay -- install -d -m 0755 /home/mcaay/<slug>/static
   chmod 0750 /home/mcaay/<slug>
   setfacl -m u:www-data:--x /home/mcaay /home/mcaay/<slug>
   find /home/mcaay/<slug>/static -type d -exec chmod 0750 {} +
   find /home/mcaay/<slug>/static -type f -exec chmod 0640 {} +
   setfacl -R -m u:www-data:rX /home/mcaay/<slug>/static
   find /home/mcaay/<slug>/static -type d \
       -exec setfacl -m d:u:www-data:r-x {} +
   ```

   The named ACL lets Nginx read only the collected assets; it cannot list the
   home or project directories. The default ACL preserves that access for later
   `collectstatic --clear` runs, provided the static root itself is retained.

3. Create `/etc/mcaay-django/<slug>.env` as `root:root`, mode `0600`. Generate
   a unique secret, set `DJANGO_DEBUG=False`, exact comma-separated allowed
   hosts, HTTPS CSRF origins, and the app-specific static path.

4. Copy the lesson-scheduling systemd unit to
   `/etc/systemd/system/mcaay-django-<slug>.service`. Change only the slug,
   project path, Python WSGI target, and socket path. Start with one worker per
   app; increase the total only after checking the VPS's memory and CPU use.

5. Copy the Nginx site to `/etc/nginx/sites-available/<slug>`. Give it exactly
   one `server_name <host>`, the app's static alias, and its own Unix socket.
   Enable with a symlink in `sites-enabled`. Do not use a shared catch-all site
   for application traffic.

6. With the environment loaded, run deployment maintenance as `mcaay`:

   ```bash
   sudo -u mcaay -- /home/mcaay/<slug>/.venv/bin/python \
       /home/mcaay/<slug>/manage.py check --deploy
   sudo -u mcaay -- /home/mcaay/<slug>/.venv/bin/python \
       /home/mcaay/<slug>/manage.py migrate --noinput
   sudo -u mcaay -- /home/mcaay/<slug>/.venv/bin/python \
       /home/mcaay/<slug>/manage.py collectstatic --noinput
   ```

   The command needs the same protected runtime settings as the service,
   including its secret. Source the protected environment file only from a root
   shell, then pass the required values explicitly to the `mcaay` command.

7. Validate and start safely:

   ```bash
   systemd-analyze verify /etc/systemd/system/mcaay-django-<slug>.service
   systemctl daemon-reload
   systemctl enable --now mcaay-django-<slug>.service
   nginx -t
   systemctl reload nginx
   ```

   Test the upstream as `www-data` with its socket, then test Nginx with the
   intended `Host` header. Check `journalctl -u mcaay-django-<slug>` and the
   app-specific Nginx logs if either request fails.

## HTTPS

HTTPS is active for `dance-lesson-scheduling.duckdns.org`. Certbot owns the
certificate configuration, redirects port 80 to HTTPS, and its enabled systemd
timer renews the certificate automatically. Check it with:

```bash
certbot certificates
systemctl status certbot.timer --no-pager
```

For a new hostname, allow ports 80 and 443, install Certbot with its Nginx
plugin, obtain its certificate, switch the CSRF origin to HTTPS, then enable
the three secure Django cookie/redirect variables shown above.

This app sends a conservative 24-hour HSTS policy. It intentionally does not
include subdomains or opt into browser preload, because those are stronger and
longer-lived commitments. Django's corresponding `check --deploy` advisories
are therefore expected; reconsider them only when every possible subdomain is
known to support HTTPS.

## Operations

Useful commands for an app slug:

```bash
systemctl status mcaay-django-<slug> --no-pager
journalctl -u mcaay-django-<slug> -n 100 --no-pager
systemctl restart mcaay-django-<slug>
nginx -t && systemctl reload nginx
```

Back up each SQLite database and any future media separately. SQLite is fine
for a small low-write app, but a busier app or several concurrent Gunicorn
workers should move to PostgreSQL before write locking becomes a problem.
