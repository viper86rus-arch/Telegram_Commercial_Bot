#!/usr/bin/env python3
"""
🤖 Демонстрационный Telegram-бот: "IT-Студия под ключ" (Release v2.1)
---------------------------------------------------------------------
Архитектура:
- config.py        : Безопасные переменные окружения (.env)
- database.py      : SQLite CRM (leads.db), аналитика и экспорт в Excel/CSV
- pdf_generator.py : Автоматическая генерация коммерческих предложений (PDF)
- ai_assistant.py  : Умный ИИ-консультант для ответов на вопросы клиентов
- demo_bot.py      : Диспетчер инлайн-меню, интерактивный квиз, карточки кейсов
"""

import json
import os
import time
import urllib.error
import urllib.request

import ai_assistant
from config import ADMIN_CHAT_ID, API_BASE, BOT_TOKEN
import database
import pdf_generator


# ---------------------------------------------------------
# СЕТЕВОЙ СЛОЙ (TELEGRAM BOT API)
# ---------------------------------------------------------

def telegram_api(method, data=None):
    """Отправка JSON-запросов к Telegram Bot API."""
    url = f"{API_BASE}/{method}"
    headers = {"Content-Type": "application/json"}
    payload = json.dumps(data).encode("utf-8") if data else None

    req = urllib.request.Request(url, data=payload, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8")
        print(f"❌ Ошибка Telegram API ({e.code}): {err}")
        return None
    except Exception as e:
        print(f"❌ Сетевая ошибка: {e}")
        return None


def send_message(chat_id, text, reply_markup=None):
    """Отправка форматированного HTML-сообщения с клавиатурой."""
    data = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    if reply_markup:
        data["reply_markup"] = reply_markup
    return telegram_api("sendMessage", data)


def send_document(chat_id, file_path, caption=""):
    """Отправка файлов (PDF/CSV/Excel) клиенту или администратору."""
    url = f"{API_BASE}/sendDocument"
    boundary = "----WebKitFormBoundary" + os.urandom(16).hex()
    filename = os.path.basename(file_path)

    # Определение mime-type
    content_type = "application/pdf" if filename.endswith(".pdf") else "text/csv; charset=utf-8"

    try:
        with open(file_path, "rb") as f:
            file_bytes = f.read()

        parts = []
        parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"chat_id\"\r\n\r\n{chat_id}\r\n".encode("utf-8"))
        if caption:
            parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"caption\"\r\n\r\n{caption}\r\n".encode("utf-8"))
        parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"document\"; filename=\"{filename}\"\r\nContent-Type: {content_type}\r\n\r\n".encode("utf-8"))
        parts.append(file_bytes)
        parts.append(f"\r\n--{boundary}--\r\n".encode("utf-8"))

        body = b"".join(parts)
        req = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"}
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"❌ Ошибка отправки документа {filename}: {e}")
        return None


# ---------------------------------------------------------
# ГЛАВНЫЕ КЛАВИАТУРЫ
# ---------------------------------------------------------

def get_main_keyboard(is_admin=False):
    """Главное меню с кнопками навигации."""
    buttons = [
        [
            {"text": "🛠 Каталог услуг", "callback_data": "services"},
            {"text": "💰 Калькулятор", "callback_data": "calc_step1"}
        ],
        [
            {"text": "📁 Моё портфолио", "callback_data": "portfolio"},
            {"text": "📞 Контакты / Заказ", "callback_data": "contacts"}
        ]
    ]
    if is_admin:
        buttons.append([{"text": "👑 Панель администратора", "callback_data": "admin_panel"}])
    return {"inline_keyboard": buttons}


def get_admin_keyboard():
    """Клавиатура панели администратора."""
    return {
        "inline_keyboard": [
            [
                {"text": "📥 Выгрузить базу в Excel (CSV)", "callback_data": "admin_export"},
                {"text": "📋 Последние заявки", "callback_data": "admin_leads"}
            ],
            [
                {"text": "◀️ В клиентское меню", "callback_data": "menu"}
            ]
        ]
    }


# ---------------------------------------------------------
# ИНТЕРАКТИВНЫЙ КВИЗ-КАЛЬКУЛЯТОР (QUIZ)
# ---------------------------------------------------------

