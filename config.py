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
ADMIN_CHAT_ID = os.environ.get("ADMIN_CHAT_ID", "")
DB_PATH = os.environ.get("DB_PATH", os.path.join(BASE_DIR, "leads.db"))
SELLER_NAME = os.environ.get("SELLER_NAME", "Самозанятый Исполнитель")
SELLER_INN = os.environ.get("SELLER_INN", "000000000000")
BANK_NAME = os.environ.get("BANK_NAME", "")
BANK_BIK = os.environ.get("BANK_BIK", "")
BANK_CORR = os.environ.get("BANK_CORR", "")
BANK_ACCOUNT = os.environ.get("BANK_ACCOUNT", "")
PAYMENT_SBP = os.environ.get("PAYMENT_SBP", "")
API_BASE = f"https://api.telegram.org/bot{BOT_TOKEN}"
