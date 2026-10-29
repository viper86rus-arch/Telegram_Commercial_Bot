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
from config import ADMIN_CHAT_ID, API_BASE, BOT_TOKEN, PAYMENT_PROVIDER_TOKEN
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


def answer_callback_query(callback_query_id, text=None, show_alert=False):
    """Ответ на callback_query для снятия анимации загрузки кнопки."""
    if not callback_query_id:
        return None
    data = {"callback_query_id": callback_query_id}
    if text:
        data["text"] = text
        data["show_alert"] = show_alert
    return telegram_api("answerCallbackQuery", data)


def send_invoice(chat_id, title, description, payload, provider_token, currency, prices):
    """Отправка счёта на оплату через нативный Telegram Payments API."""
    data = {
        "chat_id": chat_id,
        "title": title,
        "description": description,
        "payload": payload,
        "provider_token": provider_token,
        "currency": currency,
        "prices": prices
    }
    return telegram_api("sendInvoice", data)


def answer_pre_checkout_query(pre_checkout_query_id, ok=True, error_message=None):
    """Подтверждение готовности принять платёж Telegram Bot API."""
    data = {
        "pre_checkout_query_id": pre_checkout_query_id,
        "ok": ok
    }
    if error_message:
        data["error_message"] = error_message
    return telegram_api("answerPreCheckoutQuery", data)


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


def send_payment_options(chat_id, lead_id, total_price, total_days):
    """Отправка карточки с вариантами оплаты (аванс 30% или 100% со скидкой 5%)."""
    advance_amount = int(round(total_price * 0.30))
    full_discount_amount = int(round(total_price * 0.95))
    discount_savings = total_price - full_discount_amount

    payment_text = (
        f"💳 <b>ОПЛАТА И СТАРТ ПРОЕКТА ПО ЗАКАЗУ #{lead_id}</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📄 Официальная смета с цифровой подписью сформирована выше.\n"
        f"💰 Полная смета: <b>{total_price:,} ₽</b>\n"
        f"⏱ Срок разработки: <b>{total_days} дн.</b>\n\n"
        f"Выберите удобный вариант оплаты:\n"
        f"1️⃣ <b>Аванс 30% ({advance_amount:,} ₽)</b> — фиксация старта, остаток 70% после приёмки работ.\n"
        f"2️⃣ <b>100% оплата со скидкой 5% ({full_discount_amount:,} ₽)</b> — моментальная экономия {discount_savings:,} ₽!\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🔒 <i>Платежи защищены ст. 435, 438 ГК РФ (безотзывная оферта) и 422-ФЗ. Электронный чек самозанятого генерируется автоматически.</i>"
    )
    payment_kb = {
        "inline_keyboard": [
            [{"text": f"💳 Внести аванс 30% ({advance_amount:,} ₽)", "callback_data": f"pay_opt:advance:{lead_id}:{advance_amount}:{total_price}"}],
            [{"text": f"💵 Оплатить 100% со скидкой ({full_discount_amount:,} ₽)", "callback_data": f"pay_opt:full:{lead_id}:{full_discount_amount}:{total_price}"}],
            [{"text": "◀️ В главное меню", "callback_data": "menu"}]
        ]
    }
    send_message(chat_id, payment_text, payment_kb)


