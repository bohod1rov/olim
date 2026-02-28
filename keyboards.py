"""Inline klaviaturalar"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from config import Config


def main_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="⚙️ Sozlamalar", callback_data="settings"),
        InlineKeyboardButton(text="📊 Statistika", callback_data="stats"),
    )
    builder.row(
        InlineKeyboardButton(text="❓ Yordam", callback_data="help"),
    )
    return builder.as_markup()


def settings_keyboard(chat_id: int = None, is_group: bool = False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.row(InlineKeyboardButton(text="🌐 Tilni o'zgartirish", callback_data="change_lang"))

    if is_group:
        builder.row(
            InlineKeyboardButton(text="✅ Yoqish", callback_data="group_on"),
            InlineKeyboardButton(text="❌ O'chirish", callback_data="group_off"),
        )

    builder.row(InlineKeyboardButton(text="◀️ Orqaga", callback_data="back_main"))
    return builder.as_markup()


def language_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    lang_buttons = [
        ("🤖 Avtomatik", "lang_auto"),
        ("🇺🇿 O'zbek",   "lang_uz"),
        ("🇷🇺 Русский",  "lang_ru"),
        ("🇬🇧 English",  "lang_en"),
    ]
    for text, data in lang_buttons:
        builder.add(InlineKeyboardButton(text=text, callback_data=data))
    builder.adjust(2)
    builder.row(InlineKeyboardButton(text="◀️ Orqaga", callback_data="settings"))
    return builder.as_markup()


def back_keyboard(callback_data: str = "back_main") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="◀️ Orqaga", callback_data=callback_data))
    return builder.as_markup()
