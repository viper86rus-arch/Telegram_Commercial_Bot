#!/usr/bin/env python3
"""
📁 Модуль базы данных SQLite (database.py)
Отвечает за сохранение лидов, настройки и экспорт данных в CSV/Excel.
"""

import csv
import os
import sqlite3
from config import ADMIN_CHAT_ID, DB_PATH


def get_connection():
    """Получение подключения к SQLite с таймаутом."""
    return sqlite3.connect(DB_PATH, timeout=10)


def init_db():
    """Инициализация таблиц базы данных и миграции."""
    try:
        conn = get_connection()
        cur = conn.cursor()
        # Таблица заявок
        cur.execute("""
            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                username TEXT,
                full_name TEXT,
                message TEXT,
                status TEXT DEFAULT 'new',
                paid_amount INTEGER DEFAULT 0,
                payment_id TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Миграция существующих таблиц (если созданы в предыдущих версиях)
        cur.execute("PRAGMA table_info(leads)")
        columns = [row[1] for row in cur.fetchall()]
        if "status" not in columns:
            cur.execute("ALTER TABLE leads ADD COLUMN status TEXT DEFAULT 'new'")
        if "paid_amount" not in columns:
            cur.execute("ALTER TABLE leads ADD COLUMN paid_amount INTEGER DEFAULT 0")
        if "payment_id" not in columns:
            cur.execute("ALTER TABLE leads ADD COLUMN payment_id TEXT DEFAULT ''")

        # Таблица настроек
        cur.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        # Закрепляем администратора по умолчанию
        cur.execute(
            "INSERT OR IGNORE INTO settings (key, value) VALUES ('admin_chat_id', ?)",
            (str(ADMIN_CHAT_ID),)
        )
        conn.commit()
        conn.close()
        print("📁 База данных SQLite (leads.db) успешно инициализирована.")
    except Exception as e:
        print(f"❌ Ошибка инициализации БД: {e}")


def save_lead(user_id, username, full_name, message):
    """Сохранение новой заявки в БД. Возвращает номер созданной заявки."""
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO leads (user_id, username, full_name, message, status) VALUES (?, ?, ?, ?, 'new')",
            (user_id, username, full_name, message)
        )
        lead_id = cur.lastrowid
        conn.commit()
        conn.close()
        return lead_id
    except Exception as e:
        print(f"❌ Ошибка сохранения заявки: {e}")
        return None


def record_payment(lead_id, amount, status, tx_id):
    """Фиксация оплаты (аванс или полная оплата) по заявке."""
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "UPDATE leads SET status = ?, paid_amount = ?, payment_id = ? WHERE id = ?",
            (status, amount, tx_id, lead_id)
        )
        conn.commit()
        conn.close()
        print(f"💳 Оплата по заявке #{lead_id} зафиксирована: {amount} ₽ ({status}, TX: {tx_id})")
        return True
    except Exception as e:
        print(f"❌ Ошибка записи оплаты: {e}")
        return False


def get_lead(lead_id):
    """Получение подробной информации о заявке по ID."""
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT id, user_id, username, full_name, message, status, paid_amount, payment_id, created_at FROM leads WHERE id = ?",
            (lead_id,)
        )
        row = cur.fetchone()
        conn.close()
        return row
    except Exception as e:
        print(f"❌ Ошибка получения заявки #{lead_id}: {e}")
        return None


def get_latest_leads(limit=5):
    """Получение последних N заявок."""
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT id, full_name, username, message, status, paid_amount, payment_id, created_at FROM leads ORDER BY id DESC LIMIT ?",
            (limit,)
        )
        rows = cur.fetchall()
        conn.close()
        return rows
    except Exception as e:
        print(f"❌ Ошибка чтения БД: {e}")
        return []


def get_all_leads():
    """Получение всех заявок для выгрузки."""
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT id, user_id, full_name, username, status, paid_amount, payment_id, message, created_at FROM leads ORDER BY id ASC"
        )
        rows = cur.fetchall()
        conn.close()
        return rows
    except Exception as e:
        print(f"❌ Ошибка чтения всех заявок: {e}")
        return []


def get_stats():
    """Получение детальной бизнес-статистики по базе данных."""
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT 
                COUNT(*), 
                COUNT(DISTINCT user_id),
                COALESCE(SUM(paid_amount), 0),
                COUNT(CASE WHEN paid_amount > 0 THEN 1 END)
            FROM leads
        """)
        total_leads, unique_clients, total_revenue, paid_orders = cur.fetchone()
        conn.close()
        return {
            "total_leads": total_leads or 0,
            "unique_clients": unique_clients or 0,
            "total_revenue": total_revenue or 0,
            "paid_orders": paid_orders or 0
        }
    except Exception as e:
        print(f"❌ Ошибка получения статистики: {e}")
        return {"total_leads": 0, "unique_clients": 0, "total_revenue": 0, "paid_orders": 0}


def set_setting(key, value):
    """Сохранение настройки в БД."""
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"❌ Ошибка записи настройки: {e}")


def get_setting(key, default=None):
    """Чтение настройки из БД."""
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = cur.fetchone()
        conn.close()
        return row[0] if row else default
    except Exception as e:
        print(f"❌ Ошибка чтения настройки: {e}")
        return default


def export_leads_to_csv(filepath=None):
    """
    Экспорт всех заявок в файл CSV с информацией о платежах.
    Использует кодировку 'utf-8-sig' с BOM для корректного открытия в Excel на Windows/Android/Mac.
    """
    if filepath is None:
        filepath = os.path.join(os.path.dirname(os.path.abspath(DB_PATH)), "leads_report.csv")
    try:
        leads = get_all_leads()
        status_map = {
            "new": "Новая заявка",
            "pending_advance": "Ожидает аванс (30%)",
            "pending_full": "Ожидает оплату (100%)",
            "paid_advance": "Оплачен аванс (30%)",
            "paid_full": "Оплачен полностью (100%)"
        }
        with open(filepath, mode="w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f, delimiter=";", quoting=csv.QUOTE_MINIMAL)
            # Заголовки таблицы
            writer.writerow([
                "ID Заявки",
                "User ID Telegram",
                "Имя клиента",
                "Telegram Ник",
                "Статус оплаты",
                "Оплачено (₽)",
                "ID Транзакции",
                "Текст задачи / Смета",
                "Дата и время (МСК)"
            ])
            for row in leads:
                lid, uid, fname, uname, status, paid_amount, tx_id, msg, dt = row
                uname_str = f"@{uname}" if uname else "Не указан"
                status_str = status_map.get(status, status or "Новая заявка")
                writer.writerow([lid, uid, fname, uname_str, status_str, paid_amount or 0, tx_id or "", msg, dt])
        return filepath
    except Exception as e:
        print(f"❌ Ошибка экспорта в CSV: {e}")
        return None
