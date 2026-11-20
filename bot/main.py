import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from .config import load_config
from .db import Database
from .handlers import setup_routers
from .middlewares import BanMiddleware
from .service import MatchService


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    config = load_config()

    db = Database(config.db_path)
    await db.connect()

    bot = Bot(config.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    svc = MatchService(bot, db, config)

    dp = Dispatcher(storage=MemoryStorage())
    dp["db"] = db
    dp["svc"] = svc
    dp["config"] = config
    dp.message.outer_middleware(BanMiddleware())
    dp.callback_query.outer_middleware(BanMiddleware())
    dp.include_router(setup_routers())
    if not config.admin_ids:
        logging.warning("ADMIN_IDS bo'sh — admin panel hech kimga ochilmaydi. /id bilan ID'ingizni bilib oling.")

    housekeeping = asyncio.create_task(svc.run_housekeeping_loop())
    try:
        await bot.delete_webhook(drop_pending_updates=False)
        await dp.start_polling(bot)
    finally:
        housekeeping.cancel()
        await db.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
