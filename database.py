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
    """Инициализация таблиц базы данных."""
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
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
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
            "INSERT INTO leads (user_id, username, full_name, message) VALUES (?, ?, ?, ?)",
            (user_id, username, full_name, message)
        )
        lead_id = cur.lastrowid
        conn.commit()
        conn.close()
        return lead_id
    except Exception as e:
        print(f"❌ Ошибка сохранения заявки: {e}")
        return None


def get_latest_leads(limit=5):
    """Получение последних N заявок."""
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT id, full_name, username, message, created_at FROM leads ORDER BY id DESC LIMIT ?",
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
        cur.execute("SELECT id, user_id, full_name, username, message, created_at FROM leads ORDER BY id ASC")
        rows = cur.fetchall()
        conn.close()
        return rows
    except Exception as e:
        print(f"❌ Ошибка чтения всех заявок: {e}")
        return []


def get_stats():
    """Получение статистики по базе данных."""
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*), COUNT(DISTINCT user_id) FROM leads")
        total_leads, unique_clients = cur.fetchone()
        conn.close()
        return {
            "total_leads": total_leads or 0,
            "unique_clients": unique_clients or 0
        }
    except Exception as e:
        print(f"❌ Ошибка получения статистики: {e}")
        return {"total_leads": 0, "unique_clients": 0}


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
    Экспорт всех заявок в файл CSV.
    Использует кодировку 'utf-8-sig' с BOM для корректного открытия в Excel на Windows/Android/Mac.
    """
    if filepath is None:
        filepath = os.path.join(os.path.dirname(os.path.abspath(DB_PATH)), "leads_report.csv")
    try:
        leads = get_all_leads()
        with open(filepath, mode="w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f, delimiter=";", quoting=csv.QUOTE_MINIMAL)
            # Заголовки таблицы
            writer.writerow([
                "ID Заявки",
                "User ID Telegram",
                "Имя клиента",
                "Telegram Ник",
                "Текст задачи / Смета",
                "Дата и время (МСК)"
            ])
            for row in leads:
                lid, uid, fname, uname, msg, dt = row
                uname_str = f"@{uname}" if uname else "Не указан"
                writer.writerow([lid, uid, fname, uname_str, msg, dt])
        return filepath
    except Exception as e:
        print(f"❌ Ошибка экспорта в CSV: {e}")
        return None
