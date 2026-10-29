#!/usr/bin/env python3
"""
⚙️ Модуль конфигурации бота
Загружает переменные из .env файла без сторонних библиотек.
"""

import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_FILE = os.path.join(BASE_DIR, ".env")


def load_env():
    """Чтение файла .env и загрузка переменных в os.environ."""
    if os.path.exists(ENV_FILE):
        with open(ENV_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    os.environ[key.strip()] = val.strip().strip("'\"")


load_env()

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
ADMIN_CHAT_ID = os.environ.get("ADMIN_CHAT_ID", "707755583")
DB_PATH = os.environ.get("DB_PATH", os.path.join(BASE_DIR, "leads.db"))
API_BASE = f"https://api.telegram.org/bot{BOT_TOKEN}"