QUIZ_PRICES = {
    "types": {
        "bot": {"title": "🤖 Telegram-бот под ключ", "price": 10000, "days": 3},
        "parser": {"title": "🕷 Парсер сайтов / каталогов", "price": 8000, "days": 2},
        "script": {"title": "⚙️ Скрипт автоматизации", "price": 6000, "days": 1}
    },
    "db": {
        "yes": {"title": "Да (SQLite / PostgreSQL)", "price": 5000, "days": 1},
        "no": {"title": "Нет (без БД)", "price": 0, "days": 0}
    },
    "extra": {
        "pay": {"title": "💳 Онлайн-оплата (ЮKassa/Банк)", "price": 8000, "days": 1},
        "admin": {"title": "📊 Админ-панель и рассылки", "price": 7000, "days": 1},
        "all": {"title": "🚀 Оплата + Админка (Пакет)", "price": 13000, "days": 2},
        "none": {"title": "⏩ Без доп. модулей", "price": 0, "days": 0}
    }
}


def handle_quiz(chat_id, data):
    """Пошаговый квиз-калькулятор стоимости."""
    parts = data.split(":")
    step = parts[0]

    if step == "calc_step1":
        text = (
            "<b>💰 ИНТЕРАКТИВНЫЙ КАЛЬКУЛЯТОР (Шаг 1 из 3):</b>\n\n"
            "Выберите направление вашего проекта:"
        )
        kb = {
            "inline_keyboard": [
                [{"text": "🤖 Telegram-бот (от 10 000 ₽)", "callback_data": "calc_step2:bot"}],
                [{"text": "🕷 Парсер данных / WB / Ozon (от 8 000 ₽)", "callback_data": "calc_step2:parser"}],
                [{"text": "⚙️ Автоматизация / Скрипт (от 6 000 ₽)", "callback_data": "calc_step2:script"}],
                [{"text": "◀️ В главное меню", "callback_data": "menu"}]
            ]
        }
        send_message(chat_id, text, kb)

    elif step == "calc_step2":
        q_type = parts[1]
        t_info = QUIZ_PRICES["types"][q_type]
        text = (
            "<b>💰 ИНТЕРАКТИВНЫЙ КАЛЬКУЛЯТОР (Шаг 2 из 3):</b>\n\n"
            f"Выбрано: <b>{t_info['title']}</b>\n\n"
            "Требуется ли подключение базы данных для хранения пользователей, заказов или истории?"
        )
        kb = {
            "inline_keyboard": [
                [{"text": "🗄 Да, нужна база (+5 000 ₽)", "callback_data": f"calc_step3:{q_type}:yes"}],
                [{"text": "❌ Нет, база не нужна (0 ₽)", "callback_data": f"calc_step3:{q_type}:no"}],
                [{"text": "◀️ Назад", "callback_data": "calc_step1"}]
            ]
        }
        send_message(chat_id, text, kb)

    elif step == "calc_step3":
        q_type, q_db = parts[1], parts[2]
        text = (
            "<b>💰 ИНТЕРАКТИВНЫЙ КАЛЬКУЛЯТОР (Шаг 3 из 3):</b>\n\n"
            "Нужны ли дополнительные бизнес-модули?"
        )
        kb = {
            "inline_keyboard": [
                [{"text": "💳 Онлайн-оплата (+8 000 ₽)", "callback_data": f"calc_res:{q_type}:{q_db}:pay"}],
                [{"text": "📊 Админка / Рассылки (+7 000 ₽)", "callback_data": f"calc_res:{q_type}:{q_db}:admin"}],
                [{"text": "🚀 Всё вместе: Оплата + Админка (+13 000 ₽)", "callback_data": f"calc_res:{q_type}:{q_db}:all"}],
                [{"text": "⏩ Без доп. модулей (0 ₽)", "callback_data": f"calc_res:{q_type}:{q_db}:none"}],
                [{"text": "◀️ Назад", "callback_data": f"calc_step2:{q_type}"}]
            ]
        }
        send_message(chat_id, text, kb)

    elif step == "calc_res":
        q_type, q_db, q_extra = parts[1], parts[2], parts[3]
        t_info = QUIZ_PRICES["types"][q_type]
        db_info = QUIZ_PRICES["db"][q_db]
        ext_info = QUIZ_PRICES["extra"][q_extra]

        total_price = t_info["price"] + db_info["price"] + ext_info["price"]
        total_days = t_info["days"] + db_info["days"] + ext_info["days"]

        text = (
            "<b>🧾 ИТОГОВЫЙ РАСЧЁТ СМЕТЫ:</b>\n"
            "━━━━━━━━━━━━━━━━━━\n"
            f"📌 <b>Тип проекта:</b> {t_info['title']}\n"
            f"🗄 <b>База данных:</b> {db_info['title']}\n"
            f"⚙️ <b>Дополнения:</b> {ext_info['title']}\n\n"
            f"💰 <b>Стоимость:</b> <b>{total_price:,} ₽</b>\n"
            f"⏱ <b>Срок разработки:</b> <b>{total_days} дн.</b>\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "<i>Нажмите кнопку ниже, чтобы зафиксировать заказ и получить официальную смету в PDF:</i>"
        )
        kb = {
            "inline_keyboard": [
                [{"text": f"✅ Заказать смету ({total_price:,} ₽ + PDF)", "callback_data": f"calc_order:{q_type}:{q_db}:{q_extra}:{total_price}:{total_days}"}],
                [{"text": "🔄 Пересчитать заново", "callback_data": "calc_step1"}],
                [{"text": "◀️ Главное меню", "callback_data": "menu"}]
            ]
        }
        send_message(chat_id, text, kb)

    elif step == "calc_order":
        q_type, q_db, q_extra = parts[1], parts[2], parts[3]
        total_price, total_days = int(parts[4]), int(parts[5])
        t_info = QUIZ_PRICES["types"][q_type]
        db_info = QUIZ_PRICES["db"][q_db]
        ext_info = QUIZ_PRICES["extra"][q_extra]

        order_desc = (
            f"Смета: {t_info['title']} | БД: {db_info['title']} | Доп: {ext_info['title']} | "
            f"Сумма: {total_price} ₽"
        )
        return order_desc, total_price, total_days, t_info["title"], db_info["title"], ext_info["title"]

    return None, None, None, None, None, None


