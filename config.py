import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # Bot token
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")

    # Whisper modeli: tiny, base, small, medium, large
    # tiny  → eng tez, kam xotira, sifat past
    # base  → tez, yaxshi sifat (tavsiya etiladi)
    # small → sekinroq, yaxshi sifat
    WHISPER_MODEL: str = os.getenv("WHISPER_MODEL", "base")

    # Fayl hajmi chegarasi (20 MB)
    MAX_FILE_SIZE: int = 20 * 1024 * 1024

    # Vaqtincha fayllar papkasi
    TEMP_DIR: str = "temp_audio"

    # Log fayli
    LOG_FILE: str = "bot.log"

    # Qo'llab-quvvatlanadigan tillar
    SUPPORTED_LANGUAGES: dict = {
        "uz": "O'zbek",
        "ru": "Русский",
        "en": "English",
        "auto": "🤖 Avtomatik",
    }

    # Default til
    DEFAULT_LANGUAGE: str = "auto"
