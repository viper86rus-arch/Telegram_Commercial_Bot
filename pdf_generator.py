#!/usr/bin/env python3
"""
📄 Модуль генерации PDF-смет и Коммерческих предложений (pdf_generator.py)
Формирует презентабельный A4 PDF-документ со сметой проекта на чистом Python
с использованием встроенного системного шрифта Roboto (Cyrillic Identity-H)
и пропорциональной таблицей метрик символов (/W).
"""

import os
import re
import struct
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROPOSALS_DIR = os.path.join(BASE_DIR, "proposals")


def find_system_font():
    """Поиск подходящего шрифта TrueType с поддержкой кириллицы."""
    candidates = [
        "/system/fonts/Roboto-Regular.ttf",
        "/system/fonts/DroidSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/TTF/DejaVuSans.ttf",
        "C:\\Windows\\Fonts\\arial.ttf"
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return "/system/fonts/Roboto-Regular.ttf"


FONT_PATH = find_system_font()

_CACHED_FONT_DATA = None
_CACHED_CMAP = None
_CACHED_W_STRING = None


def clean_text_for_pdf(text):
    """Удаляет эмодзи и спецсимволы, которых нет в текстовом шрифте (устраняет символы tofu)."""
    if not text:
        return ""
    emoji_pattern = re.compile(
        r'[\U00010000-\U0010ffff]'
        r'|[\u2600-\u27bf]'
        r'|[\ufe00-\ufe0f]',
        flags=re.UNICODE
    )
    cleaned = emoji_pattern.sub("", str(text))
    return cleaned.strip()


def get_font_cmap_and_widths():
    """Загрузка и кэширование шрифта, таблицы cmap и таблицы пропорциональных ширин (/W)."""
    global _CACHED_FONT_DATA, _CACHED_CMAP, _CACHED_W_STRING
    if _CACHED_FONT_DATA is not None:
        return _CACHED_FONT_DATA, _CACHED_CMAP, _CACHED_W_STRING

    with open(FONT_PATH, "rb") as f:
        font_data = f.read()

    num_tables = struct.unpack(">H", font_data[4:6])[0]
    head_offset = hhea_offset = hmtx_offset = cmap_offset = None

    for i in range(num_tables):
        tag, check, offset, length = struct.unpack(">4sIII", font_data[12 + i * 16 : 12 + (i + 1) * 16])
        if tag == b"head":
            head_offset = offset
        elif tag == b"hhea":
            hhea_offset = offset
        elif tag == b"hmtx":
            hmtx_offset = offset
        elif tag == b"cmap":
            cmap_offset = offset

    # 1. Извлечение cmap таблицы
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

    # 2. Извлечение пропорциональных ширин (/W)
    units_per_em = struct.unpack(">H", font_data[head_offset + 18 : head_offset + 20])[0]
    num_h_metrics = struct.unpack(">H", font_data[hhea_offset + 34 : hhea_offset + 36])[0]

    widths_list = []
    for gid in range(num_h_metrics):
        adv_w = struct.unpack(">H", font_data[hmtx_offset + gid * 4 : hmtx_offset + gid * 4 + 2])[0]
        # Масштабирование метрик к стандартной сетке PDF (1000 единиц)
        widths_list.append(str(round(adv_w * 1000 / units_per_em)))

    _CACHED_FONT_DATA = font_data
    _CACHED_CMAP = mapping
    _CACHED_W_STRING = " ".join(widths_list)

    return _CACHED_FONT_DATA, _CACHED_CMAP, _CACHED_W_STRING


def generate_proposal_pdf(order_id, client_name, project_type, db_title, extra_title, total_price, total_days):
    """
    Генерация презентабельного PDF коммерческого предложения с идеальной типографикой.
    """
    os.makedirs(PROPOSALS_DIR, exist_ok=True)
    pdf_filename = f"proposal_{order_id}.pdf"
    output_path = os.path.join(PROPOSALS_DIR, pdf_filename)

    font_data, cmap, w_array_str = get_font_cmap_and_widths()

    # Очищаем входные строки от эмодзи, чтобы не было символов tofu (квадратов)
    project_type = clean_text_for_pdf(project_type)
    db_title = clean_text_for_pdf(db_title)
    extra_title = clean_text_for_pdf(extra_title)
    client_name = clean_text_for_pdf(client_name)

    def enc(text):
        return "".join(f"{cmap.get(c, 0):04X}" for c in str(text))

    date_str = time.strftime("%d.%m.%Y")

    stream_ops = []

    # 1. Шапка (Синий баннер)
    stream_ops.append("0.08 0.20 0.38 rg 0 740 595 102 re f")
    stream_ops.append("1.0 1.0 1.0 rg")
    stream_ops.append(f"BT /F1 16 Tf 40 802 Td <{enc('IT-СТУДИЯ «ПОД КЛЮЧ» | КОММЕРЧЕСКОЕ ПРЕДЛОЖЕНИЕ')}> Tj ET")
    stream_ops.append(f"BT /F1 11 Tf 40 768 Td <{enc(f'Официальная смета к заказу №{order_id} от {date_str}')}> Tj ET")

    # 2. Карточка заказчика и реквизиты
    stream_ops.append("0.15 0.15 0.15 rg")
    stream_ops.append(f"BT /F1 11 Tf 40 705 Td <{enc(f'Заказчик: {client_name}')}> Tj ET")
    stream_ops.append(f"BT /F1 10.5 Tf 40 686 Td <{enc('Исполнитель: Макс (@V1PER86RUS) | Python Full-Stack Developer')}> Tj ET")
    stream_ops.append(f"BT /F1 10 Tf 40 668 Td <{enc('Портфолио проектов: https://github.com/viper86rus-arch')}> Tj ET")

    # Горизонтальная линия-разделитель
    stream_ops.append("0.82 0.84 0.88 RG 1.5 w 40 652 m 555 652 l S")

    # 3. Таблица спецификации
    # Заголовок таблицы
    stream_ops.append("0.93 0.95 0.98 rg 40 618 515 25 re f")
    stream_ops.append("0.08 0.20 0.38 rg")
    stream_ops.append(f"BT /F1 10.5 Tf 50 626 Td <{enc('НАИМЕНОВАНИЕ МОДУЛЯ / УСЛУГИ')}> Tj ET")
    stream_ops.append(f"BT /F1 10.5 Tf 240 626 Td <{enc('ВЫБРАННАЯ КОНФИГУРАЦИЯ / СТАТУС')}> Tj ET")

    # Строки таблицы
    y = 588
    rows = [
        ("• Основной функционал:", project_type),
        ("• Слой базы данных:", db_title),
        ("• Дополнительные опции:", extra_title),
        ("• Гарантийное обслуживание:", "12 месяцев техподдержки (0 ₽)"),
        ("• Развёртывание и запуск:", "Под ключ на сервере (Включено)")
    ]

    for label, val in rows:
        stream_ops.append("0.20 0.20 0.20 rg")
        stream_ops.append(f"BT /F1 10.5 Tf 50 {y} Td <{enc(label)}> Tj ET")
        stream_ops.append("0.10 0.10 0.10 rg")
        stream_ops.append(f"BT /F1 10.5 Tf 240 {y} Td <{enc(val)}> Tj ET")
        stream_ops.append(f"0.88 0.90 0.93 RG 0.8 w 40 {y-8} m 555 {y-8} l S")
        y -= 34

    # 4. Итоговый блок (Контур и акцент)
    stream_ops.append("0.96 0.98 1.0 rg 40 375 515 65 re f")
    stream_ops.append("0.12 0.40 0.80 RG 1.2 w 40 375 515 65 re S")
    stream_ops.append("0.08 0.20 0.38 rg")
    stream_ops.append(f"BT /F1 14 Tf 55 416 Td <{enc(f'ИТОГО К ОПЛАТЕ: {total_price:,} РУБЛЕЙ')}> Tj ET")
    stream_ops.append("0.25 0.25 0.25 rg")
    stream_ops.append(f"BT /F1 10.5 Tf 55 392 Td <{enc(f'Плановый срок сдачи проекта: {total_days} рабочих дня(ей)')}> Tj ET")

    # 5. Условия и гарантии
    stream_ops.append("0.35 0.35 0.35 rg")
    stream_ops.append(f"BT /F1 10 Tf 40 338 Td <{enc('УСЛОВИЯ СОТРУДНИЧЕСТВА И ГАРАНТИИ:')}> Tj ET")
    stream_ops.append(f"BT /F1 9 Tf 40 318 Td <{enc('• Чистый, документированный код на Python 3 с соблюдением стандартов PEP 8.')}> Tj ET")
    stream_ops.append(f"BT /F1 9 Tf 40 300 Td <{enc('• Полная передача всех исходных кодов и авторских прав заказчику.')}> Tj ET")
    stream_ops.append(f"BT /F1 9 Tf 40 282 Td <{enc('• Бесплатное исправление любых замечаний и сопровождение первого запуска.')}> Tj ET")

    stream_ops.append("0.20 0.20 0.20 rg")
    stream_ops.append(f"BT /F1 10 Tf 40 215 Td <{enc('Разработчик: Макс | Telegram: @V1PER86RUS')}> Tj ET")
    stream_ops.append("0.50 0.50 0.50 rg")
    stream_ops.append(f"BT /F1 9 Tf 40 196 Td <{enc('Смета зафиксирована ботом автоматически и готова к согласованию.')}> Tj ET")

    stream_data = "\n".join(stream_ops).encode("ascii")

    # Сборка валидного PDF 1.4 с CIDFont и точной таблицей ширин /W
    objects = []
    objects.append(b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")
    objects.append(b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n")
    objects.append(b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n")
    objects.append(f"4 0 obj\n<< /Length {len(stream_data)} >>\nstream\n".encode("ascii") + stream_data + b"\nendstream\nendobj\n")
    objects.append(b"5 0 obj\n<< /Type /Font /Subtype /Type0 /BaseFont /Roboto /Encoding /Identity-H /DescendantFonts [6 0 R] >>\nendobj\n")

    # Объект 6: CIDFontType2 с явной таблицей пропорциональных ширин /W
    cid_font_str = f"6 0 obj\n<< /Type /Font /Subtype /CIDFontType2 /BaseFont /Roboto /CIDSystemInfo << /Registry (Adobe) /Ordering (Identity) /Supplement 0 >> /FontDescriptor 7 0 R /CIDToGIDMap /Identity /DW 1000 /W [ 0 [ {w_array_str} ] ] >>\nendobj\n"
    objects.append(cid_font_str.encode("ascii"))

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
