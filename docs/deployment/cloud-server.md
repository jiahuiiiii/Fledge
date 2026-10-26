# Run a Fledge test copy on a cloud server

This puts a **separate test copy** of Fledge on a small Linux server so friends can try it from their phones. It has its own database, its own AI key and a hard AI spending cap. It is not the original installation and its results are not the original installation's evidence ([test copy rules](../development/test-copy.md)).

Checked against the code in this repository; the steps below were not run on a real cloud host. Expect to adjust names and versions.

## What you need

| Item | Notes |
| --- | --- |
| A Linux server | Ubuntu 24.04, 2 GB RAM, 1–2 vCPU is enough for a small group (e.g. DigitalOcean, Hetzner, Lightsail, Vultr). Singapore region if offered. |
| A domain or subdomain | e.g. `fledge.yourname.com`, with an **A record** pointing at the server's IP. HTTPS needs a name, not a bare IP. |
| OpenAI API key | Set a **monthly usage limit** in the OpenAI dashboard too: the in-app cap is the second line of defence, not the first. |
| Finnhub key | Free tier is fine to start. |
| `SEC_USER_AGENT` | `Fledge test your-email@example.com` (SEC asks for a contact). |
| Privacy contact email | Shown in the Terms and Privacy Notice (PDPA). |

## 1. Server basics

```sh
# As root, once:
apt update && apt -y upgrade
apt -y install git python3.12-venv python3-pip curl ca-certificates gnupg locales ufw
locale-gen en_US.UTF-8
adduser --disabled-password --gecos "" fledge      # PostgreSQL refuses to run as root
ufw allow OpenSSH && ufw allow 80 && ufw allow 443 && ufw enable
```

PostgreSQL 18 (from the PostgreSQL apt repository; only the binaries are used, Fledge runs its own private cluster):

```sh
install -d /usr/share/postgresql-common/pgdg
curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc -o /usr/share/postgresql-common/pgdg/apt.postgresql.org.asc
echo "deb [signed-by=/usr/share/postgresql-common/pgdg/apt.postgresql.org.asc] https://apt.postgresql.org/pub/repos/apt noble-pgdg main" > /etc/apt/sources.list.d/pgdg.list
apt update && apt -y install postgresql-18
systemctl disable --now postgresql   # the system cluster is not used
```

Node 24 (only to build the frontend):

```sh
curl -fsSL https://deb.nodesource.com/setup_24.x | bash -
apt -y install nodejs
```

## 2. Get the code and build

```sh
su - fledge
git clone https://github.com/jiahuiiiii/Fledge.git
cd Fledge
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cd frontend && npm ci --ignore-scripts && npm run build && cd ..
cp .env.example .env && chmod 600 .env
```

## 3. Fill in `.env`

Edit `/home/fledge/Fledge/.env` on the server (never paste keys into chat or commit them). The lines that matter:

```ini
THESIS_AUTH_MODE=password
THESIS_PUBLIC_ORIGIN=https://fledge.yourname.com
THESIS_PRIVACY_CONTACT=you@example.com

OPENAI_API_KEY=...
THESIS_MODEL_SERVING_PROVIDER=openai
THESIS_SENTIMENT_MODEL=gpt-6-luna
THESIS_LIVE_MODELS_ENABLED=true
THESIS_TEST_COPY=true
THESIS_TEST_COPY_CAP_USD=10        # total AI spend for this copy, max 100

THESIS_LIVE_DATA_ENABLED=true
FINNHUB_API_KEY=...
SEC_USER_AGENT=Fledge test you@example.com
```

For Telegram alerts, add a bot token too (see "Telegram alerts" below):

```ini
TELEGRAM_BOT_TOKEN=...
```

Leave the Supabase lines empty. `THESIS_PUBLIC_ORIGIN` must be exactly the address people type, with `https://` and no trailing slash: it lets the browser's requests through and marks the sign-in cookie HTTPS-only.

## 4. First start (by hand)

```sh
export THESIS_PG_BIN=/usr/lib/postgresql/18/bin LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8
.venv/bin/python run.py --port 8841
```