# ---------------------------------------------------------
# ОБРАБОТЧИК КНОПОК И КАРТОЧЕК ПОРТФОЛИО
# ---------------------------------------------------------

def handle_callback(chat_id, data, user_name, username):
    """Обработка инлайн-кнопок."""
    current_admin = database.get_setting("admin_chat_id", ADMIN_CHAT_ID)
    is_admin = (str(chat_id) == str(current_admin))

    if data == "menu":
        welcome = (
            f"Привет, <b>{user_name}</b>! 👋\n\n"
            "Я автоматический бот-визитка для демонстрации коммерческих возможностей IT-Студии.\n"
            "Рассчитайте смету в калькуляторе или выберите раздел ниже:"
        )
        send_message(chat_id, welcome, get_main_keyboard(is_admin))

    elif data == "services":
        text = (
            "<b>🛠 НАШИ УСЛУГИ:</b>\n\n"
            "1. <b>Telegram-боты под ключ</b> (магазины, онлайн-запись, оплата) — от 10 000 ₽\n"
            "2. <b>Парсинг сайтов и каталогов</b> (WB, Ozon, базы данных) — от 8 000 ₽\n"
            "3. <b>Автоматизация рутины</b> (скрипты, отчёты, интеграция CRM) — от 6 000 ₽\n"
            "4. <b>Локальные ИИ-ассистенты</b> под базу знаний компании — от 40 000 ₽"
        )
        send_message(chat_id, text, get_main_keyboard(is_admin))

    # Меню интерактивного портфолио
    elif data == "portfolio":
        text = (
            "<b>📁 МОЁ ПОРТФОЛИО (Интерактивные кейсы):</b>\n\n"
            "Выберите проект ниже, чтобы посмотреть стек технологий, архитектуру и результаты:"
        )
        portfolio_kb = {
            "inline_keyboard": [
                [{"text": "⚡ Кейс: Async TCP Port Scanner", "callback_data": "case_scanner"}],
                [{"text": "🕷 Кейс: Enterprise Web Scraper", "callback_data": "case_scraper"}],
                [{"text": "🤖 Кейс: Telegram Commercial Hub (v2.1)", "callback_data": "case_hub"}],
                [{"text": "🐙 Открыть GitHub профиль", "url": "https://github.com/viper86rus-arch"}],
                [{"text": "◀️ В главное меню", "callback_data": "menu"}]
            ]
        }
        send_message(chat_id, text, portfolio_kb)

    # Карточка кейса 1: Сканер
    elif data == "case_scanner":
        text = (
            "⚡ <b>КЕЙС: Async TCP Port Scanner</b>\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "🎯 <b>Задача:</b> Высокоскоростное сканирование портов и аудит сетевой безопасности.\n"
            "🛠 <b>Стек технологий:</b> Python 3, asyncio, raw sockets, non-blocking I/O.\n"
            "🚀 <b>Результат:</b> Сканирование 10 000 портов менее чем за 3 секунды.\n"
            "🔒 <b>Особенность:</b> Устойчивая обработка таймаутов, микропотребление RAM (<30MB).\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "👉 Исходный код открыт на GitHub:"
        )
        kb = {
            "inline_keyboard": [
                [{"text": "🐙 Смотреть код на GitHub", "url": "https://github.com/viper86rus-arch/Async_TCP_Scanner"}],
                [
                    {"text": "📁 Другие кейсы", "callback_data": "portfolio"},
                    {"text": "💰 Заказать", "callback_data": "calc_step1"}
                ],
                [{"text": "◀️ В главное меню", "callback_data": "menu"}]
            ]
        }
        send_message(chat_id, text, kb)

    # Карточка кейса 2: Парсер
    elif data == "case_scraper":
        text = (
            "🕷 <b>КЕЙС: Enterprise Web Scraper</b>\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "🎯 <b>Задача:</b> Промышленный сбор каталогов товаров с маркетплейсов (WB, Ozon).\n"
            "🛠 <b>Стек технологий:</b> Python 3, aiohttp / requests, ротация прокси, User-Agent pool.\n"
            "🚀 <b>Результат:</b> Сбор 100 000+ карточек товаров с ценами и фото без банов.\n"
            "💾 <b>Форматы выгрузки:</b> Excel (CSV с UTF-8 BOM), SQLite, JSON, PostgreSQL.\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "👉 Исходный код открыт на GitHub:"
        )
        kb = {
            "inline_keyboard": [
                [{"text": "🐙 Смотреть код на GitHub", "url": "https://github.com/viper86rus-arch/Enterprise_Web_Scraper"}],
                [
                    {"text": "📁 Другие кейсы", "callback_data": "portfolio"},
                    {"text": "💰 Рассчитать парсер", "callback_data": "calc_step2:parser"}
                ],
                [{"text": "◀️ В главное меню", "callback_data": "menu"}]
            ]
        }
        send_message(chat_id, text, kb)

    # Карточка кейса 3: Коммерческий хаб
    elif data == "case_hub":
        text = (
            "🤖 <b>КЕЙС: Telegram Commercial Hub (v2.1)</b>\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "🎯 <b>Задача:</b> Комплексная бот-платформа для продаж, приёма заказов и сбора лидов.\n"
            "🛠 <b>Стек:</b> Python 3, Telegram Bot API, SQLite CRM, Role-Based Access Control.\n"
            "📄 <b>Фичи:</b> Интерактивный квиз, автогенерация КП в PDF, выгрузка базы в Excel.\n"
            "📱 <b>Особенность:</b> Разработано и развёрнуто прямо на мобильной рабочей станции (Android).\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "👉 Исходный код на GitHub:"
        )
        kb = {
            "inline_keyboard": [
                [{"text": "🐙 Открыть GitHub профиль", "url": "https://github.com/viper86rus-arch"}],
                [
                    {"text": "📁 Другие кейсы", "callback_data": "portfolio"},
                    {"text": "💰 Рассчитать бота", "callback_data": "calc_step1"}
                ],
                [{"text": "◀️ В главное меню", "callback_data": "menu"}]
            ]
        }
        send_message(chat_id, text, kb)

    elif data == "contacts":
        text = (
            "<b>📞 СВЯЗАТЬСЯ СО МНОЙ / ЗАКАЗ:</b>\n\n"
            "Готов обсудить ваш проект и составить ТЗ прямо сейчас!\n\n"
            "🐙 <b>GitHub:</b> <a href=\"https://github.com/viper86rus-arch\">https://github.com/viper86rus-arch</a>\n\n"
            "💡 <i>Нажмите «✍️ Оставить заявку» или просто отправьте в чат вопрос/сообщение — наш ИИ-консультант моментально ответит, а Макс свяжется с вами!</i>"
        )
        contacts_kb = {
            "inline_keyboard": [
                [
                    {"text": "✍️ Оставить заявку", "callback_data": "leave_lead"},
                    {"text": "🐙 GitHub", "url": "https://github.com/viper86rus-arch"}
                ],
                [
                    {"text": "💰 Рассчитать смету", "callback_data": "calc_step1"},
                    {"text": "◀️ Главное меню", "callback_data": "menu"}
                ]
            ]
        }
        send_message(chat_id, text, contacts_kb)

    elif data == "leave_lead":
        text = (
            "<b>✍️ ОФОРМЛЕНИЕ ЗАЯВКИ:</b>\n\n"
            "Напишите прямо сюда в ответном сообщении:\n"
            "• Какая задача стоит (бот, парсер, скрипт)?\n"
            "• Ваши контакты (Telegram / Телефон / Email)\n\n"
            "<i>Заявка будет автоматически сохранена в базу данных SQLite (leads.db)!</i>"
        )
        send_message(chat_id, text, get_main_keyboard(is_admin))

    # Квиз-калькулятор
    elif data.startswith("calc_"):
        if data.startswith("calc_order:"):
            order_desc, total_price, total_days, t_name, db_name, ext_name = handle_quiz(chat_id, data)
            if order_desc:
                lead_id = database.save_lead(chat_id, username, user_name, order_desc)
                ok_msg = (
                    f"✅ <b>Заказ #{lead_id} успешно оформлен!</b>\n\n"
                    f"Предварительная смета зафиксирована на сумму <b>{total_price:,} ₽</b>.\n"
                    f"⏳ Генерирую для вас официальное коммерческое предложение в PDF..."
                )
                send_message(chat_id, ok_msg, get_main_keyboard(is_admin))

                # Генерация PDF коммерческого предложения
                pdf_path = pdf_generator.generate_proposal_pdf(
                    order_id=lead_id,
                    client_name=user_name,
                    project_type=t_name,
                    db_title=db_name,
                    extra_title=ext_name,
                    total_price=total_price,
                    total_days=total_days
                )

                # Отправка PDF клиенту
                if pdf_path and os.path.exists(pdf_path):
                    send_document(
                        chat_id,
                        pdf_path,
                        caption=f"📄 Коммерческое предложение к заказу #{lead_id} от IT-Студии"
                    )

                # Уведомление администратора
                if current_admin:
                    uname_display = f"@{username}" if username else "нет (только имя)"
                    admin_alert = (
                        f"🔔 <b>НОВЫЙ ЗАКАЗ ПО КАЛЬКУЛЯТОРУ #{lead_id}!</b>\n"
                        f"━━━━━━━━━━━━━━━━━━\n"
                        f"👤 <b>Клиент:</b> {user_name}\n"
                        f"📱 <b>Telegram:</b> {uname_display}\n"
                        f"🆔 <b>User ID:</b> <code>{chat_id}</code>\n\n"
                        f"📋 <b>Детали сметы:</b>\n"
                        f"{order_desc}\n"
                        f"💵 <b>Сумма к оплате:</b> {total_price:,} ₽ ({total_days} дн.)"
                    )
                    reply_kb = None
                    if username:
                        reply_kb = {
                            "inline_keyboard": [
                                [{"text": f"💬 Написать клиенту (@{username})", "url": f"https://t.me/{username}"}]
                            ]
                        }
                    send_message(current_admin, admin_alert, reply_kb)
                    # Отправляем копию PDF администратору
                    if pdf_path and os.path.exists(pdf_path):
                        send_document(
                            current_admin,
                            pdf_path,
                            caption=f"📄 Копия КП #{lead_id} для клиента {user_name}"
                        )
        else:
            handle_quiz(chat_id, data)

    # Админ-панель
    elif data == "admin_panel":
        if not is_admin:
            send_message(chat_id, "⛔ Доступ запрещён.", get_main_keyboard(False))
            return
        stats = database.get_stats()
        text = (
            "👑 <b>ПАНЕЛЬ УПРАВЛЕНИЯ АДМИНИСТРАТОРА:</b>\n"
            "━━━━━━━━━━━━━━━━━━\n"
            f"📊 <b>Всего заявок в базе:</b> {stats['total_leads']}\n"
            f"👥 <b>Уникальных заказчиков:</b> {stats['unique_clients']}\n"
            f"🆔 <b>Ваш Telegram ID:</b> <code>{chat_id}</code>\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "Выберите действие ниже:"
        )
        send_message(chat_id, text, get_admin_keyboard())

    elif data == "admin_export":
        if not is_admin:
            return
        csv_path = database.export_leads_to_csv()
        if csv_path and os.path.exists(csv_path):
            send_message(chat_id, "⏳ Формирую файл отчёта Excel (CSV)...")
            send_document(chat_id, csv_path, caption="📊 Полная выгрузка базы заявок (Excel/CSV)")
        else:
            send_message(chat_id, "❌ Ошибка формирования выгрузки.")

    elif data == "admin_leads":
        if not is_admin:
            return
        leads = database.get_latest_leads(5)
        if not leads:
            rep = "📭 База заявок пока пуста."
        else:
            rep = "<b>📋 ПОСЛЕДНИЕ ЗАЯВКИ ИЗ БД:</b>\n\n"
            for lid, fname, uname, msg_text, dt in leads:
                uname_str = f"@{uname}" if uname else "без юзернейма"
                rep += f"<b>Заявка #{lid}</b> от {fname} ({uname_str}):\n"
                rep += f"💬 <i>{msg_text}</i>\n"
                rep += f"🕒 <code>{dt}</code>\n\n"
        send_message(chat_id, rep, get_admin_keyboard())


