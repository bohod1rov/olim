"""
Audio faylni matnga o'girish moduli
- Whisper (offline) asosiy
- Katta fayllar uchun bo'laklarga bo'lib ishlash
- O'zbek, Rus, Ingliz tillarini avtomatik aniqlash
"""

import os
import asyncio
import logging
import subprocess

logger = logging.getLogger(__name__)

# Whisper modeli global yuklab olinadi (bir marta)
_whisper_model = None


def get_whisper_model():
    """Whisper modelini yuklash (faqat bir marta)"""
    global _whisper_model
    if _whisper_model is None:
        try:
            import whisper
            from config import Config
            logger.info(f"Whisper modeli yuklanmoqda: {Config.WHISPER_MODEL}")
            _whisper_model = whisper.load_model(Config.WHISPER_MODEL)
            logger.info("Whisper modeli tayyor!")
        except Exception as e:
            logger.error(f"Whisper yuklanmadi: {e}")
            raise
    return _whisper_model


def convert_to_wav(input_path: str, output_path: str) -> bool:
    """Audio faylni WAV formatiga o'girish (ffmpeg orqali)"""
    try:
        cmd = [
            "ffmpeg", "-y",
            "-i", input_path,
            "-ar", "16000",   # 16kHz — Whisper uchun optimal
            "-ac", "1",        # Mono
            "-f", "wav",
            output_path
        ]
        result = subprocess.run(cmd, capture_output=True, timeout=300)
        return result.returncode == 0
    except Exception as e:
        logger.error(f"ffmpeg xatosi: {e}")
        return False


def get_audio_duration(wav_path: str) -> float:
    """Audio davomiyligini aniqlash (soniyalarda)"""
    try:
        cmd = [
            "ffprobe", "-v", "quiet",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            wav_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return float(result.stdout.strip())
    except Exception:
        return 0.0


def split_audio(wav_path: str, chunk_duration: int = 600) -> list:
    """
    Audio faylni bo'laklarga bo'lish
    chunk_duration: har bir bo'lak davomiyligi (soniyalarda), default 10 daqiqa
    """
    duration = get_audio_duration(wav_path)
    if duration <= chunk_duration:
        return [wav_path]  # Bo'lish shart emas

    chunks = []
    temp_dir = os.path.dirname(wav_path)
    start = 0
    index = 0

    while start < duration:
        chunk_path = os.path.join(temp_dir, f"chunk_{index}.wav")
        cmd = [
            "ffmpeg", "-y",
            "-i", wav_path,
            "-ss", str(start),
            "-t", str(chunk_duration),
            "-ar", "16000",
            "-ac", "1",
            chunk_path
        ]
        result = subprocess.run(cmd, capture_output=True, timeout=120)
        if result.returncode == 0:
            chunks.append(chunk_path)
        start += chunk_duration
        index += 1

    logger.info(f"Audio {len(chunks)} bo'lakka bo'lindi (har biri max {chunk_duration}s)")
    return chunks


def transcribe_chunk(model, wav_path: str, language: str) -> tuple:
    """
    Bitta bo'lakni transcribe qilish
    Qaytaradi: (matn, aniqlangan_til)
    """
    if language == "auto":
        whisper_lang = None  # Whisper o'zi aniqlaydi
    else:
        lang_map = {"uz": "uzbek", "ru": "russian", "en": "english"}
        whisper_lang = lang_map.get(language, None)

    result = model.transcribe(
        wav_path,
        language=whisper_lang,
        task="transcribe",
        fp16=False,
        verbose=False,
        condition_on_previous_text=True,
        temperature=0.0,
    )

    text = result.get("text", "").strip()
    detected_lang = result.get("language", "unknown")
    return text, detected_lang


async def transcribe_audio(file_path: str, language: str = "auto") -> str:
    """
    Asosiy funksiya: audio faylni matnga o'girish
    - Katta fayllarni bo'laklarga bo'ladi (10 daqiqalik bo'laklar)
    - Barcha bo'laklarni birlashtiradi
    - Tilni avtomatik aniqlaydi (uz/ru/en)
    """
    try:
        model = get_whisper_model()
    except Exception as e:
        return f"❌ Whisper modeli yuklanmadi: {e}"

    # WAV fayl yo'li
    base = os.path.splitext(file_path)[0]
    wav_path = base + "_converted.wav"
    chunk_files = []

    try:
        # 1. WAV formatiga o'girish
        logger.info(f"WAV ga o'girilmoqda: {os.path.basename(file_path)}")
        if not convert_to_wav(file_path, wav_path):
            return "❌ Audio faylni o'girishda xatolik yuz berdi (ffmpeg)"

        # 2. Davomiylikni aniqlash
        duration = get_audio_duration(wav_path)
        logger.info(f"Audio davomiyligi: {duration:.1f}s")

        # 3. Bo'laklarga bo'lish (10 daqiqadan ortiq bo'lsa)
        chunks = await asyncio.get_event_loop().run_in_executor(
            None, split_audio, wav_path, 600
        )

        # Asl wav fayldan farqli bo'laklarni yig'ib olish (tozalash uchun)
        chunk_files = [c for c in chunks if c != wav_path]

        # 4. Har bir bo'lakni transcribe qilish
        all_texts = []
        detected_language = "unknown"

        for i, chunk_path in enumerate(chunks):
            logger.info(f"Bo'lak {i+1}/{len(chunks)} transcribe qilinmoqda...")
            try:
                text, detected_lang = await asyncio.get_event_loop().run_in_executor(
                    None, transcribe_chunk, model, chunk_path, language
                )
                if text:
                    all_texts.append(text)
                if i == 0:
                    detected_language = detected_lang
                    logger.info(f"Aniqlangan til: {detected_language}")
            except Exception as e:
                logger.error(f"Bo'lak {i+1} xatosi: {e}")
                all_texts.append(f"[{i+1}-qism o'girilmadi]")

        # 5. Natijalarni birlashtirish
        if not all_texts:
            return "❌ Ovozli xabardan matn ajratib bo'lmadi. Aniqroq gapiring."

        full_text = " ".join(all_texts).strip()
        return full_text

    except Exception as e:
        logger.error(f"transcribe_audio xatosi: {e}", exc_info=True)
        return f"❌ Xatolik yuz berdi: {e}"

    finally:
        # Vaqtincha fayllarni tozalash
        for chunk_file in chunk_files:
            try:
                if os.path.exists(chunk_file):
                    os.remove(chunk_file)
            except OSError:
                pass
        try:
            if os.path.exists(wav_path):
                os.remove(wav_path)
        except OSError:
            pass