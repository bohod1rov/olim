"""
🎤 Ovozli Xabarni Matnga O'giruvchi Telegram Bot
──────────────────────────────────────────────────
• Whisper (offline) → Google STT (online) zanjiri
• SQLite orqali sozlamalar va statistika
• Guruh va shaxsiy chat qo'llab-quvvatlanadi
"""

import os
import asyncio
import logging
import tempfile
import time

import static_ffmpeg
static_ffmpeg.add_paths()

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery

from config import Config
from utils import setup_logging, clean_temp_files, create_temp_dir, format_duration
from storage import (
    init_db,
    get_user_language, set_user_language,
    is_chat_enabled, set_chat_enabled,
    get_user_stats, get_global_stats,
    save_stat,
)
from transcriber import transcribe_audio
from keyboards import main_keyboard, settings_keyboard, language_keyboard, back_keyboard

# ── Sozlash ────────────────────────────────────────────────────────────────

setup_logging(Config.LOG_FILE)
logger = logging.getLogger(__name__)

bot = Bot(token=Config.BOT_TOKEN)
dp  = Dispatcher()

# ── Yordamchi matnlar ──────────────────────────────────────────────────────

WELCOME_TEXT = """
🎤 *Ovozli Xabarni Matnga O'giruvchi Bot*

Assalomu alaykum! Men ovozli xabarlarni matnga o'giraman.

*Imkoniyatlar:*
• Offline Whisper AI modeli (aniq, tez)
• O'zbek, Rus, Ingliz tillarini qo'llab-quvvatlash
• Guruh chatlarida ishlash
• Shaxsiy statistika

*Boshlash uchun* ovozli xabar yuboring 👇
"""

HELP_TEXT = """
❓ *Yordam*

*Qanday ishlatish:*
1. Ovozli xabar yuboring
2. Bot uni avtomatik matnga o'giradi
3. `/settings` orqali tilni sozlang

*Guruhlarda:*
• Meni guruhga admin sifatida qo'shing
• Barcha ovozli xabarlar avtomatik o'giriladi
• `/settings` orqali o'chirish mumkin

*Tillar:*
• 🤖 Avtomatik — til o'zi aniqlanadi (tavsiya)
• 🇺🇿 O'zbek, 🇷🇺 Русский, 🇬🇧 English

*Texnologiya:*
• Whisper AI (offline, mahalliy)
• Google Speech Recognition (zaxira)
"""

# ── Buyruqlar ──────────────────────────────────────────────────────────────

@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(WELCOME_TEXT, parse_mode="Markdown", reply_markup=main_keyboard())


@dp.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(HELP_TEXT, parse_mode="Markdown", reply_markup=back_keyboard())


@dp.message(Command("settings"))
async def cmd_settings(message: Message):
    is_group = message.chat.type in ("group", "supergroup")
    text = "⚙️ *Sozlamalar*\n\n"

    lang = get_user_language(message.from_user.id)
    lang_name = Config.SUPPORTED_LANGUAGES.get(lang, "Avtomatik")
    text += f"🌐 Joriy til: *{lang_name}*"

    if is_group:
        enabled = is_chat_enabled(message.chat.id)
        status = "✅ Yoqiq" if enabled else "❌ O'chiq"
        text += f"\n📢 Guruh holati: *{status}*"

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=settings_keyboard(message.chat.id, is_group=is_group),
    )


@dp.message(Command("stats"))
async def cmd_stats(message: Message):
    user_s  = get_user_stats(message.from_user.id)
    global_s = get_global_stats()

    text = (
        f"📊 *Statistika*\n\n"
        f"*Sizning:*\n"
        f"• Jami xabarlar: `{user_s['total']}`\n"
        f"• Jami belgilar: `{user_s['total_chars']}`\n"
        f"• Jami davomiylik: `{format_duration(user_s['total_duration'])}`\n\n"
        f"*Umumiy:*\n"
        f"• Barcha xabarlar: `{global_s['total']}`\n"
        f"• Foydalanuvchilar: `{global_s['unique_users']}`\n"
        f"• Barcha belgilar: `{global_s['total_chars']}`"
    )
    await message.answer(text, parse_mode="Markdown", reply_markup=back_keyboard())


