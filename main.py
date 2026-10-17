return response.text
            
        except APIError as e:
            if e.code in (429, 500, 502, 503, 504):
                print(f"Gemini temporary API error ({e.code}); retrying in {delay} seconds...")
                time.sleep(delay)
                delay *= 2  # Exponential backoff
            else:
                # If it is any other type of API error (like 400 or 403), raise it
                raise e
        except Exception as e:
            print(f"Connection issue on attempt {attempt + 1}: {e}. Retrying...")
            time.sleep(delay)
            delay *= 2

    # --- Fallback Option ---
    # If Gemini 3.6 was completely overloaded, we use your highly reliable Gemini 2.5 Flash
    print(f"{primary_model} unavailable. Falling back to {backup_model}...")
    try:
        response = client.models.generate_content(
            model=backup_model,
            contents=prompt
        )
        if not response.text or not response.text.strip():
            raise ValueError("Fallback Gemini returned an empty response")
        return response.text
    except Exception as fallback_err:
        raise RuntimeError(f"Both Gemini models failed ({primary_model}, {backup_model})") from fallback_err


def split_telegram_message(message, limit=4000):
    """Keep each part below Telegram's limit, including supplementary emojis."""
    chunks = []
    while message:
        units = 0
        end = 0
        for char in message:
            size = 2 if ord(char) > 0xFFFF else 1
            if units + size > limit:
                break
            units += size
            end += 1
        if end == 0:
            raise ValueError("Message limit is too small")
        if end < len(message):
            # Prefer paragraph, then line boundaries to keep stories readable.
            boundary = message.rfind("\n\n", 0, end)
            if boundary > 0:
                end = boundary + 2
            else:
                boundary = message.rfind("\n", 0, end)
                if boundary > 0:
                    end = boundary + 1
        chunks.append(message[:end])
        message = message[end:]
    return chunks


def send_to_telegram(message):
    primary_chat_id = (CHANNEL_ID or "").strip()
    secondary_chat_id = (CHANNEL_ID_2 or "").strip()
    if not primary_chat_id:
        raise ValueError("CHANNEL_ID is required. Set it in GitHub Actions secrets.")

    destinations = [("CHANNEL_ID", primary_chat_id)]
    if secondary_chat_id:
        destinations.append(("CHANNEL_ID_2", secondary_chat_id))
    else:
        print("CHANNEL_ID_2 is not set; skipping the optional second channel.")

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    parts = split_telegram_message(message)

    for channel_name, chat_id in destinations:
        for index, part in enumerate(parts):
            if index:
                time.sleep(1)
            result = requests.post(
                url,
                json={"chat_id": chat_id, "text": part},
                timeout=30,
            )
            data = result.json()
            if not result.ok or not data.get("ok"):
                raise RuntimeError(
                    f"Telegram send to {channel_name} failed: "
                    f"{data.get('description', 'Unknown error')}"
                )
            print(f"Sent part {index + 1}/{len(parts)} to {channel_name}")


def main():
    print("Getting news...")

    articles = get_news()

    print(f"Found {len(articles)} articles")

    summary = summarize_news(articles)

    snapshot = get_market_snapshot()
    company_returns = get_company_returns()

    final_message = f"""{summary}

{snapshot}"""
    if company_returns:
        final_message += f"\n\n{company_returns}"

    print("Summary created")

    send_to_telegram(final_message)

    print("Posted to Telegram")


if __name__ == "__main__":
    main()
