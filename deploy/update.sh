#!/usr/bin/env bash
# Serverda botni GitHub'dagi eng yangi versiyaga yangilaydi.
# .env va baza (taxi.db) o'zgarmaydi.
# Ishlatish:  bash /opt/taxi-bot/deploy/update.sh
set -euo pipefail

URL="https://github.com/Abdumalik-web/first_project/archive/refs/heads/claude/telegram-driver-passenger-matching-x4mqyp.tar.gz"
APP_DIR=/opt/taxi-bot
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

echo ">>> Yangi versiya yuklanmoqda..."
curl -fsSL "$URL" -o "$TMP/bot.tar.gz"
tar -xzf "$TMP/bot.tar.gz" -C "$APP_DIR" --strip-components=1
bash "$APP_DIR/deploy/setup.sh"