# ── Callback handler ───────────────────────────────────────────────────────

@dp.callback_query()
async def process_callback(callback: CallbackQuery):
    data = callback.data
    await callback.answer()

    is_group = callback.message.chat.type in ("group", "supergroup")

    # ── Asosiy menyuga qaytish
    if data == "back_main":
        await callback.message.edit_text(
            WELCOME_TEXT, parse_mode="Markdown", reply_markup=main_keyboard()
        )

    # ── Sozlamalar
    elif data == "settings":
        lang     = get_user_language(callback.from_user.id)
        lang_name = Config.SUPPORTED_LANGUAGES.get(lang, "Avtomatik")
        text     = f"⚙️ *Sozlamalar*\n\n🌐 Joriy til: *{lang_name}*"
        await callback.message.edit_text(
            text,
            parse_mode="Markdown",
            reply_markup=settings_keyboard(callback.message.chat.id, is_group=is_group),
        )

    # ── Yordam
    elif data == "help":
        await callback.message.edit_text(
            HELP_TEXT, parse_mode="Markdown", reply_markup=back_keyboard()
        )

    # ── Statistika
    elif data == "stats":
        user_s   = get_user_stats(callback.from_user.id)
        global_s = get_global_stats()
        text = (
            f"📊 *Statistika*\n\n"
            f"*Sizning:*\n"
            f"• Jami xabarlar: `{user_s['total']}`\n"
            f"• Jami belgilar: `{user_s['total_chars']}`\n\n"
            f"*Umumiy:*\n"
            f"• Barcha xabarlar: `{global_s['total']}`\n"
            f"• Foydalanuvchilar: `{global_s['unique_users']}`"
        )
        await callback.message.edit_text(
            text, parse_mode="Markdown", reply_markup=back_keyboard()
        )

    # ── Guruhda yoqish/o'chirish
    elif data == "group_on":
        if not is_group:
            return
        set_chat_enabled(callback.message.chat.id, True)
        await callback.answer("✅ Bot guruhda yoqildi", show_alert=True)

    elif data == "group_off":
        if not is_group:
            return
        set_chat_enabled(callback.message.chat.id, False)
        await callback.answer("❌ Bot guruhda o'chirildi", show_alert=True)

    # ── Til tanlash menyusi
    elif data == "change_lang":
        await callback.message.edit_text(
            "🌐 *Tilni tanlang:*\n\n"
            "🤖 *Avtomatik* — Whisper tilni o'zi aniqlaydi (tavsiya)\n"
            "Yoki aniq tilni belgilang:",
            parse_mode="Markdown",
            reply_markup=language_keyboard(),
        )

    # ── Til saqlash
    elif data.startswith("lang_"):
        lang = data.replace("lang_", "")
        set_user_language(callback.from_user.id, lang)
        lang_name = Config.SUPPORTED_LANGUAGES.get(lang, lang)
        await callback.answer(f"✅ Til saqlandi: {lang_name}", show_alert=True)
        # Sozlamalar menyusiga qaytish
        text = f"⚙️ *Sozlamalar*\n\n🌐 Joriy til: *{lang_name}*"
        await callback.message.edit_text(
            text,
            parse_mode="Markdown",
            reply_markup=settings_keyboard(callback.message.chat.id, is_group=is_group),
        )


# ── Ovozli xabar handler ───────────────────────────────────────────────────

