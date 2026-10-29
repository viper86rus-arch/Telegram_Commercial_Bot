# 🤖 Enterprise Commercial Telegram Bot & Sales Platform

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue.svg?logo=python&logoColor=white)](https://www.python.org/)
[![Telegram Bot API](https://img.shields.io/badge/Telegram_Bot_API-v7.0%2B-2CA5E0.svg?logo=telegram&logoColor=white)](https://core.telegram.org/bots/api)
[![PDF Engine](https://img.shields.io/badge/PDF_Engine-Pure_Python-45ba4b.svg?logo=adobeacrobatreader&logoColor=white)](https://github.com/viper86rus-arch/Telegram_Commercial_Bot)
[![SQLite3](https://img.shields.io/badge/SQLite3-Micro_CRM-003B57.svg?logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![Dependencies](https://img.shields.io/badge/Dependencies-Zero_Pip-orange.svg)](https://github.com/viper86rus-arch/Telegram_Commercial_Bot)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> **Промышленная платформа коммерческого Telegram-бота для продаж, лидогенерации и автоматизации клиентского сервиса.**  
> Поддерживает автоматический 3-шаговый расчёт смет в интерактивном диалоге, генерацию официальных A4 PDF коммерческих предложений на лету и встроенную микро-CRM на SQLite3. Разработан на **чистом Python Standard Library** без внешних зависимостей (`pip install` не требуется).

---

## 🌟 Ключевые возможности

1. **📄 Автоматическая генерация смет в PDF (Commercial Proposal):**
   - Формирование официального A4 PDF коммерческого предложения со сметой, таблицей цен, реквизитами и гарантийными условиями.
   - Чистая векторная отрисовка кириллицы на базе встроенного системного шрифта Roboto.
   - Моментальная отправка PDF-файла клиенту и администратору сразу после завершения квиза.

2. **🧠 Умный ИИ-консультант (AI Sales Assistant):**
   - Анализирует вопросы клиентов по парсингу, маркетплейсам (WB, Ozon), ботам и базам данных.
   - Гибридный режим: поддержка прямого онлайн-запроса через **Google Gemini API** (при наличии ключа в `.env`) либо мгновенный ответ через встроенную экспертную базу знаний IT-Студии.

3. **📁 Интерактивные карточки кейсов в портфолио:**
   - Полноценные карточки реализованных проектов:
     - ⚡ **Async TCP Port Scanner** (asyncio, 10 000 портов за 3 сек).
     - 🕷 **Enterprise Web Scraper** (прокси, антибан, сбор 100k+ товаров).
     - 🤖 **Telegram Commercial Hub** (микро-CRM, квиз, экспорт в Excel/PDF).
   - Прямые ссылки на исходный код в GitHub-репозиториях.

4. **💰 Интерактивный квиз-калькулятор сметы (Inline Stepper):**
   - 3-шаговый расчёт стоимости проекта прямо в диалоге (тип проекта, база данных, онлайн-оплата, админка).
   - Динамический расчёт бюджета и сроков в реальном времени.

5. **🗄 Встроенная микро-CRM на SQLite3:**
   - Автоматический сбор и каталогизация входящих заявок и лидов.
   - Мгновенные push-уведомления администратору в Telegram с кнопкой быстрого ответа `[💬 Написать клиенту (@username)]`.

6. **📊 Экспорт базы заявок в Excel (CSV):**
   - Выгрузка всей базы лидов файлом `.csv` прямо в чат Telegram одной кнопкой из админ-панели.
   - Кодировка `UTF-8 с BOM (utf-8-sig)` для идеального открытия в Excel на Windows, Mac и Android без кракозябр.

7. **🛡 Безопасность (.env) и защита прав (RBAC):**
   - Защита административных команд (`/admin`, `/leads`, `/stop`, выгрузка данных) с привязкой к Telegram ID.
   - Вынос токенов и секретов в изолированный `.env` файл (защита от утечек на GitHub).

---

## 🏗 Архитектура проекта

```text
bots/
├── demo_bot.py        # Диспетчер событий Telegram, квиз и логика меню
├── ai_assistant.py    # Модуль гибридного ИИ-консультанта (Gemini + база знаний)
├── pdf_generator.py   # Генератор официальных смет в PDF (A4 PostScript/Cyrillic)
├── database.py        # Слой работы с SQLite3, CRM и генератор CSV-отчётов
├── config.py          # Парсер безопасных переменных окружения (.env)
├── .env.example       # Публичный шаблон переменных окружения
├── .gitignore         # Исключение секретов, баз данных и отчётов из Git
└── README.md          # Документация проекта
```

---

## 🚀 Быстрый старт

### 1. Клонирование репозитория
```bash
git clone https://github.com/viper86rus-arch/Telegram_Commercial_Bot.git
cd Telegram_Commercial_Bot
```

### 2. Настройка конфигурации
Скопируйте шаблон `.env.example` в `.env`:
```bash
cp .env.example .env
```
Откройте файл `.env` и впишите ваш токен от `@BotFather`:
```ini
BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
ADMIN_CHAT_ID=123456789
DB_PATH=leads.db
# GEMINI_API_KEY=your_key_here (опционально для онлайн-ИИ)
```

### 3. Запуск бота
Сторонние библиотеки (`pip`) **не требуются** — бот работает сразу на любом стандартном Python 3.9+:
```bash
python demo_bot.py
```

---

## 👨‍💻 Автор и контакты

* **Разработчик:** Макс ([@V1PER86RUS](https://t.me/V1PER86RUS))
* **GitHub:** [viper86rus-arch](https://github.com/viper86rus-arch)
* **Специализация:** Разработка Telegram-ботов, асинхронные парсеры данных (Web Scraping), автоматизация бизнес-процессов на Python.

---

## 📄 Лицензия
Проект распространяется под свободной лицензией [MIT](LICENSE).
