"""Yordamchi funksiyalar"""

import os
import logging
import time
from pathlib import Path


def setup_logging(log_file: str = "bot.log"):
    """Logging sozlash"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )


def create_temp_dir(temp_dir: str):
    """Vaqtincha papka yaratish"""
    Path(temp_dir).mkdir(parents=True, exist_ok=True)


def clean_temp_files(temp_dir: str, hours: int = 1):
    """Eski vaqtincha fayllarni o'chirish"""
    now = time.time()
    try:
        for f in Path(temp_dir).iterdir():
            if f.is_file() and (now - f.stat().st_mtime) > hours * 3600:
                f.unlink()
    except Exception as e:
        logging.getLogger(__name__).warning(f"Fayllarni tozalashda xato: {e}")


def format_duration(seconds: int) -> str:
    """Soniyalarni chiroyli formatga o'girish"""
    if seconds < 60:
        return f"{seconds}s"
    minutes = seconds // 60
    secs = seconds % 60
    if minutes < 60:
        return f"{minutes}m {secs}s"
    hours = minutes // 60
    mins = minutes % 60
    return f"{hours}h {mins}m {secs}s"