from aiogram import Router

from . import admin, common, driver, offers, passenger, voice


def setup_routers() -> Router:
    root = Router()
    # common birinchi: /start va "Bekor qilish" har qanday holatda ishlashi uchun
    root.include_router(common.router)
    root.include_router(admin.router)
    root.include_router(driver.router)
    root.include_router(passenger.router)
    root.include_router(offers.router)
    # voice oxirida: admin xabar tarqatishda ovozli xabar ham yuborishi mumkin
    root.include_router(voice.router)
    return root
