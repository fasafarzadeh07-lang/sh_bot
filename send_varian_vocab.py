# -*- coding: utf-8 -*-
"""Independent daily Varian vocabulary publisher for the Telegram forum topic."""
import json
import os
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
START_DATE = date.fromisoformat(os.getenv("VOCAB_START_DATE", "2026-10-18"))


def build_daily_message(today=None):
    today = today or datetime.now(ZoneInfo("Asia/Tehran")).date()
    elapsed_days = (today - START_DATE).days
    if elapsed_days < 0:
        return None, None
    entries = json.loads((ROOT / "varian_economic_vocabulary.json").read_text(encoding="utf-8"))["entries"]
    if not entries:
        raise ValueError("No entries in vocabulary JSON")
    entry = entries[elapsed_days % len(entries)]
    message = (
        "📚 Varian | Daily Microeconomics Term\n\n"
        f"💡 {entry['term']}\n\n"
        f"📖 Definition: {entry['definition']}\n\n"
        f"🔎 Example: {entry['example']}\n\n"
        f"📌 Chapter {entry['chapter']} · {entry['topic']}"
    )
    return entry, message


def main():
    token = os.getenv("BOT_TOKEN")
    chat_id = os.getenv("VOCAB_CHAT_ID")
    thread_id = os.getenv("VOCAB_THREAD_ID")
    if not all((token, chat_id, thread_id)):
        raise RuntimeError("Set BOT_TOKEN, VOCAB_CHAT_ID, and VOCAB_THREAD_ID as GitHub Actions secrets")
    today = datetime.now(ZoneInfo("Asia/Tehran")).date()
    entry, message = build_daily_message(today)
    if entry is None:
        print("Before VOCAB_START_DATE; skipping")
        return
    payload = urlencode({
        "chat_id": chat_id,
        "message_thread_id": thread_id,
        "text": message,
    }).encode("utf-8")
    request = Request(f"https://api.telegram.org/bot{token}/sendMessage", data=payload, method="POST")
    with urlopen(request, timeout=30) as response:
        result = json.load(response)
    if not result.get("ok"):
        raise RuntimeError("Telegram did not confirm delivery")
    print(f"Sent {entry['id']} to vocab topic on {today.isoformat()}")


if __name__ == "__main__":
    main()
