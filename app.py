import asyncio
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext

import config
from db import DB
from keyboards import main_kb, machines_kb, machine_menu_kb, items_kb
from states import InvQty

def is_admin(user_id: int) -> bool:
    return user_id in config.ADMIN_IDS

def fmt_status(row) -> str:
    return (
        f"**{row['name']}**\n"
        f"🧰 Обслуживание: {row['last_service_date'] or '—'}\n"
        f"💧 Вода: {row['last_water_date'] or '—'}\n\n"
        f"📦 Склад (шт.):\n"
        f"• Стаканы: {row['cups']}\n"
        f"• Крышки: {row['lids']}\n"
        f"• Молоко: {row['milk']}\n"
        f"• Шоколад: {row['chocolate']}\n"
        f"• Кофе: {row['coffee']}\n"
    )

async def main():
    if not config.BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is empty")
    if not config.DATABASE_URL:
        raise RuntimeError("DATABASE_URL is empty")
    if not config.ADMIN_IDS:
        raise RuntimeError("ADMIN_IDS is empty (example: 12345,67890)")

    bot = Bot(token=config.BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    db = DB(config.DATABASE_URL)
    await db.connect()

    # Автоприменение схемы при старте (без ручного psql)
    schema_path = Path(__file__).with_name("schema.sql")
    await db.apply_schema(schema_path.read_text(encoding="utf-8"))

    # ======= /start =======
    @dp.message(F.text == "/start")
    async def start(m: Message):
        if not is_admin(m.from_user.id):
            await m.answer("❌ У вас нет доступа к этому боту.")
            return
        await m.answer("Меню кофейных точек:", reply_markup=main_kb())

    # ======= Общая блокировка не-админов на любые кнопки =======
    @dp.callback_query()
    async def block_non_admin_callbacks(c: CallbackQuery):
        if not is_admin(c.from_user.id):
            await c.answer("Нет доступа", show_alert=True)
            return
        # если админ — пропускаем дальше (через handler filters),
        # но aiogram 3 ловит первый подходящий.
        # Поэтому блокировку делаем через фильтры на остальных хэндлерах:
        await c.answer()  # нейтрально

    # ======= Навигация =======
    @dp.callback_query(F.data == "back_main")
    async def back_main(c: CallbackQuery):
        if not is_admin(c.from_user.id):
            await c.answer("Нет доступа", show_alert=True)
            return
        await c.message.edit_text("Меню кофейных точек:", reply_markup=main_kb())
        await c.answer()

    @dp.callback_query(F.data == "choose_machine")
    async def choose_machine(c: CallbackQuery):
        if not is_admin(c.from_user.id):
            await c.answer("Нет доступа", show_alert=True)
            return
        machines = await db.list_machines()
        await c.message.edit_text("Выбери точку:", reply_markup=machines_kb(machines))
        await c.answer()

    @dp.callback_query(F.data == "status_all")
    async def status_all(c: CallbackQuery):
        if not is_admin(c.from_user.id):
            await c.answer("Нет доступа", show_alert=True)
            return
        machines = await db.list_machines()
        texts = []
        for m in machines:
            row = await db.get_status(m["id"])
            texts.append(fmt_status(row))
        await c.message.edit_text("\n\n".join(texts), reply_markup=main_kb(), parse_mode="Markdown")
        await c.answer()

    @dp.callback_query(F.data.startswith("m:"))
    async def open_machine(c: CallbackQuery):
        if not is_admin(c.from_user.id):
            await c.answer("Нет доступа", show_alert=True)
            return
        machine_id = int(c.data.split(":")[1])
        row = await db.get_status(machine_id)
        await c.message.edit_text(fmt_status(row), reply_markup=machine_menu_kb(machine_id), parse_mode="Markdown")
        await c.answer()

    # ======= Даты "сегодня" =======
    @dp.callback_query(F.data.startswith("today_service:"))
    async def today_service(c: CallbackQuery):
        if not is_admin(c.from_user.id):
            await c.answer("Нет доступа", show_alert=True)
            return
        machine_id = int(c.data.split(":")[1])
        await db.set_today(machine_id, c.from_user.id, "SERVICE")
        row = await db.get_status(machine_id)
        await c.message.edit_text(fmt_status(row), reply_markup=machine_menu_kb(machine_id), parse_mode="Markdown")
        await c.answer("Обслуживание отмечено ✅")

    @dp.callback_query(F.data.startswith("today_water:"))
    async def today_water(c: CallbackQuery):
        if not is_admin(c.from_user.id):
            await c.answer("Нет доступа", show_alert=True)
            return
        machine_id = int(c.data.split(":")[1])
        await db.set_today(machine_id, c.from_user.id, "WATER")
        row = await db.get_status(machine_id)
        await c.message.edit_text(fmt_status(row), reply_markup=machine_menu_kb(machine_id), parse_mode="Markdown")
        await c.answer("Вода отмечена ✅")

    # ======= Склад =======
    @dp.callback_query(F.data.startswith("inv:"))
    async def inv_show(c: CallbackQuery):
        if not is_admin(c.from_user.id):
            await c.answer("Нет доступа", show_alert=True)
            return
        machine_id = int(c.data.split(":")[1])
        row = await db.get_status(machine_id)
        await c.message.edit_text(fmt_status(row), reply_markup=machine_menu_kb(machine_id), parse_mode="Markdown")
        await c.answer()

    @dp.callback_query(F.data.startswith("inv_add:"))
    async def inv_add(c: CallbackQuery):
        if not is_admin(c.from_user.id):
            await c.answer("Нет доступа", show_alert=True)
            return
        machine_id = int(c.data.split(":")[1])
        await c.message.edit_text("Что пополняем?", reply_markup=items_kb("add_item", machine_id))
        await c.answer()

    @dp.callback_query(F.data.startswith("inv_sub:"))
    async def inv_sub(c: CallbackQuery):
        if not is_admin(c.from_user.id):
            await c.answer("Нет доступа", show_alert=True)
            return
        machine_id = int(c.data.split(":")[1])
        await c.message.edit_text("Что списываем?", reply_markup=items_kb("sub_item", machine_id))
        await c.answer()

    @dp.callback_query(F.data.startswith(("add_item:", "sub_item:")))
    async def pick_item(c: CallbackQuery, state: FSMContext):
        if not is_admin(c.from_user.id):
            await c.answer("Нет доступа", show_alert=True)
            return
        mode, machine_id, item = c.data.split(":")
        await state.update_data(mode=mode, machine_id=int(machine_id), item=item)
        await state.set_state(InvQty.waiting_qty)
        await c.message.edit_text("Введи количество (целое число > 0):")
        await c.answer()

    @dp.message(InvQty.waiting_qty)
    async def set_qty(m: Message, state: FSMContext):
        if not is_admin(m.from_user.id):
            await m.answer("❌ Нет доступа.")
            await state.clear()
            return

        try:
            qty = int(m.text.strip())
            if qty <= 0:
                raise ValueError
        except Exception:
            await m.answer("Нужно целое число больше 0. Введи ещё раз:")
            return

        data = await state.get_data()
        action = "ADD" if data["mode"] == "add_item" else "SUB"
        ok = await db.change_inventory(data["machine_id"], m.from_user.id, action, data["item"], qty)
        await state.clear()

        if not ok:
            await m.answer("❌ Недостаточно на складе для списания.")
            return

        row = await db.get_status(data["machine_id"])
        await m.answer(fmt_status(row), reply_markup=machine_menu_kb(data["machine_id"]), parse_mode="Markdown")

    try:
        await dp.start_polling(bot)
    finally:
        await db.close()

if __name__ == "__main__":
    asyncio.run(main())
