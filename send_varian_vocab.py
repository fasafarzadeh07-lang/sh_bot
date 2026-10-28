# -*- coding: utf-8 -*-
"""Post one Varian term to a Telegram forum topic, with GitHub-persisted progress.

Manual workflow runs are previews: they send a real message but never advance the tracker.
Scheduled runs send the next unsent term and update the tracker only on success.
"""
import json
import os
import random
import requests
from vocab_visual import render
from datetime import date, datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
VOCAB_FILE = ROOT / 'varian_economic_vocabulary.json'
TRACKER_FILE = ROOT / 'vocab_progress.json'
TEHRAN = ZoneInfo('Asia/Tehran')


def load_terms():
    items = json.loads(VOCAB_FILE.read_text(encoding='utf-8'))
    if not isinstance(items, list) or not items:
        raise ValueError('The vocabulary file must contain a nonempty JSON array.')
    seen = set()
    for index, item in enumerate(items, 1):
        if not isinstance(item, dict) or any(not isinstance(item.get(field), str) or not item[field].strip()
                                             for field in ('term', 'definition', 'example')):
            raise ValueError(f'Entry #{index} must contain term, definition, and example strings.')
        key = item['term'].strip().casefold()
        if key in seen:
            raise ValueError(f'Duplicate term in JSON: {item["term"]}')
        seen.add(key)
    return items


def term_id(entry):
    # Stable across insertion/reordering. Rename is treated as a new term.
    return entry['term'].strip().casefold()


def load_progress():
    if not TRACKER_FILE.exists():
        raise FileNotFoundError(f'Missing {TRACKER_FILE.name}; keep it in the repository.')
    progress = json.loads(TRACKER_FILE.read_text(encoding='utf-8'))
    if not isinstance(progress, dict) or not isinstance(progress.get('sent_ids'), list):
        raise ValueError('Malformed vocab_progress.json; expected sent_ids list.')
    return progress


def select_scheduled(terms, progress):
    available = {term_id(t) for t in terms}
    sent = set(progress['sent_ids']) & available
    # Completion resets the current cycle; newly added terms are not skipped.
    if len(sent) == len(available):
        sent = set()
        progress['completed_cycles'] = int(progress.get('completed_cycles', 0)) + 1
    selected = next(t for t in terms if term_id(t) not in sent)
    return selected, sent


def format_message(entry):
    category = entry.get('category', '').strip()
    footer = f'\n\n🏷️ {category}' if category else ''
    return (
        f'💡 {entry["term"]}\n\n'
        f'📖 Definition: {entry["definition"]}\n\n'
        f'🔎 Example: {entry["example"]}'
        f'{footer}'
    )


def post_to_telegram(message, entry):
    """Send an educational image with the original message as its caption."""
    token = os.getenv('BOT_TOKEN', '').strip()
    chat_id = (os.getenv('VOCAB_CHAT_ID') or os.getenv('CHANNEL_ID') or '').strip()
    thread_id = os.getenv('VOCAB_THREAD_ID', '').strip()
    if not token or not chat_id or not thread_id:
        raise RuntimeError('Set BOT_TOKEN, VOCAB_THREAD_ID and either VOCAB_CHAT_ID or CHANNEL_ID.')
    caption_length = len(message.encode('utf-16-le')) // 2
    if caption_length > 1024:
        raise ValueError('Telegram photo caption exceeds 1024 characters.')
    photo, is_diagram = render(entry)
    print('Image type:', 'economic diagram' if is_diagram else 'concept card')
    response = requests.post(
        f'https://api.telegram.org/bot{token}/sendPhoto',
        data={'chat_id': chat_id, 'message_thread_id': thread_id, 'caption': message},
        files={'photo': ('varian.png', photo, 'image/png')},
        timeout=60,
    )
    if not response.ok:
        raise RuntimeError(f'Telegram sendPhoto failed (HTTP {response.status_code}).')
    payload = response.json()
    if not payload.get('ok') or not payload.get('result', {}).get('message_id'):
        raise RuntimeError('Telegram did not confirm the photo message.')
    return payload['result']['message_id']


def main():
    manual = os.getenv('VOCAB_MANUAL_TEST', '').strip().lower() == 'true'
    today = datetime.now(TEHRAN).date()
    terms = load_terms()

    if manual:
        raw = os.getenv('VOCAB_TEST_TERM_NUMBER', '').strip()
        if raw:
            try:
                index = int(raw)
            except ValueError:
                raise ValueError('Manual term number must be an integer.') from None
            if not 1 <= index <= len(terms):
                raise ValueError(f'Manual term number must be 1–{len(terms)}.')
            entry = terms[index - 1]
        else:
            entry = random.choice(terms)
        message_id = post_to_telegram(format_message(entry), entry)
        print(f'MANUAL TEST sent: {entry["term"]!r}; message_id={message_id}; tracker unchanged.')
        return

    start = date.fromisoformat(os.getenv('VOCAB_START_DATE', '2026-10-18'))
    if today < start:
        print(f'Before start date ({start}); scheduled posting skipped. Manual tests still work.')
        return

    progress = load_progress()
    if progress.get('last_sent_date') == today.isoformat():
        print(f'Already sent scheduled vocabulary on {today}; skipping.')
        return

    entry, sent = select_scheduled(terms, progress)
    message_id = post_to_telegram(format_message(entry), entry)
    sent.add(term_id(entry))
    progress['sent_ids'] = [term_id(t) for t in terms if term_id(t) in sent]
    progress['last_sent_date'] = today.isoformat()
    progress['last_sent_term'] = entry['term']
    progress['last_message_id'] = message_id
    TRACKER_FILE.write_text(json.dumps(progress, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'SCHEDULED sent: {entry["term"]!r}; message_id={message_id}; tracker updated locally.')
    print('GitHub Actions must commit and push vocab_progress.json to persist this update.')


if __name__ == '__main__':
    main()
