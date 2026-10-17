# -*- coding: utf-8 -*-
"""Send one Varian term to a Telegram forum topic; support manual previews."""
import json
import os
import random
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent


def get_entries():
    entries = json.loads((ROOT / 'varian_economic_vocabulary.json').read_text(encoding='utf-8'))['entries']
    if not entries:
        raise ValueError('Vocabulary JSON contains no entries')
    return entries


def select_term(today, *, manual=False, term_number=''):
    entries = get_entries()
    if manual:
        if term_number.strip():
            try:
                n = int(term_number)
            except ValueError as exc:
                raise ValueError('term_number must be an integer') from exc
            if not 1 <= n <= len(entries):
                raise ValueError(f'term_number must be between 1 and {len(entries)}')
            return entries[n - 1]
        return random.choice(entries)

    start_date = date.fromisoformat(os.getenv('VOCAB_START_DATE', '2026-10-18'))
    if today < start_date:
        return None
    return entries[(today - start_date).days % len(entries)]


def format_message(entry):
    return (
        '📚 Varian | Daily Microeconomics Term\n\n'
        f"💡 {entry['term']}\n\n"
        f"📖 Definition: {entry['definition']}\n\n"
        f"🔎 Example: {entry['example']}\n\n"
        f"📌 Chapter {entry['chapter']} · {entry['topic']}"
    )


def main():
    # Manual workflows can send even before VOCAB_START_DATE.
    manual = os.getenv('VOCAB_MANUAL_TEST', '').lower() == 'true'
    today = datetime.now(ZoneInfo('Asia/Tehran')).date()
    entry = select_term(today, manual=manual,
                        term_number=os.getenv('VOCAB_TEST_TERM_NUMBER', ''))
    if entry is None:
        print('Before VOCAB_START_DATE; skipping scheduled run')
        return

    token = os.getenv('BOT_TOKEN', '').strip()
    chat_id = os.getenv('VOCAB_CHAT_ID', '').strip()
    thread_id = os.getenv('VOCAB_THREAD_ID', '').strip()
    if not all((token, chat_id, thread_id)):
        raise RuntimeError('Missing BOT_TOKEN, VOCAB_CHAT_ID or VOCAB_THREAD_ID in GitHub Actions secrets')

    payload = urlencode({
        'chat_id': chat_id,
        'message_thread_id': thread_id,
        'text': format_message(entry),
    }).encode('utf-8')
    request = Request(f'https://api.telegram.org/bot{token}/sendMessage', data=payload, method='POST')
    with urlopen(request, timeout=30) as response:
        result = json.load(response)
    if not result.get('ok'):
        raise RuntimeError('Telegram did not confirm delivery')
    print(f"Sent {entry['id']} to Telegram topic ({'manual test' if manual else 'scheduled'})")


if __name__ == '__main__':
    main()