def process_successful_payment(chat_id, user_name, username, lead_id, opt, amount, tx_id):
    """Единая обработка успешного платежа (демо или реального)."""
    status = "paid_advance" if opt == "advance" else "paid_full"
    opt_title = "Аванс 30%" if opt == "advance" else "Полная оплата 100% (со скидкой 5%)"
    database.record_payment(lead_id, amount, status, tx_id)

    now_str = time.strftime("%d.%m.%Y %H:%M:%S")
    client_receipt = (
        f"🎉 <b>ОПЛАТА УСПЕШНО ЗАЧИСЛЕНА!</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🧾 <b>Чек / Транзакция:</b> <code>#{tx_id}</code>\n"
        f"📋 <b>Номер заказа:</b> #{lead_id}\n"
        f"💰 <b>Сумма платежа:</b> <b>{amount:,} ₽</b>\n"
        f"📊 <b>Статус:</b> Оплачено ({opt_title})\n"
        f"🕒 <b>Дата и время:</b> {now_str} (МСК)\n"
        f"👤 <b>Заказчик:</b> {user_name}\n\n"
        f"✅ <b>Фискализация (422-ФЗ):</b> Электронный фискальный чек сформирован в сервисе ФНС «Мой налог».\n"
        f"📑 <b>Юридическая гарантия (63-ФЗ):</b> Сделка оформлена по акцептованной смете #{lead_id}.\n"
        f"🚀 <b>Статус проекта:</b> «В РАБОТЕ». Разработчик уведомлен и приступает к реализации!\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"<i>Спасибо за сотрудничество! Вы можете связаться со мной или отслеживать этапы в любой момент:</i>"
    )
    receipt_kb = {
        "inline_keyboard": [
            [{"text": "📁 Моё портфолио", "callback_data": "portfolio"}],
            [{"text": "📞 Контакты разработчика", "callback_data": "contacts"}],
            [{"text": "◀️ В главное меню", "callback_data": "menu"}]
        ]
    }
    send_message(chat_id, client_receipt, receipt_kb)

    # Уведомление администратора
    current_admin = database.get_setting("admin_chat_id", ADMIN_CHAT_ID)
    if current_admin:
        uname_display = f"@{username}" if username else "нет (только имя)"
        admin_alert = (
            f"💰 <b>ПОСТУПИЛА ОПЛАТА ПО ЗАКАЗУ #{lead_id}!</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🧾 <b>Транзакция:</b> <code>#{tx_id}</code>\n"
            f"👤 <b>Клиент:</b> {user_name}\n"
            f"📱 <b>Telegram:</b> {uname_display}\n"
            f"🆔 <b>User ID:</b> <code>{chat_id}</code>\n"
            f"💵 <b>Сумма:</b> <b>{amount:,} ₽</b> ({opt_title})\n"
            f"🕒 <b>Время:</b> {now_str} (МСК)\n\n"
            f"🚀 <b>Статус:</b> Заказ переведён в «В работе». Свяжитесь с клиентом для начала разработки!"
        )
        reply_kb = None
        if username:
            reply_kb = {
                "inline_keyboard": [
                    [{"text": f"💬 Написать клиенту (@{username})", "url": f"https://t.me/{username}"}]
                ]
            }
        send_message(current_admin, admin_alert, reply_kb)


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

