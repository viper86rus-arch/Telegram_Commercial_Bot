"""
==============================================================================
Тестовый комплекс: Telegram_Commercial_Bot Test Suite
==============================================================================
Автор: V1PER (viper86rus-arch)
GitHub: https://github.com/viper86rus-arch/Telegram_Commercial_Bot
Лицензия: MIT License (2026)
Назначение: Автоматизированное тестирование SQLite БД, генератора PDF-смет,
            экспорта отчетов в CSV (UTF-8 BOM) и экспертного ИИ-ассистента.
==============================================================================
"""

import csv
import os
import shutil
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

# Добавление корня проекта в sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

import config
import database
import pdf_generator
import ai_assistant


class TestTelegramCommercialBot(unittest.TestCase):
    """Модульные тесты для коммерческого Telegram-бота и вспомогательных модулей."""

    def setUp(self):
        """Создание изолированной временной среды для каждого теста."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_leads.db")
        self.proposals_dir = os.path.join(self.temp_dir, "proposals")
        os.makedirs(self.proposals_dir, exist_ok=True)

        # Перенаправление путей в config и модулях
        self.orig_db_path = config.DB_PATH
        self.orig_proposals_dir = pdf_generator.PROPOSALS_DIR

        config.DB_PATH = self.db_path
        database.DB_PATH = self.db_path
        pdf_generator.PROPOSALS_DIR = self.proposals_dir

        # Инициализация тестовой БД
        database.init_db()

    def tearDown(self):
        """Очистка временных файлов."""
        config.DB_PATH = self.orig_db_path
        database.DB_PATH = self.orig_db_path
        pdf_generator.PROPOSALS_DIR = self.orig_proposals_dir
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    # ==========================================================================
    # 1. ТЕСТИРОВАНИЕ БАЗЫ ДАННЫХ SQLITE
    # ==========================================================================

    def test_database_lifecycle_and_leads(self):
        """Проверка полного жизненного цикла заявки (сохранение, чтение, оплата, статистика)."""
        # Сохранение лида
        lead_id = database.save_lead(
            user_id=12345678,
            username="test_client",
            full_name="Тестовый Клиент",
            message="Разработка Telegram-бота под ключ с интеграцией эквайринга"
        )
        self.assertIsNotNone(lead_id)
        self.assertGreater(lead_id, 0)

        # Получение лида по ID
        lead = database.get_lead(lead_id)
        self.assertIsNotNone(lead)
        self.assertEqual(lead[0], lead_id)
        self.assertEqual(lead[1], 12345678)
        self.assertEqual(lead[2], "test_client")
        self.assertEqual(lead[3], "Тестовый Клиент")
        self.assertEqual(lead[5], "new")
        self.assertEqual(lead[6], 0)

        # Фиксация платежа
        pay_success = database.record_payment(
            lead_id=lead_id,
            amount=15000,
            status="paid_advance",
            tx_id="TX_TEST_998877"
        )
        self.assertTrue(pay_success)

        # Проверка обновленного статуса
        updated_lead = database.get_lead(lead_id)
        self.assertEqual(updated_lead[5], "paid_advance")
        self.assertEqual(updated_lead[6], 15000)
        self.assertEqual(updated_lead[7], "TX_TEST_998877")

        # Проверка бизнес-статистики
        stats = database.get_stats()
        self.assertEqual(stats["total_leads"], 1)
        self.assertEqual(stats["unique_clients"], 1)
        self.assertEqual(stats["total_revenue"], 15000)
        self.assertEqual(stats["paid_orders"], 1)

    def test_database_settings_key_value(self):
        """Проверка хранения и чтения настроек (key-value store)."""
        database.set_setting("support_channel", "@v1per_support")
        val = database.get_setting("support_channel")
        self.assertEqual(val, "@v1per_support")

        # Проверка дефолтного значения для несуществующего ключа
        unknown = database.get_setting("non_existent_key", default="fallback")
        self.assertEqual(unknown, "fallback")

    # ==========================================================================
    # 2. ТЕСТИРОВАНИЕ ЭКСПОРТА CSV
    # ==========================================================================

    def test_database_export_leads_to_csv(self):
        """Проверка экспорта заявок в CSV с кодировкой UTF-8 BOM и разделителем ';'."""
        database.save_lead(
            user_id=111,
            username="buyer1",
            full_name="Алексей",
            message="Парсер маркетплейса Wildberries"
        )
        database.save_lead(
            user_id=222,
            username="buyer2",
            full_name="Елена",
            message="Асинхронный сканер сети"
        )

        csv_path = os.path.join(self.temp_dir, "test_leads_export.csv")
        result_path = database.export_leads_to_csv(filepath=csv_path)

        self.assertIsNotNone(result_path)
        self.assertTrue(os.path.exists(csv_path))

        # Проверка сигнатуры UTF-8 BOM (0xEF, 0xBB, 0xBF)
        with open(csv_path, "rb") as bf:
            raw_header = bf.read(3)
            self.assertEqual(raw_header, b"\xef\xbb\xbf")

        # Проверка структуры и разделителя
        with open(csv_path, "r", encoding="utf-8-sig") as f:
            reader = csv.reader(f, delimiter=";")
            rows = list(reader)

        self.assertGreaterEqual(len(rows), 3)  # Шапка + 2 строки данных
        self.assertIn("ID Заявки", rows[0][0])
        self.assertIn("Telegram Ник", rows[0][3])
        self.assertEqual(rows[1][1], "111")
        self.assertEqual(rows[1][3], "'@buyer1")
        self.assertEqual(rows[2][1], "222")

    def test_csv_formula_injection_defense(self):
        """Проверка защиты от формульных инъекций Excel (CWE-1236)."""
        evil_name = "=cmd|' /C calc'!A0"
        sanitized = database._sanitize_csv_cell(evil_name)
        self.assertTrue(sanitized.startswith("'="))

    def test_pdf_path_traversal_defense(self):
        """Проверка защиты от выхода за пределы директории в PDF-генераторе (CWE-22)."""
        traversal_id = "test/../../escape"
        pdf_path = pdf_generator.generate_proposal_pdf(
            traversal_id, "Safe Client", "Type", "DB", "Extra", 10000, 2
        )
        self.assertTrue(os.path.abspath(pdf_path).startswith(os.path.abspath(pdf_generator.PROPOSALS_DIR)))
        if os.path.exists(pdf_path):
            os.remove(pdf_path)

    # ==========================================================================
    # 3. ТЕСТИРОВАНИЕ ГЕНЕРАТОРА PDF
    # ==========================================================================

    def test_clean_text_for_pdf(self):
        """Проверка очистки текста от эмодзи и спецсимволов для PDF."""
        raw = "🚀 Бот с автооплатой 💳 и интеграцией CRM! 🎯"
        cleaned = pdf_generator.clean_text_for_pdf(raw)
        self.assertNotIn("🚀", cleaned)
        self.assertNotIn("💳", cleaned)
        self.assertNotIn("🎯", cleaned)
        self.assertIn("Бот с автооплатой", cleaned)

    def test_generate_proposal_pdf(self):
        """Проверка генерации презентабельного PDF-документа коммерческого предложения."""
        pdf_path = pdf_generator.generate_proposal_pdf(
            order_id="TEST-101",
            client_name="ООО Вектор Развития",
            project_type="Telegram MiniApp + FastAPI Backend",
            db_title="PostgreSQL 16 Enterprise",
            extra_title="Эквайринг ЮKassa + СБП + Чек ФНС",
            total_price=45000,
            total_days="5-7"
        )

        self.assertTrue(os.path.exists(pdf_path))
        self.assertGreater(os.path.getsize(pdf_path), 1000)

        # Проверка заголовка и маркеров валидного PDF-документа
        with open(pdf_path, "rb") as f:
            data = f.read()

        self.assertTrue(data.startswith(b"%PDF-1.4"))
        self.assertTrue(data.rstrip().endswith(b"%%EOF"))
        self.assertIn(b"/Catalog", data)
        self.assertIn(b"/Pages", data)

    # ==========================================================================
    # 4. ТЕСТИРОВАНИЕ ИИ-КОНСУЛЬТАНТА (AI ASSISTANT)
    # ==========================================================================

    def test_ai_assistant_offline_expert_knowledge(self):
        """Проверка работы экспертной базы знаний ИИ-консультанта в офлайн-режиме."""
        # Запрос по маркетплейсу Wildberries
        wb_reply = ai_assistant.get_expert_ai_response("Парсите ли вы Wildberries?", "Дмитрий")
        self.assertIn("Wildberries", wb_reply)
        self.assertIn("Дмитрий", wb_reply)
        self.assertIn("СПП", wb_reply)

        # Запрос по Telegram-ботам
        tg_reply = ai_assistant.get_expert_ai_response("Сколько стоит Telegram бот с оплатой?", "Ольга")
        self.assertIn("Telegram", tg_reply)
        self.assertIn("Ольга", tg_reply)
        self.assertTrue(any(w in tg_reply for w in ["смет", "бюджет", "руб", "₽"]))


if __name__ == "__main__":
    unittest.main()
