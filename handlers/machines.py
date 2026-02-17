from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from keyboards import machines_kb, machine_menu_kb, items_kb
from states import InvQty

router = Router()

def fmt_status(row):
    # row: name, dates, inventory
    return (
        f"**{row['name']}**\n"
        f"🧰 Обслуживание: {row['last_service_date'] or '—'}\n"
        f"💧 Вода: {row['last_water_date'] or '—'}\n\n"
        f"📦 Склад:\n"
        f"• Стаканы: {row['cups']}\n"
        f"• Крышки: {row['lids']}\n"
        f"• Молоко: {row['milk']}\n"
        f"• Шоколад: {row['chocolate']}\n"
        f"• Кофе: {row['coffee']}\n"
    )

@router.callback_query(F.data == "choose_machine")
async def choose_machine(c: CallbackQuery, db, user_role):
    machines = await db.list_machines()
    await c.message.edit_text("Выбери точку:", reply_markup=machines_kb(machines))
    await c.answer()

@router.callback_query(F.data.startswith("m:"))
async def open_machine(c: CallbackQuery, db):
    machine_id = int(c.data.split(":")[1])
    row = await db.get_status(machine_id)
    await c.message.edit_text(fmt_status(row), reply_markup=machine_menu_kb(machine_id), parse_mode="Markdown")
    await c.answer()

@router.callback_query(F.data == "status_all")
async def status_all(c: CallbackQuery, db):
    machines = await db.list_machines()
    texts = []
    for m in machines:
        row = await db.get_status(m["id"])
        texts.append(fmt_status(row))
    await c.message.edit_text("\n\n".join(texts), reply_markup=machine_menu_kb(machines[0]["id"]) if machines else None, parse_mode="Markdown")
    await c.answer()

@router.callback_query(F.data.startswith("today_service:"))
async def today_service(c: CallbackQuery, db):
    machine_id = int(c.data.split(":")[1])
    await db.set_today(machine_id, c.from_user.id, "SERVICE")
    row = await db.get_status(machine_id)
    await c.message.edit_text(fmt_status(row), reply_markup=machine_menu_kb(machine_id), parse_mode="Markdown")
    await c.answer("Отмечено: обслуживание сегодня ✅")

@router.callback_query(F.data.startswith("today_water:"))
async def today_water(c: CallbackQuery, db):
    machine_id = int(c.data.split(":")[1])
    await db.set_today(machine_id, c.from_user.id, "WATER")
    row = await db.get_status(machine_id)
    await c.message.edit_text(fmt_status(row), reply_markup=machine_menu_kb(machine_id), parse_mode="Markdown")
    await c.answer("Отмечено: вода сегодня ✅")

@router.callback_query(F.data.startswith("inv_add:"))
async def inv_add(c: CallbackQuery):
    machine_id = int(c.data.split(":")[1])
    await c.message.edit_text("Что пополняем?", reply_markup=items_kb("add_item", machine_id))
    await c.answer()

@router.callback_query(F.data.startswith("inv_sub:"))
async def inv_sub(c: CallbackQuery):
    machine_id = int(c.data.split(":")[1])
    await c.message.edit_text("Что списываем?", reply_markup=items_kb("sub_item", machine_id))
    await c.answer()

@router.callback_query(F.data.startswith(("add_item:", "sub_item:")))
async def pick_item(c: CallbackQuery, state: FSMContext):
    parts = c.data.split(":")
    mode = parts[0]  # add_item/sub_item
    machine_id = int(parts[1])
    item = parts[2]
    await state.update_data(mode=mode, machine_id=machine_id, item=item)
    await state.set_state(InvQty.waiting_qty)
    await c.message.edit_text("Введи количество (целое число > 0):")
    await c.answer()

@router.message(InvQty.waiting_qty)
async def set_qty(m: Message, state: FSMContext, db):
    try:
        qty = int(m.text.strip())
        if qty <= 0:
            raise ValueError
    except Exception:
        await m.answer("Нужно целое число больше 0. Попробуй ещё раз:")
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
