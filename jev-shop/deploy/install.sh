#!/usr/bin/env bash
# Installs the shop's timers on the server (Ubuntu). From the project folder:
#     sudo bash deploy/install.sh
# Works whether you log in as root (most VPS providers) or as ubuntu (Oracle Cloud).
#   jev-shop.timer      the daily run, 15:18 India time, Monday to Friday
#   jev-remind.timer    a Telegram nudge at 14:30 if you haven't logged in to Firstock yet
#   jev-news.timer      reads the news every hour and keeps the watch-list of stocks with serious bad news
#   jev-telegram        listens for /login, /status, /stop, /resume (only if Telegram is set up in .env)
# Undo: sudo systemctl disable --now jev-shop.timer jev-remind.timer jev-news.timer jev-telegram
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_USER="${SUDO_USER:-$(id -un)}"
HOME_DIR="$(getent passwd "$RUN_USER" | cut -d: -f6)"
UV="$HOME_DIR/.local/bin/uv"
[ -x "$UV" ] || UV="$(command -v uv || true)"
if [ -z "$UV" ] || [ ! -x "$UV" ]; then
  echo "uv isn't installed for $RUN_USER: run  curl -LsSf https://astral.sh/uv/install.sh | sh  first"; exit 1
fi
[ -f "$DIR/.env" ] || { echo "no .env in $DIR: copy it up first"; exit 1; }
UNIT_DIR="${UNIT_DIR:-/etc/systemd/system}"

service() {  # name, description, command, type
  cat > "$UNIT_DIR/$1.service" <<EOF
[Unit]
Description=$2
After=network-online.target
Wants=network-online.target

[Service]
Type=$4
User=$RUN_USER
WorkingDirectory=$DIR
ExecStart=$UV run python -m jevlab $3
Environment=PYTHONUNBUFFERED=1
EOF
}

timer() {  # name, description, calendar (India time)
  cat > "$UNIT_DIR/$1.timer" <<EOF
[Unit]
Description=$2

[Timer]
OnCalendar=$3 Asia/Kolkata
AccuracySec=1s

[Install]
WantedBy=timers.target
EOF
}

service jev-shop "Nifty Shop: the daily run" run oneshot
echo "TimeoutStartSec=900" >> "$UNIT_DIR/jev-shop.service"
timer jev-shop "Run the Nifty Shop at 15:18 India time on weekdays" "Mon..Fri *-*-* 15:18:00"

service jev-remind "Nifty Shop: remind me to log in" remind oneshot
timer jev-remind "Remind me to log in to Firstock at 14:30 India time on weekdays" "Mon..Fri *-*-* 14:30:00"

service jev-news "Nifty Shop: read the news, keep the watch-list" news oneshot
timer jev-news "Read the news every hour, 07:05 to 23:05 India time, every day" "*-*-* 07..23:05:00"

TELEGRAM=""
if grep -Eq '^TELEGRAM_BOT_TOKEN=.+' "$DIR/.env" && grep -Eq '^TELEGRAM_CHAT_ID=.+' "$DIR/.env"; then
  TELEGRAM=1
  service jev-telegram "Nifty Shop: Telegram commands (/login, /status, /stop, /resume)" telegram simple
  printf 'Restart=always\nRestartSec=10\n\n[Install]\nWantedBy=multi-user.target\n' >> "$UNIT_DIR/jev-telegram.service"
fi

echo "wrote the units to $UNIT_DIR (running as $RUN_USER, project in $DIR)"
if [ -n "${NO_SYSTEMCTL:-}" ]; then exit 0; fi
systemctl daemon-reload
systemctl enable --now jev-shop.timer jev-remind.timer jev-news.timer
if [ -n "$TELEGRAM" ]; then
  systemctl enable jev-telegram.service
  systemctl restart jev-telegram.service
  echo "Telegram listener running"
else
  echo "Telegram isn't set up in .env, so no listener (log in with: uv run python -m jevlab login)"
fi
systemctl list-timers 'jev-*' --no-pager
