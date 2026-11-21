from aiogram import F, Router

from . import admin, common, driver, group, handover, offers, passenger, voice


def setup_routers() -> Router:
    root = Router()

    # Shaxsiy chat: bot bilan suhbat
    private = Router(name="private")
    private.message.filter(F.chat.type == "private")
    # common birinchi: /start va "Bekor qilish" har qanday holatda ishlashi uchun
    private.include_router(common.router)
    private.include_router(admin.router)
    private.include_router(driver.router)
    private.include_router(passenger.router)
    private.include_router(handover.router)
    private.include_router(offers.router)
    # voice oxirida: admin xabar tarqatishda ovozli xabar ham yuborishi mumkin
    private.include_router(voice.router)

    root.include_router(private)
    # Guruhlar: bot faqat o'qiydi, hech narsa yozmaydi
    root.include_router(group.router)
    return root
