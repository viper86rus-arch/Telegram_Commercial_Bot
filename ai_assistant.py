#!/usr/bin/env python3
"""
🧠 Модуль Умного ИИ-консультанта (ai_assistant.py)
Анализирует вопросы клиентов и формирует экспертные ответы:
- Онлайн-режим: через Gemini API (если указан GEMINI_API_KEY в .env)
- Офлайн-режим: встроенная экспертная база знаний IT-Студии
"""

import json
import os
import re
import urllib.error
import urllib.request

import config

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

SYSTEM_PROMPT = """
Ты — старший инженер и технический консультант IT-Студии разработчика Макса (@V1PER86RUS).
Ты консультируешь клиентов по разработке: Telegram-боты, парсеры данных (Wildberries, Ozon), автоматизация на Python.
Твой тон: дружелюбный, экспертный, конкретный. Без лишней воды.
Отвечай на русском языке.
В конце сообщения кратко напомни, что Макс уже получил уведомление и скоро выйдет на связь для точного расчёта.
"""


def _query_gemini_api(prompt):
    """Запрос к официальному Gemini REST API (при наличии ключа)."""
    if not GEMINI_API_KEY:
        return None

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": f"{SYSTEM_PROMPT}\n\nВопрос клиента: {prompt}"}
                ]
            }
        ]
    }
    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception as e:
        print(f"⚠️ Ошибка Gemini API: {e}")
        return None


def get_expert_ai_response(user_text, user_name="клиент"):
    """
    Формирование умного консультационного ответа клиенту.
    Автоматически выбирает Gemini API или встроенную экспертную базу знаний.
    """
    # 1. Попытка онлайн-ответа через Gemini API
    online_ans = _query_gemini_api(user_text)
    if online_ans:
        return online_ans

    # 2. Встроенная экспертная база знаний (Офлайн ИИ)
    text = user_text.lower()

    if any(k in text for k in ["парс", "скрейп", "wb", "wildberries", "ozon", "озон", "авито", "каталог", "цен", "сбор"]):
        return (
            f"Здравствуйте, <b>{user_name}</b>! 🕷\n\n"
            "По вопросу <b>парсинга данных</b>:\n"
            "• Мы разрабатываем промышленные асинхронные парсеры на <b>Python (asyncio / aiohttp)</b> с защитой от блокировок.\n"
            "• Поддерживается автоматическая ротация прокси, эмуляция браузерных заголовков и обход Cloudflare/капчи.\n"
            "• Выгрузка в любом удобном формате: <b>Excel (CSV с UTF-8 BOM)</b>, Google Таблицы, SQLite или PostgreSQL.\n"
            "• Скорость сбора: до 50 000–100 000 товаров в час.\n\n"
            "<i>💡 Макс уже получил уведомление о вашем запросе и скоро напишет для уточнения ссылки на источник!</i>"
        )

    elif any(k in text for k in ["бот", "bot", "магазин", "оплат", "юкасс", "заказ", "воронк", "crm"]):
        return (
            f"Здравствуйте, <b>{user_name}</b>! 🤖\n\n"
            "По вопросу <b>Telegram-бота</b>:\n"
            "• Создаём коммерческие боты с каталогом товаров, корзиной и онлайн-оплатой (ЮKassa, Robokassa, СБП, банки).\n"
            "• Встраиваем микро-CRM на <b>SQLite/Postgres</b>: все заявки моментально прилетают вам в личку.\n"
            "• Настраиваем админ-панель: статистика, рассылка уведомлений клиентам и выгрузка отчётов в Excel в 1 клик.\n\n"
            "<i>💡 Заявка зафиксирована в базе данных! Макс изучает задачу и напишет вам в ЛС в течение нескольких минут.</i>"
        )

    elif any(k in text for k in ["срок", "дн", "быстро", "скольк", "стоимост", "цен", "прайс", "бюджет"]):
        return (
            f"Здравствуйте, <b>{user_name}</b>! 💰\n\n"
            "По <b>срокам и ценам</b>:\n"
            "• Небольшие скрипты и парсеры: от <b>6 000 до 10 000 ₽</b> (срок: 1–3 дня).\n"
            "• Многофункциональные боты с оплатой и CRM: от <b>15 000 до 35 000 ₽</b> (срок: 3–5 дней).\n"
            "• Точную смету можно рассчитать прямо сейчас в меню кнопки <b>«💰 Калькулятор»</b>.\n"
            "• На все проекты предоставляется <b>12 месяцев бесплатной гарантии</b> на устранение любых замечаний.\n\n"
            "<i>💡 Макс уже получил оповещение и свяжется с вами для обсуждения деталей!</i>"
        )

    elif any(k in text for k in ["стек", "технолог", "python", "язык", "сервер", "vps"]):
        return (
            f"Здравствуйте, <b>{user_name}</b>! ⚙️\n\n"
            "Наш <b>технологический стек</b>:\n"
            "• <b>Язык:</b> Python 3.12–3.14 (чистая архитектура, PEP 8, строгая типизация).\n"
            "• <b>Сеть:</b> asyncio, aiohttp, Telegram Bot API (Long Polling / Webhooks).\n"
            "• <b>Базы данных:</b> SQLite, PostgreSQL, Redis.\n"
            "• <b>Инфраструктура:</b> Docker, systemd на Linux VPS, автозапуск 24/7.\n\n"
            "<i>💡 Заявка сохранена в базе. Разработчик скоро ответит вам лично!</i>"
        )

    else:
        return (
            f"Спасибо за обращение, <b>{user_name}</b>! 👋\n\n"
            "Ваш запрос успешно зарегистрирован в базе данных IT-Студии.\n"
            "Я — виртуальный ассистент, и я уже передал карточку вашей задачи разработчику Максу (@V1PER86RUS).\n\n"
            "Пока вы ожидаете, вы можете рассчитать ориентировочную стоимость и срок в меню <b>«💰 Калькулятор»</b> или ознакомиться с примерами работ в <b>«📁 Портфолио»</b>!"
        )
