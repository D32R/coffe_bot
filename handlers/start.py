from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from keyboards import main_kb

router = Router()

@router.message(F.text == "/start")
async def start(m: Message, db, config):
    # авто-регистрация: админы из ADMIN_IDS -> admin, остальные -> staff (или запретить и добавлять только админом)
    role = "admin" if m.from_user.id in config.ADMIN_IDS else "staff"
    await db.ensure_user(m.from_user.id, m.from_user.username, role)
    await m.answer("Меню кофейных точек:", reply_markup=main_kb())

@router.callback_query(F.data == "back_main")
async def back_main(c: CallbackQuery):
    await c.message.edit_text("Меню кофейных точек:", reply_markup=main_kb())
    await c.answer()
