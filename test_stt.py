"""TTS -> STT roundtrip test.
Run: python test_stt.py
"""
import asyncio, os, sys
from dotenv import load_dotenv
load_dotenv()

from backend.services.speech_service import (
    XFYUN_APP_ID, XFYUN_API_KEY, XFYUN_API_SECRET,
    _run_tts, _run_iat, _extract_iat_text,
)


def run_tts(text: str) -> bytes:
    from xfyunsdkspeech.tts_client import TtsClient
    import base64
    client = TtsClient(
        app_id=XFYUN_APP_ID,
        api_key=XFYUN_API_KEY,
        api_secret=XFYUN_API_SECRET,
        vcn="xiaoyan",
        aue="raw",        # PCM output
        auf="audio/L16;rate=16000",  # 16kHz to match IAT requirement
    )
    audio = bytearray()
    for chunk in client.stream(text):
        if isinstance(chunk, dict) and chunk.get("audio"):
            audio.extend(base64.b64decode(chunk["audio"]))
    return bytes(audio)


def run_iat(mp3_path: str) -> str:
    from xfyunsdkspeech.iat_client import IatClient
    client = IatClient(
        app_id=XFYUN_APP_ID,
        api_key=XFYUN_API_KEY,
        api_secret=XFYUN_API_SECRET,
        encoding="raw",
        format="audio/L16;rate=16000",
    )
    result = []
    with open(mp3_path, "rb") as f:
        for chunk in client.stream(f):
            text = _extract_iat_text(chunk)
            if text:
                result.append(text)
    return "".join(result)


async def main():
    if not XFYUN_APP_ID:
        print("[ERR] XFYUN_APP_ID not set")
        return

    test_text = "你好，我想应聘这个软件工程师的职位，我有三年的Python开发经验。"
    print("[1] TTS: generating audio for: %s" % test_text)

    try:
        mp3_bytes = await asyncio.to_thread(run_tts, test_text)
    except Exception as e:
        print("[ERR] TTS failed:", e)
        return

    if not mp3_bytes:
        print("[ERR] TTS returned empty audio")
        return

    mp3_path = "tts_output.mp3"
    with open(mp3_path, "wb") as f:
        f.write(mp3_bytes)
    print("[OK] TTS done: %d bytes -> %s" % (len(mp3_bytes), mp3_path))

    print("[2] STT: sending audio to IAT...")
    try:
        recognized = await asyncio.to_thread(run_iat, mp3_path)
    except Exception as e:
        print("[ERR] STT failed:", e)
        return

    print("[OK] STT result:", recognized if recognized else "(empty)")
    print()
    print("Original : %s" % test_text)
    print("Recognized: %s" % recognized)


asyncio.run(main())
