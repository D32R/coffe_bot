from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from keyboards import main_kb

router = Router()

@router.message(F.text == "/start")
async def start(m: Message, db, config):

    if m.from_user.id not in config.ADMIN_IDS:
        await m.answer("❌ У вас нет доступа к этому боту.")
        return

    # регистрируем админа в базе
    await db.ensure_user(m.from_user.id, m.from_user.username, "admin")

    await m.answer("✅ Доступ разрешён.\n\nМеню кофейных точек:", reply_markup=main_kb())
