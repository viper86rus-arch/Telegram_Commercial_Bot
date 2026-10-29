#!/usr/bin/env python3
"""
📄 Модуль генерации PDF-смет и Коммерческих предложений (pdf_generator.py)
Формирует презентабельный A4 PDF-документ со сметой проекта на чистом Python
с использованием встроенного системного шрифта Roboto (Cyrillic Identity-H).
"""

import os
import struct
import time

PROPOSALS_DIR = "/storage/emulated/0/Documents/Freelance/bots/proposals"
FONT_PATH = "/system/fonts/Roboto-Regular.ttf"

_CACHED_FONT_DATA = None
_CACHED_CMAP = None


def get_font_and_cmap():
    """Загрузка и кэширование TrueType шрифта и таблицы cmap."""
    global _CACHED_FONT_DATA, _CACHED_CMAP
    if _CACHED_FONT_DATA is not None:
        return _CACHED_FONT_DATA, _CACHED_CMAP

    with open(FONT_PATH, "rb") as f:
        font_data = f.read()

    num_tables = struct.unpack(">H", font_data[4:6])[0]
    cmap_offset = None
    for i in range(num_tables):
        tag, check, offset, length = struct.unpack(">4sIII", font_data[12 + i * 16 : 12 + (i + 1) * 16])
        if tag == b"cmap":
            cmap_offset = offset
            break

    version, num_subtables = struct.unpack(">HH", font_data[cmap_offset : cmap_offset + 4])
    sub_offset = None
    for i in range(num_subtables):
        p_id, e_id, offset = struct.unpack(">HHI", font_data[cmap_offset + 4 + i * 8 : cmap_offset + 4 + (i + 1) * 8])
        if (p_id == 3 and e_id == 1) or (p_id == 0 and e_id == 3):
            sub_offset = cmap_offset + offset
            break

    fmt = struct.unpack(">H", font_data[sub_offset : sub_offset + 2])[0]
    mapping = {}
    if fmt == 4:
        length, lang, seg_count_x2 = struct.unpack(">HHH", font_data[sub_offset + 2 : sub_offset + 8])
        seg_count = seg_count_x2 // 2
        end_codes = struct.unpack(f">{seg_count}H", font_data[sub_offset + 14 : sub_offset + 14 + seg_count * 2])
        start_codes = struct.unpack(f">{seg_count}H", font_data[sub_offset + 16 + seg_count * 2 : sub_offset + 16 + seg_count * 4])
        id_deltas = struct.unpack(f">{seg_count}h", font_data[sub_offset + 16 + seg_count * 4 : sub_offset + 16 + seg_count * 6])
        id_range_offsets_pos = sub_offset + 16 + seg_count * 6
        for i in range(seg_count - 1):
            sc, ec, delta = start_codes[i], end_codes[i], id_deltas[i]
            ro = struct.unpack(">H", font_data[id_range_offsets_pos + i * 2 : id_range_offsets_pos + (i + 1) * 2])[0]
            for cp in range(sc, ec + 1):
                if ro == 0:
                    mapping[chr(cp)] = (cp + delta) & 0xFFFF
                else:
                    g_pos = id_range_offsets_pos + i * 2 + ro + (cp - sc) * 2
                    gid = struct.unpack(">H", font_data[g_pos : g_pos + 2])[0]
                    if gid != 0:
                        mapping[chr(cp)] = (gid + delta) & 0xFFFF

    _CACHED_FONT_DATA = font_data
    _CACHED_CMAP = mapping
    return _CACHED_FONT_DATA, _CACHED_CMAP