It creates the private database in `.local/`, applies migrations and serves on `127.0.0.1:8841` only. Stop it with Ctrl+C once it starts cleanly.

## 5. Keep it running (systemd)

As root, create `/etc/systemd/system/fledge.service`:

```ini
[Unit]
Description=Fledge test copy
After=network-online.target

[Service]
User=fledge
WorkingDirectory=/home/fledge/Fledge
Environment=THESIS_PG_BIN=/usr/lib/postgresql/18/bin
Environment=LC_ALL=en_US.UTF-8
Environment=LANG=en_US.UTF-8
ExecStart=/home/fledge/Fledge/.venv/bin/python run.py --port 8841
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```sh
systemctl daemon-reload && systemctl enable --now fledge
journalctl -u fledge -f      # logs
```

## 6. HTTPS in front (Caddy)

```sh
apt -y install caddy
cat > /etc/caddy/Caddyfile <<'EOF'
fledge.yourname.com {
    encode gzip
    reverse_proxy 127.0.0.1:8841
}
EOF
systemctl reload caddy
```

Caddy gets and renews the certificate automatically once the DNS record points at the server. Open `https://fledge.yourname.com`, create an account, save the recovery code, and check that the Privacy page shows your contact email.

## 7. Backups

The research database lives in `/home/fledge/Fledge/.local/`. A nightly dump, as the `fledge` user (`crontab -e`):

```cron
15 3 * * * mkdir -p ~/backups && /usr/lib/postgresql/18/bin/pg_dump -h ~/Fledge/.local/socket -p 55439 -U thesis_local -Fc thesis > ~/backups/fledge-$(date +\%F).dump && find ~/backups -name 'fledge-*.dump' -mtime +14 -delete
```

`thesis_local` is the cluster's superuser that `run.py` creates; the socket only accepts connections from the `fledge` user on this machine. Copy a dump off the server now and then (your provider's snapshots also work). Keep `.env` out of any shared backup.

## 8. Forgotten passwords

Users reset their own password with the recovery code they saved at sign-up (**Forgot password?** on Sign in). If someone lost the code too, reset it for them on the server:

```sh
cd ~/Fledge && THESIS_PG_BIN=/usr/lib/postgresql/18/bin .venv/bin/python -m thesis.password_auth reset <username>
```

It asks for a temporary password, signs that account out everywhere and removes the old recovery code. Give them the temporary password privately; they change it and create a new recovery code from **Account → Password and recovery code**. Check who is asking before you do this.

## 9. Updating

```sh
su - fledge && cd Fledge && git pull
.venv/bin/python -m pip install -r requirements.txt
cd frontend && npm ci --ignore-scripts && npm run build && cd ..
exit
systemctl restart fledge
```

New migrations apply automatically at start. Take a backup first.

## Telegram alerts

Without `TELEGRAM_BOT_TOKEN` the Telegram card on the Account page is hidden and
"Watch for changes" never asks people to connect Telegram, because there is
nothing to connect to.

1. In Telegram, open a chat with **@BotFather**, send `/newbot`, pick a name and a
   username ending in `bot`. It replies with a token.
2. Put it in `.env` as `TELEGRAM_BOT_TOKEN=...` (on the server, never in chat or git).
3. `sudo systemctl restart fledge`. The Account page now shows Telegram alerts → Manage.

## Finding slow pages

Every API answer has a `Server-Timing` header (browser dev tools → Network → a
request → Timing): total time, time in the database and how many transactions it
used. Requests over 1.5 s are also logged:

```sh
journalctl -u fledge --since "1 hour ago" | grep "Slow request"
```

If everything is slow at once, check the CPU first: `top` (press `1`). A small
Lightsail plan has a burstable CPU; when its credits run out the whole server runs at
a fraction of one core (Lightsail console → the instance → Metrics → CPU).

## Before you invite people

- Tell testers it is a test: data can be reset, AI can be wrong, it is not financial advice.
- Set the OpenAI monthly limit and the in-app cap; when the cap is reached, AI features stop until you raise it.
- Only the server owner should hold SSH access and `.env`.
- Monitoring and alerts run while the server runs; there is no separate worker to start.