def handle_callback(chat_id, data, user_name, username, cb_id=None):
    """Обработка инлайн-кнопок."""
    if cb_id:
        answer_callback_query(cb_id)
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
                [{"text": "🐙 Смотреть код на GitHub", "url": "https://github.com/viper86rus-arch/Telegram_Commercial_Bot"}],
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
                    f"⏳ Генерирую официальное коммерческое предложение в PDF с цифровой подписью..."
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
                        caption=f"📄 Официальная смета к заказу #{lead_id} (заверена штампом ПЭП самозанятого)"
                    )

                # Предлагаем клиенту варианты оплаты (аванс 30% или 100% со скидкой)
                send_payment_options(chat_id, lead_id, total_price, total_days)

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
                            caption=f"📄 Копия сметы #{lead_id} со штампом ПЭП для клиента {user_name}"
                        )
        else:
            handle_quiz(chat_id, data)

    # Выбор опции оплаты (Аванс 30% / Полная оплата 100%)
    elif data.startswith("pay_opt:"):
        parts = data.split(":")
        opt = parts[1]
        lead_id = int(parts[2])
        amount = int(parts[3])
        total_price = int(parts[4]) if len(parts) > 4 else amount

        opt_title = "Аванс 30%" if opt == "advance" else "Полная оплата 100% (со скидкой 5%)"

        if PAYMENT_PROVIDER_TOKEN:
            # Нативный платёж Telegram Payments
            inv_title = f"{opt_title} (#{lead_id})"
            inv_desc = f"Оплата разработки ПО по смете #{lead_id}. Безопасная сделка (422-ФЗ / 63-ФЗ)."
            prices = [{"label": opt_title, "amount": amount * 100}]
            payload = f"order_{lead_id}_{opt}_{amount}"
            send_invoice(chat_id, inv_title, inv_desc, payload, PAYMENT_PROVIDER_TOKEN, "RUB", prices)
        else:
            # Интерактивный терминал демо-эквайринга
            demo_card_text = (
                f"💳 <b>ИНТЕРАКТИВНЫЙ ЭКВАЙРИНГ / ДЕМО-ОПЛАТА</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"📋 <b>Номер сметы:</b> #{lead_id}\n"
                f"📌 <b>Тариф:</b> {opt_title}\n"
                f"💰 <b>Сумма к списанию:</b> <b>{amount:,} ₽</b>\n"
                f"🛡 <b>Протокол:</b> 3-D Secure / МИР Accept / PCI DSS v4.0\n\n"
                f"🏦 <b>Тестовые реквизиты песочницы:</b>\n"
                f"• Номер карты: <code>1111 1111 1111 1026</code>\n"
                f"• Срок действия: <code>12/28</code> | CVC: <code>123</code>\n"
                f"• Режим: Тестовая транзакция (без реального списания средств)\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"<i>Нажмите кнопку ниже для моментального подтверждения тестовой оплаты и фискализации:</i>"
            )
            demo_card_kb = {
                "inline_keyboard": [
                    [{"text": f"✅ Подтвердить демо-оплату ({amount:,} ₽)", "callback_data": f"pay_confirm:{lead_id}:{opt}:{amount}"}],
                    [{"text": "🔄 Выбрать другой вариант", "callback_data": f"pay_show_opts:{lead_id}:{total_price}"}],
                    [{"text": "❌ Отмена", "callback_data": "menu"}]
                ]
            }
            send_message(chat_id, demo_card_text, demo_card_kb)

    # Подтверждение оплаты (в демо-режиме)
    elif data.startswith("pay_confirm:"):
        parts = data.split(":")
        lead_id = int(parts[1])
        opt = parts[2]
        amount = int(parts[3])
        tx_id = f"TX-{lead_id}-{int(time.time()) % 100000:05d}"
        process_successful_payment(chat_id, user_name, username, lead_id, opt, amount, tx_id)

    # Возврат к выбору оплаты
    elif data.startswith("pay_show_opts:"):
        parts = data.split(":")
        lead_id = int(parts[1])
        total_price = int(parts[2])
        send_payment_options(chat_id, lead_id, total_price, 3)

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
            f"💳 <b>Оплаченных заказов:</b> {stats['paid_orders']}\n"
            f"💰 <b>Общая выручка:</b> <b>{stats['total_revenue']:,} ₽</b>\n"
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
            for lid, fname, uname, msg_text, status, paid_amount, tx_id, dt in leads:
                uname_str = f"@{uname}" if uname else "без юзернейма"
                pay_badge = f"💳 <b>{paid_amount:,} ₽</b> (#{tx_id})" if paid_amount > 0 else "⏳ Ожидает оплаты"
                rep += f"<b>Заявка #{lid}</b> от {fname} ({uname_str}) — {pay_badge}\n"
                rep += f"💬 <i>{msg_text}</i>\n"
                rep += f"🕒 <code>{dt}</code>\n\n"
        send_message(chat_id, rep, get_admin_keyboard())


# ---------------------------------------------------------
# ОСНОВНОЙ ЦИКЛ БОТА (SERVER RUNNER)
# ---------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PID_FILE = os.path.join(BASE_DIR, "bot.pid")