def generate_proposal_pdf(order_id, client_name, project_type, db_title, extra_title, total_price, total_days):
    """
    Генерация полноценного PDF коммерческого предложения.
    Возвращает абсолютный путь к созданному файлу.
    """
    os.makedirs(PROPOSALS_DIR, exist_ok=True)
    pdf_filename = f"proposal_{order_id}.pdf"
    output_path = os.path.join(PROPOSALS_DIR, pdf_filename)

    font_data, cmap = get_font_and_cmap()

    def enc(text):
        return "".join(f"{cmap.get(c, 0):04X}" for c in str(text))

    date_str = time.strftime("%d.%m.%Y")

    # Рисование элементов страницы на PostScript/PDF операторах
    # MediaBox: [0 0 595 842] (A4)
    stream_ops = []

    # 1. Шапка (Синий баннер)
    stream_ops.append("0.08 0.20 0.38 rg 0 740 595 102 re f")  # Заливка прямоугольника
    stream_ops.append("1.0 1.0 1.0 rg")  # Белый цвет текста
    stream_ops.append(f"BT /F1 18 Tf 40 800 Td <{enc('IT-СТУДИЯ «ПОД КЛЮЧ» | КОММЕРЧЕСКОЕ ПРЕДЛОЖЕНИЕ')}> Tj ET")
    stream_ops.append(f"BT /F1 11 Tf 40 765 Td <{enc(f'Официальная смета к заказу №{order_id} от {date_str}')}> Tj ET")

    # 2. Карточка заказчика и реквизиты
    stream_ops.append("0.15 0.15 0.15 rg")  # Тёмно-серый текст
    stream_ops.append(f"BT /F1 12 Tf 40 705 Td <{enc(f'Заказчик: {client_name}')}> Tj ET")
    stream_ops.append(f"BT /F1 11 Tf 40 685 Td <{enc('Исполнитель: Макс (@V1PER86RUS) | Python Full-Stack Developer')}> Tj ET")
    stream_ops.append(f"BT /F1 10 Tf 40 668 Td <{enc('Портфолио: https://github.com/viper86rus-arch')}> Tj ET")

    # Горизонтальная линия-разделитель
    stream_ops.append("0.8 0.82 0.85 RG 2 w 40 650 m 555 650 l S")

    # 3. Таблица спецификации услуг
    # Заголовок таблицы
    stream_ops.append("0.94 0.96 0.98 rg 40 615 515 25 re f")  # Светлый фон таблицы
    stream_ops.append("0.08 0.20 0.38 rg")
    stream_ops.append(f"BT /F1 11 Tf 50 623 Td <{enc('СПЕЦИФИКАЦИЯ ТРЕБОВАНИЙ И МОДУЛЕЙ')}> Tj ET")
    stream_ops.append(f"BT /F1 11 Tf 450 623 Td <{enc('СТАТУС / СУММА')}> Tj ET")

    # Строки таблицы
    y = 585
    rows = [
        ("1. Базовый функционал", project_type),
        ("2. Слой базы данных", db_title),
        ("3. Дополнительные опции", extra_title),
        ("4. Гарантийное обслуживание", "12 месяцев техподдержки (0 ₽)"),
        ("5. Развёртывание и настройка", "Под ключ на сервере (Включено)")
    ]

    for label, val in rows:
        stream_ops.append("0.18 0.18 0.18 rg")
        stream_ops.append(f"BT /F1 11 Tf 50 {y} Td <{enc(label)}> Tj ET")
        stream_ops.append(f"BT /F1 10 Tf 220 {y} Td <{enc(val)}> Tj ET")
        stream_ops.append(f"0.88 0.90 0.92 RG 1 w 40 {y-8} m 555 {y-8} l S")
        y -= 35

    # 4. Итоговый блок
    stream_ops.append("0.95 0.97 1.0 rg 40 370 515 70 re f")
    stream_ops.append("0.1 0.4 0.8 RG 1.5 w 40 370 515 70 re S")
    stream_ops.append("0.08 0.20 0.38 rg")
    stream_ops.append(f"BT /F1 15 Tf 60 415 Td <{enc(f'ИТОГО К ОПЛАТЕ: {total_price:,} РУБЛЕЙ')}> Tj ET")
    stream_ops.append(f"BT /F1 11 Tf 60 388 Td <{enc(f'Плановый срок сдачи проекта: {total_days} рабочих дня(ей)')}> Tj ET")

    # 5. Гарантии и подпись
    stream_ops.append("0.35 0.35 0.35 rg")
    stream_ops.append(f"BT /F1 10 Tf 40 330 Td <{enc('УСЛОВИЯ И ГАРАНТИИ:')}> Tj ET")
    stream_ops.append(f"BT /F1 9 Tf 40 310 Td <{enc('• Чистый, документированный код на Python 3 с соблюдением стандартов PEP 8.')}> Tj ET")
    stream_ops.append(f"BT /F1 9 Tf 40 292 Td <{enc('• Полная передача всех исходных кодов и прав собственности заказчику.')}> Tj ET")
    stream_ops.append(f"BT /F1 9 Tf 40 274 Td <{enc('• Бесплатное устранение любых замечаний и сопровождение запуска.')}> Tj ET")

    stream_ops.append(f"BT /F1 10 Tf 40 200 Td <{enc(f'Разработчик: Макс | Контакт в Telegram: @V1PER86RUS')}> Tj ET")
    stream_ops.append(f"BT /F1 9 Tf 40 180 Td <{enc('Смета зафиксирована ботом автоматически и готова к подписанию.')}> Tj ET")

    stream_data = "\n".join(stream_ops).encode("ascii")

    # Формирование структуры PDF 1.4
    objects = []
    objects.append(b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")
    objects.append(b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n")
    objects.append(b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n")
    objects.append(f"4 0 obj\n<< /Length {len(stream_data)} >>\nstream\n".encode("ascii") + stream_data + b"\nendstream\nendobj\n")
    objects.append(b"5 0 obj\n<< /Type /Font /Subtype /Type0 /BaseFont /Roboto /Encoding /Identity-H /DescendantFonts [6 0 R] >>\nendobj\n")
    objects.append(b"6 0 obj\n<< /Type /Font /Subtype /CIDFontType2 /BaseFont /Roboto /CIDSystemInfo << /Registry (Adobe) /Ordering (Identity) /Supplement 0 >> /FontDescriptor 7 0 R /CIDToGIDMap /Identity >>\nendobj\n")
    objects.append(b"7 0 obj\n<< /Type /FontDescriptor /FontName /Roboto /Flags 32 /FontBBox [-500 -300 1200 1000] /ItalicAngle 0 /Ascent 928 /Descent -244 /CapHeight 714 /StemV 80 /FontFile2 8 0 R >>\nendobj\n")
    objects.append(f"8 0 obj\n<< /Length {len(font_data)} >>\nstream\n".encode("ascii") + font_data + b"\nendstream\nendobj\n")

    pdf = b"%PDF-1.4\n"
    offsets = [0]
    for obj in objects:
        offsets.append(len(pdf))
        pdf += obj

    xref_offset = len(pdf)
    pdf += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode("ascii")
    for off in offsets[1:]:
        pdf += f"{off:010d} 00000 n \n".encode("ascii")
    pdf += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF".encode("ascii")

    with open(output_path, "wb") as f:
        f.write(pdf)

    print(f"📄 Сгенерировано КП в PDF: {output_path} (Размер: {len(pdf)} байт)")
    return output_path