@dp.message(F.voice)
async def handle_voice(message: Message):
    """Ovozli xabarni qabul qilib matnga o'girish"""

    chat_id = message.chat.id
    user_id = message.from_user.id
    is_group = message.chat.type in ("group", "supergroup")

    # Guruhda o'chirilgan bo'lsa — e'tibor berma
    if is_group and not is_chat_enabled(chat_id):
        return

    # Fayl hajmini tekshirish
    if message.voice.file_size > Config.MAX_FILE_SIZE:
        await message.reply("❌ Fayl hajmi 20 MB dan katta. Iltimos, qisqaroq xabar yuboring.")
        return

    # "Ishlanmoqda..." xabari
    status_msg = await message.reply("🔄 Ovozni qabul qildim, matnga o'girmoqda...")

    temp_path = None
    start_time = time.time()

    try:
        # Faylni yuklab olish
        voice_file = await bot.get_file(message.voice.file_id)
        temp_fd, temp_path = tempfile.mkstemp(suffix=".ogg", dir=Config.TEMP_DIR)
        os.close(temp_fd)

        await bot.download_file(voice_file.file_path, temp_path)
        logger.info(f"Fayl yuklandi: {os.path.basename(temp_path)} ({message.voice.file_size} bayt)")

        # Til aniqlash (foydalanuvchi sozlamasidan)
        language = get_user_language(user_id)

        # Asosiy funksiya — audio → matn
        text_result = await transcribe_audio(temp_path, language)

        elapsed = time.time() - start_time

        # Natijani formatlash
        if is_group:
            user_name = message.from_user.full_name
            result = (
                f"👤 *{user_name}* ovozli xabari:\n\n"
                f"📝 {text_result}\n\n"
                f"⏱ {format_duration(message.voice.duration)} | 🕐 {elapsed:.1f}s"
            )
        else:
            result = (
                f"📝 *Natija:*\n\n{text_result}\n\n"
                f"⏱ Davomiylik: {format_duration(message.voice.duration)} | "
                f"🕐 O'girish: {elapsed:.1f}s"
            )

        # Xabarni yangilash
        await bot.edit_message_text(
            result,
            chat_id=chat_id,
            message_id=status_msg.message_id,
            parse_mode="Markdown",
        )

        # Statistika saqlash
        if not text_result.startswith("❌"):
            save_stat(user_id, chat_id, message.voice.duration, text_result, language)

        logger.info(
            f"Muvaffaqiyatli | user:{user_id} | "
            f"davom:{message.voice.duration}s | "
            f"belgi:{len(text_result)} | vaqt:{elapsed:.1f}s"
        )

    except Exception as e:
        logger.error(f"handle_voice xatosi: {e}", exc_info=True)
        await bot.edit_message_text(
            f"❌ Kutilmagan xatolik yuz berdi.\n\nXato: `{e}`",
            chat_id=chat_id,
            message_id=status_msg.message_id,
            parse_mode="Markdown",
        )

    finally:
        # Vaqtincha faylni o'chirish
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass


# ── Guruhga qo'shilganda ───────────────────────────────────────────────────

@dp.message(F.new_chat_members)
async def on_bot_added(message: Message):
    for member in message.new_chat_members:
        if member.id == bot.id:
            await message.answer(
                "👋 *Salom guruh!*\n\n"
                "Men ovozli xabarlarni matnga o'giraman.\n"
                "Ovozli xabar yuboring — avtomatik tarjima qilaman! 🎤➡️📝\n\n"
                "Sozlamalar: /settings",
                parse_mode="Markdown",
            )


# ── Ishga tushirish ────────────────────────────────────────────────────────

async def main():
    # Tayyorgarlik
    create_temp_dir(Config.TEMP_DIR)
    init_db()

    # Eski fayllarni tozalash
    clean_temp_files(Config.TEMP_DIR, hours=1)

    logger.info("=" * 50)
    logger.info("🤖 Bot ishga tushdi")
    logger.info(f"📦 Whisper modeli: {Config.WHISPER_MODEL}")
    logger.info("=" * 50)

    print("🤖 Bot ishga tushdi!")
    print(f"📦 Whisper modeli: {Config.WHISPER_MODEL}")
    print("📝 Ovozli xabarlar qabul qilinadi...")

    await dp.start_polling(bot, skip_updates=True)


if __name__ == "__main__":
    asyncio.run(main())