# ---------------------------------------------------------
# ОСНОВНОЙ ЦИКЛ БОТА (SERVER RUNNER)
# ---------------------------------------------------------

def run_bot():
    print("=" * 60)
    print("🤖 TELEGRAM BOT SERVER ЗАПУЩЕН (v2.1 Full Suite)")
    print("=" * 60)

    database.init_db()

    if not BOT_TOKEN or BOT_TOKEN.startswith("YOUR_BOT"):
        print("\n⚠️ ВНИМАНИЕ: BOT_TOKEN не указан в файле .env!")
        return

    me = telegram_api("getMe")
    if not me or not me.get("ok"):
        print("❌ Не удалось подключиться к Telegram. Проверь токен и интернет!")
        return

    bot_username = me["result"]["username"]
    print(f"✅ Успешное подключение! Имя бота: @{bot_username}")
    print("Ожидание сообщений... (Нажми Ctrl+C или напиши /stop)\n")

    bot_start_time = time.time()
    offset = None

    while True:
        try:
            params = {"timeout": 20}
            if offset:
                params["offset"] = offset

            updates = telegram_api("getUpdates", params)
            if updates and updates.get("ok"):
                for item in updates["result"]:
                    offset = item["update_id"] + 1

                    # 1. Обработка текстовых сообщений
                    if "message" in item:
                        msg = item["message"]
                        chat_id = msg["chat"]["id"]
                        text = msg.get("text", "")
                        user_name = msg["from"].get("first_name", "Пользователь")
                        uname = msg["from"].get("username", "")

                        current_admin = database.get_setting("admin_chat_id", ADMIN_CHAT_ID)
                        is_admin = (str(chat_id) == str(current_admin))

                        print(f"📩 Сообщение от {user_name} (ID: {chat_id}): {text}")

                        # Приветственное сообщение строго по образцу пользователя
                        if text == "/start":
                            welcome = (
                                f"Привет, <b>{user_name}</b>! 👋\n\n"
                                "Я автоматический бот-визитка для демонстрации коммерческих возможностей IT-Студии.\n"
                                "Рассчитайте смету в калькуляторе или выберите раздел ниже:"
                            )
                            send_message(chat_id, welcome, get_main_keyboard(is_admin))

                        elif text == "/stop":
                            telegram_api("getUpdates", {"offset": item["update_id"] + 1, "limit": 1})
                            if msg.get("date", 0) < bot_start_time - 2:
                                print(f"⏩ Пропуск старой команды /stop из очереди.")
                                continue

                            if not is_admin:
                                send_message(chat_id, "⛔ Выключение бота доступно только администратору.", get_main_keyboard(False))
                            else:
                                send_message(chat_id, "🛑 Бот выключен по команде /stop.")
                                print(f"\n🛑 Бот остановлен администратором {user_name}.")
                                return

                        elif text == "/admin":
                            if not is_admin:
                                send_message(chat_id, "⛔ <b>Доступ запрещён!</b> У этого бота уже назначен администратор.", get_main_keyboard(False))
                                if current_admin:
                                    uname_str = f"@{uname}" if uname else user_name
                                    send_message(current_admin, f"⚠️ Попытка вызова /admin от {uname_str} (ID: <code>{chat_id}</code>)")
                            else:
                                send_message(chat_id, "👑 <b>Вы подтверждены как главный администратор.</b>", get_admin_keyboard())

                        elif text == "/leads":
                            if not is_admin:
                                send_message(chat_id, "⛔ Доступ только для администратора.", get_main_keyboard(False))
                            else:
                                leads = database.get_latest_leads(5)
                                if not leads:
                                    rep = "📭 База заявок пока пуста."
                                else:
                                    rep = "<b>📋 ПОСЛЕДНИЕ ЗАЯВКИ ИЗ БД:</b>\n\n"
                                    for lid, fname, l_uname, msg_text, dt in leads:
                                        l_uname_str = f"@{l_uname}" if l_uname else "без юзернейма"
                                        rep += f"<b>Заявка #{lid}</b> от {fname} ({l_uname_str}):\n"
                                        rep += f"💬 <i>{msg_text}</i>\n"
                                        rep += f"🕒 <code>{dt}</code>\n\n"
                                send_message(chat_id, rep, get_admin_keyboard())

                        else:
                            # 1. Сохраняем входящее сообщение как заявку в CRM
                            lead_id = database.save_lead(chat_id, uname, user_name, text)
                            print(f"💾 Заявка #{lead_id} от {user_name} сохранена в leads.db!")

                            # 2. Формируем экспертный ответ ИИ-консультанта клиенту
                            ai_reply = ai_assistant.get_expert_ai_response(text, user_name)
                            send_message(chat_id, ai_reply, get_main_keyboard(is_admin))

                            # 3. Мгновенный пуш администратору в личку
                            if current_admin:
                                uname_display = f"@{uname}" if uname else "нет (только имя)"
                                admin_alert = (
                                    f"🔔 <b>НОВАЯ ЗАЯВКА / ВОПРОС #{lead_id}!</b>\n"
                                    f"━━━━━━━━━━━━━━━━━━\n"
                                    f"👤 <b>Клиент:</b> {user_name}\n"
                                    f"📱 <b>Telegram:</b> {uname_display}\n"
                                    f"🆔 <b>User ID:</b> <code>{chat_id}</code>\n\n"
                                    f"📝 <b>Вопрос / Задача:</b>\n"
                                    f"«<i>{text}</i>»"
                                )
                                reply_kb = None
                                if uname:
                                    reply_kb = {
                                        "inline_keyboard": [
                                            [{"text": f"💬 Написать клиенту (@{uname})", "url": f"https://t.me/{uname}"}]
                                        ]
                                    }
                                send_message(current_admin, admin_alert, reply_kb)

                    # 2. Обработка нажатий на инлайн-кнопки
                    elif "callback_query" in item:
                        cb = item["callback_query"]
                        chat_id = cb["message"]["chat"]["id"]
                        cb_data = cb.get("data", "")
                        from_user = cb.get("from", {})
                        user_name = from_user.get("first_name", "Пользователь")
                        uname = from_user.get("username", "")

                        print(f"🔘 Кнопка от {user_name}: {cb_data}")
                        handle_callback(chat_id, cb_data, user_name, uname)

            time.sleep(1)

        except KeyboardInterrupt:
            print("\nБот остановлен пользователем.")
            break
        except Exception as e:
            print(f"⚠️ Ошибка в цикле: {e}")
            time.sleep(3)


if __name__ == "__main__":
    run_bot()
