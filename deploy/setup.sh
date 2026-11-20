#!/usr/bin/env bash
# Ubuntu/Debian serverda botni o'rnatadi yoki yangilaydi va doimiy ishga tushiradi.
# Ishlatish:  bash /opt/taxi-bot/deploy/setup.sh
set -euo pipefail

APP_DIR=/opt/taxi-bot
cd "$APP_DIR"

if [ ! -f .env ]; then
  echo "XATO: $APP_DIR/.env topilmadi. Avval .env faylni yuklang." >&2
  exit 1
fi
# Windows'da saqlangan fayllardagi \r belgilarini olib tashlaymiz
sed -i 's/\r$//' .env

echo ">>> Python o'rnatilmoqda..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq python3 python3-venv >/dev/null

echo ">>> Bot foydalanuvchisi..."
id -u taxibot >/dev/null 2>&1 || useradd --system --home-dir "$APP_DIR" --shell /usr/sbin/nologin taxibot

echo ">>> Kutubxonalar o'rnatilmoqda..."
[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -r requirements.txt

chown -R taxibot:taxibot "$APP_DIR"
chmod 600 .env

echo ">>> Xizmat ishga tushirilmoqda..."
cp deploy/taxi-bot.service /etc/systemd/system/taxi-bot.service
systemctl daemon-reload
systemctl enable taxi-bot >/dev/null
systemctl restart taxi-bot
sleep 3
systemctl --no-pager --lines=5 status taxi-bot || true
echo
echo "✅ Tayyor. Bot endi doim ishlaydi va server qayta yoqilganda o'zi ishga tushadi."
echo "Loglarni ko'rish: journalctl -u taxi-bot -f"
