from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def main_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Статус всех точек", callback_data="status_all")],
        [InlineKeyboardButton(text="☕ Выбрать точку", callback_data="choose_machine")],
    ])


def machines_kb(machines):
    rows = [[InlineKeyboardButton(text=m["name"], callback_data=f"m:{m['id']}")] for m in machines]
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def machine_menu_kb(machine_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📦 Склад", callback_data=f"inv:{machine_id}")],
        [InlineKeyboardButton(text="➕ Пополнить", callback_data=f"inv_add:{machine_id}"),
         InlineKeyboardButton(text="➖ Списать", callback_data=f"inv_sub:{machine_id}")],
        [InlineKeyboardButton(text="🧰 Обслуживание: сегодня", callback_data=f"today_service:{machine_id}")],
        [InlineKeyboardButton(text="💧 Вода: сегодня", callback_data=f"today_water:{machine_id}")],
        [InlineKeyboardButton(text="⬅️ К точкам", callback_data="choose_machine")]
    ])


def items_kb(prefix: str, machine_id: int):
    items = [
        ("Стаканы", "cups"),
        ("Крышки", "lids"),
        ("Молоко", "milk"),
        ("Шоколад", "chocolate"),
        ("Кофе", "coffee"),
        ("Раф", "raf"),
    ]
    rows = [[InlineKeyboardButton(text=t, callback_data=f"{prefix}:{machine_id}:{code}")] for t, code in items]
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=f"m:{machine_id}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
