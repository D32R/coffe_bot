import asyncio
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest

import config
from db import DB
from keyboards import main_kb, machines_kb, machine_menu_kb, items_kb
from states import InvQty


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


async def safe_edit(c: CallbackQuery, text: str, reply_markup=None):
    """Чтобы не падало на message is not modified"""
    try:
        await c.message.edit_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    except TelegramBadRequest as e:
        if "message is not modified" in str(e).lower():
            pass
        else:
            await c.message.answer(text, reply_markup=reply_markup, parse_mode="Markdown")


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

    # Накатываем схему при старте
    schema_path = Path(__file__).with_name("schema.sql")
    await db.apply_schema(schema_path.read_text(encoding="utf-8"))

    # ===== Middleware: доступ только админам =====
    @dp.update.outer_middleware()
    async def admin_only_middleware(handler, event, data):
        user = data.get("event_from_user")
        if user and user.id not in config.ADMIN_IDS:
            cq = getattr(event, "callback_query", None)
            if cq:
                await cq.answer("❌ Нет доступа", show_alert=True)
            else:
                msg = getattr(event, "message", None)
                if msg:
                    await msg.answer("❌ У вас нет доступа к этому боту.")
            return
        return await handler(event, data)

    # ===== /start =====
    @dp.message(F.text == "/start")
    async def start(m: Message):
        await m.answer("Меню кофейных точек:", reply_markup=main_kb())

    # ===== Главное меню =====
    @dp.callback_query(F.data == "back_main")
    async def back_main(c: CallbackQuery):
        await safe_edit(c, "Меню кофейных точек:", reply_markup=main_kb())
        await c.answer()

    # ===== Выбор точки =====
    @dp.callback_query(F.data == "choose_machine")
    async def choose_machine(c: CallbackQuery):
        machines = await db.list_machines()
        await safe_edit(c, "Выбери точку:", reply_markup=machines_kb(machines))
        await c.answer()

    # ===== Статус всех =====
    @dp.callback_query(F.data == "status_all")
    async def status_all(c: CallbackQuery):
        machines = await db.list_machines()
        texts = []
        for m in machines:
            row = await db.get_status(m["id"])
            texts.append(fmt_status(row))
        await safe_edit(c, "\n\n".join(texts), reply_markup=main_kb())
        await c.answer()

    # ===== Открыть точку =====
    @dp.callback_query(F.data.startswith("m:"))
    async def open_machine(c: CallbackQuery):
        machine_id = int(c.data.split(":")[1])
        row = await db.get_status(machine_id)
        await safe_edit(c, fmt_status(row), reply_markup=machine_menu_kb(machine_id))
        await c.answer()

    # ===== Показать склад/статус (кнопка "Склад") =====
    @dp.callback_query(F.data.startswith("inv:"))
    async def inv_show(c: CallbackQuery):
        machine_id = int(c.data.split(":")[1])
        row = await db.get_status(machine_id)
        await safe_edit(c, fmt_status(row), reply_markup=machine_menu_kb(machine_id))
        await c.answer()

    # ===== Даты "сегодня" =====
    @dp.callback_query(F.data.startswith("today_service:"))
    async def today_service(c: CallbackQuery):
        machine_id = int(c.data.split(":")[1])
        await db.set_today(machine_id, c.from_user.id, "SERVICE")
        row = await db.get_status(machine_id)
        await safe_edit(c, fmt_status(row), reply_markup=machine_menu_kb(machine_id))
        await c.answer("Обслуживание отмечено ✅")

    @dp.callback_query(F.data.startswith("today_water:"))
    async def today_water(c: CallbackQuery):
        machine_id = int(c.data.split(":")[1])
        await db.set_today(machine_id, c.from_user.id, "WATER")
        row = await db.get_status(machine_id)
        await safe_edit(c, fmt_status(row), reply_markup=machine_menu_kb(machine_id))
        await c.answer("Вода отмечена ✅")

    # ===== Пополнить/списать =====
    @dp.callback_query(F.data.startswith("inv_add:"))
    async def inv_add(c: CallbackQuery):
        machine_id = int(c.data.split(":")[1])
        await safe_edit(c, "Что пополняем?", reply_markup=items_kb("add_item", machine_id))
        await c.answer()

    @dp.callback_query(F.data.startswith("inv_sub:"))
    async def inv_sub(c: CallbackQuery):
        machine_id = int(c.data.split(":")[1])
        await safe_edit(c, "Что списываем?", reply_markup=items_kb("sub_item", machine_id))
        await c.answer()

    @dp.callback_query(F.data.startswith(("add_item:", "sub_item:")))
    async def pick_item(c: CallbackQuery, state: FSMContext):
        mode, machine_id, item = c.data.split(":")
        await state.update_data(mode=mode, machine_id=int(machine_id), item=item)
        await state.set_state(InvQty.waiting_qty)
        await safe_edit(c, "Введи количество (целое число > 0):")
        await c.answer()

    @dp.message(InvQty.waiting_qty)
    async def set_qty(m: Message, state: FSMContext):
        try:
            qty = int(m.text.strip())
            if qty <= 0:
                raise ValueError
        except Exception:
            await m.answer("Нужно целое число больше 0. Введи ещё раз:")
            return

        data = await state.get_data()
        action = "ADD" if data["mode"] == "add_item" else "SUB"

        ok = await db.change_inventory(
            machine_id=data["machine_id"],
            by=m.from_user.id,
            action=action,
            item=data["item"],
            qty=qty
        )

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
