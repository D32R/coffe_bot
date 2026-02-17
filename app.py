import asyncio
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

import config
from db import DB
from handlers import start, machines

async def main():
    bot = Bot(token=config.BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    db = DB(config.DATABASE_URL)
    await db.connect()

    # простая инъекция зависимостей
    dp["db"] = db
    dp["config"] = config

    # хук для user_role (минимальный вариант)
    @dp.update.outer_middleware()
    async def role_middleware(handler, event, data):
        dbx: DB = data["dispatcher"]["db"]
        user = data.get("event_from_user")
        if user:
            data["user_role"] = await dbx.get_user_role(user.id)
        return await handler(event, data)

    dp.include_router(start.router)
    dp.include_router(machines.router)

    try:
        await dp.start_polling(bot, db=db, config=config)
    finally:
        await db.close()

if __name__ == "__main__":
    asyncio.run(main())
