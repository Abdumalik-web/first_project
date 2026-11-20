#!/usr/bin/env bash
# Ubuntu/Debian serverda botni o'rnatib, doimiy ishlaydigan qilib qo'yadi.
# Ishlatish:  sudo bash setup.sh
set -euo pipefail

REPO="https://github.com/Abdumalik-web/first_project.git"
BRANCH="claude/intelligent-hamilton-0d3rbc"
DIR="/opt/reklama_bot"

apt-get update -y
apt-get install -y git python3 python3-venv

if [ -d "$DIR/.git" ]; then
  git -C "$DIR" pull --ff-only
else
  git clone -b "$BRANCH" "$REPO" "$DIR"
fi

python3 -m venv "$DIR/venv"
"$DIR/venv/bin/pip" install -q -r "$DIR/bot/requirements.txt"

if [ ! -f /etc/reklama_bot.env ]; then
  read -rsp "Bot tokenini kiriting (ko'rinmaydi): " TOKEN; echo
  TOKEN="${TOKEN//\"/}"
  printf 'BOT_TOKEN=%s\nBLOCK_ALL_LINKS=1\nDELETE_VIDEOS=0\nWARN_TTL=10\n' "$TOKEN" > /etc/reklama_bot.env
  chmod 600 /etc/reklama_bot.env
fi

if ! grep -q '^REQUIRED_BOT_TOKEN=' /etc/reklama_bot.env; then
  echo "Guruhga yozishdan oldin a'zolar start bosishi kerak bo'lgan boshqa bot bormi?"
  read -rsp "Bor bo'lsa o'sha botning tokenini kiriting, yo'q bo'lsa shunchaki Enter bosing: " REQ; echo
  REQ="${REQ//\"/}"
  echo "REQUIRED_BOT_TOKEN=$REQ" >> /etc/reklama_bot.env
fi

cat > /etc/systemd/system/reklama_bot.service <<UNIT
[Unit]
Description=Reklama o'chiruvchi Telegram bot
After=network-online.target
Wants=network-online.target

[Service]
WorkingDirectory=$DIR/bot
EnvironmentFile=/etc/reklama_bot.env
ExecStart=$DIR/venv/bin/python bot.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
UNIT

systemctl daemon-reload
systemctl enable --now reklama_bot
systemctl restart reklama_bot
sleep 3
systemctl --no-pager status reklama_bot | head -n 15
echo
echo "Tayyor! Loglarni ko'rish: journalctl -u reklama_bot -f"