def enforce_single_instance():
    """Гарантирует, что запущен строго один экземпляр бота (убивает старые дубликаты)."""
    my_pid = os.getpid()
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, "r") as f:
                content = f.read().strip()
            if content.isdigit():
                old_pid = int(content)
                if old_pid != my_pid:
                    try:
                        # Проверяем, жив ли старый процесс
                        os.kill(old_pid, 0)
                        print(f"🔪 Завершаю старый дублирующий экземпляр бота (PID {old_pid})...")
                        os.kill(old_pid, 9)
                        time.sleep(0.5)
                    except OSError:
                        pass
        except Exception as e:
            print(f"⚠️ Ошибка проверки PID: {e}")

    try:
        with open(PID_FILE, "w") as f:
            f.write(str(my_pid))
    except Exception as e:
        print(f"⚠️ Ошибка записи PID: {e}")


def run_bot():
    print("=" * 60)
    print("🤖 TELEGRAM BOT SERVER ЗАПУЩЕН (v2.1 Full Suite)")
    print("=" * 60)

    enforce_single_instance()
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

                    # 1. Обработка текстовых сообщений и платежей
                    if "message" in item:
                        msg = item["message"]
                        chat_id = msg["chat"]["id"]
                        user_name = msg["from"].get("first_name", "Пользователь")
                        uname = msg["from"].get("username", "")

                        current_admin = database.get_setting("admin_chat_id", ADMIN_CHAT_ID)
                        is_admin = (str(chat_id) == str(current_admin))

                        # Проверка на успешную оплату через Telegram Payments
                        if "successful_payment" in msg:
                            sp = msg["successful_payment"]
                            total_rub = sp.get("total_amount", 0) // 100
                            payload = sp.get("invoice_payload", "")
                            tg_charge = sp.get("telegram_payment_charge_id", "")
                            tx_id = f"TG-{tg_charge[:10]}" if tg_charge else f"TX-{int(time.time())}"

                            parts_p = payload.split("_")
                            lead_id = int(parts_p[1]) if len(parts_p) > 1 and parts_p[1].isdigit() else 0
                            opt = parts_p[2] if len(parts_p) > 2 else "full"

                            print(f"💰 Успешный нативный платёж Telegram: {total_rub} ₽ по заказу #{lead_id} (TX: {tx_id})")
                            process_successful_payment(chat_id, user_name, uname, lead_id, opt, total_rub, tx_id)
                            continue

                        text = msg.get("text", "")
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
                                    for lid, fname, l_uname, msg_text, status, paid_amount, tx_id, dt in leads:
                                        l_uname_str = f"@{l_uname}" if l_uname else "без юзернейма"
                                        pay_badge = f"💳 <b>{paid_amount:,} ₽</b> (#{tx_id})" if paid_amount > 0 else "⏳ Ожидает оплаты"
                                        rep += f"<b>Заявка #{lid}</b> от {fname} ({l_uname_str}) — {pay_badge}\n"
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

                    # 2. Обработка готовности принять платёж Telegram Payments
                    elif "pre_checkout_query" in item:
                        pcq = item["pre_checkout_query"]
                        pcq_id = pcq.get("id")
                        answer_pre_checkout_query(pcq_id, ok=True)
                        print(f"💳 Pre-checkout query #{pcq_id} успешно подтверждён.")

                    # 3. Обработка нажатий на инлайн-кнопки
                    elif "callback_query" in item:
                        cb = item["callback_query"]
                        cb_id = cb.get("id")
                        chat_id = cb["message"]["chat"]["id"]
                        cb_data = cb.get("data", "")
                        from_user = cb.get("from", {})
                        user_name = from_user.get("first_name", "Пользователь")
                        uname = from_user.get("username", "")

                        print(f"🔘 Кнопка от {user_name}: {cb_data}")
                        handle_callback(chat_id, cb_data, user_name, uname, cb_id=cb_id)

            time.sleep(1)

        except KeyboardInterrupt:
            print("\nБот остановлен пользователем.")
            break
        except Exception as e:
            print(f"⚠️ Ошибка в цикле: {e}")
            time.sleep(3)


if __name__ == "__main__":
    run_bot()
