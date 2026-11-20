from aiogram import Router

from . import admin, common, driver, passenger, offers


def setup_routers() -> Router:
    root = Router()
    # common birinchi: /start va "Bekor qilish" har qanday holatda ishlashi uchun
    root.include_router(common.router)
    root.include_router(admin.router)
    root.include_router(driver.router)
    root.include_router(passenger.router)
    root.include_router(offers.router)
    return root
