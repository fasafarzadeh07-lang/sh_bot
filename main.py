# -*- coding: utf-8 -*-
import os
import time
import json
import feedparser
import requests
from google import genai
from google.genai import types
from google.genai.errors import APIError  # Added to handle Gemini specific errors
import yfinance as yf


# Get secrets from GitHub Actions
BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_KEY")


RSS_FEEDS = [
    # 📊 MarketWatch (official RSS)
    "https://feeds.marketwatch.com/marketwatch/topstories/",

    # ₿ CoinDesk (crypto)
    "https://www.coindesk.com/arc/outboundfeeds/rss/",

    # 📈 Investing.com (official RSS)
    "https://www.investing.com/rss/news.rss",
    "https://www.investing.com/rss/news_25.rss",  # economic calendar / macro focus

    # 📰 Reuters (official but limited RSS)
    "https://feeds.reuters.com/reuters/businessNews",
    "https://feeds.reuters.com/reuters/globalmarketsNews",

    # 📊 Yahoo Finance (official RSS)
    "https://finance.yahoo.com/news/rssindex",
    "https://feeds.finance.yahoo.com/rss/2.0/headline",

    # 🏦 Financial Times (official section RSS)
    "https://www.ft.com/world?format=rss",
    "https://www.ft.com/markets?format=rss",
    "https://www.ft.com/global-economy?format=rss",

    # 🏛 Bloomberg (⚠️ via Google News RSS workaround)
    "https://news.google.com/rss/search?q=site:bloomberg.com+markets",
    "https://news.google.com/rss/search?q=site:bloomberg.com+economy",

    # 📰 Wall Street Journal (⚠️ limited + workaround)
    "https://wsj.com/xml/rss/3_7014.xml",
    "https://wsj.com/xml/rss/3_7031.xml",
    "https://news.google.com/rss/search?q=site:wsj.com+markets",

    # 📊 Morningstar (no official RSS → Google News workaround)
    "https://news.google.com/rss/search?q=site:morningstar.com+stocks",
    "https://news.google.com/rss/search?q=site:morningstar.com+fund",

    # 📉 Barron's (no official RSS → workaround)
    "https://news.google.com/rss/search?q=site:barrons.com+markets",

    # 🌍 The Economist (no official RSS → workaround)
    "https://news.google.com/rss/search?q=site:economist.com+economy",

    # 💱 Forex Factory (VERY IMPORTANT for FX + macro)
    "https://www.forexfactory.com/news-feed",
    "https://www.forexfactory.com/calendar"
]


def is_valid_url(url):
    return url and url.startswith("http") and "news.google.com" not in url


def get_news():
    articles = []

    for feed_url in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)

            if not hasattr(feed, "entries"):
                continue

            for entry in feed.entries[:3]:
                if hasattr(entry, "title") and hasattr(entry, "link"):
                    if is_valid_url(entry.link):
                        articles.append({
                            "title": entry.title,
                            "summary": getattr(entry, "summary", ""),
                            "link": entry.link
                        })

        except Exception as e:
            print(f"RSS failed: {feed_url} -> {e}")

    return articles


def get_change(symbol):
    hist = yf.Ticker(symbol).history(period="5d")

    if len(hist) < 2:
        return None

    last = hist["Close"].iloc[-1]
    prev = hist["Close"].iloc[-2]

    change = ((last - prev) / prev) * 100

    return last, change


def get_market_snapshot():
    snapshot = "📊 Market Snapshot\n\n"

    assets = [
        ("₿ Bitcoin", "BTC-USD", "${:,.0f}"),
        ("🔷 Ethereum", "ETH-USD", "${:,.0f}"),
        ("🛢️ Brent", "BZ=F", "${:.2f}"),
        ("🥇 Gold", "GC=F", "${:.2f}"),
        ("📈 S&P 500", "^GSPC", "{:.0f}")
    ]

    for name, ticker, fmt in assets:
        try:
            result = get_change(ticker)

            if result is None:
                continue

            price, change = result

            snapshot += f"{name}: {fmt.format(price)} ({change:+.1f}%)\n"

        except Exception as e:
            print(f"{ticker} failed: {e}")

    if snapshot.strip() == "📊 Market Snapshot":
        return "📊 Market Snapshot unavailable today"

    return snapshot


def get_curated_word_fallback():
    """Reads a word from the local JSON list, increments the index, and saves state."""
    try:
        # Load the tracker index
        with open("tracker.json", "r") as f:
            tracker = json.load(f)
        current_id = tracker.get("next_word_id", 0)

        # Load your curated economic words
        with open("econ_words.json", "r") as f:
            word_list = json.load(f)

        if not word_list:
            return "Economic Term of the Day\nCould not fetch terms."

        # Ensure index isn't out of range by wrapping around using modulo
        word_idx = current_id % len(word_list)
        selected_item = word_list[word_idx]

        # Increment and save next index (wrapping back to 0 if we hit the end of the list)
        tracker["next_word_id"] = (word_idx + 1) % len(word_list)
        with open("tracker.json", "w") as f:
            json.dump(tracker, f, indent=2)

        fallback_output = f"""📚 Daily Econ Word (Education Bonus):
- {selected_item['word']}
- {selected_item['definition']}"""
        return fallback_output

    except Exception as e:
        print(f"Fallback JSON workflow failed: {e}")
        return "📚 Daily Econ Word (Education Bonus):\n- Arbitrage\n- The simultaneous purchase and sale of an asset to profit from an imbalance in the price."


def summarize_news(articles):    
    headlines = "\n\n".join(
        f"""Title: {article['title']}
Summary: {article['summary']}
URL: {article['link']}"""
        for article in articles
    )

    # Cleaned and optimized system instruction payload
    system_instruction = """
You are a professional global macroeconomic news editor writing for a Telegram audience of students and finance enthusiasts.

Task:
- Read all provided articles (Title, Summary, URL).
- Group them into thematic sections.
- Select only the most important and market-moving stories.
- Merge duplicate stories from different sources into one concise story.
- Ignore low-impact, local, entertainment, lifestyle, promotional, repetitive, and non-economic news.

Newsworthiness Rules:
Prioritize factual, event-driven news.
Prefer stories reporting:
- Official economic data releases (CPI, PPI, GDP, PMI, employment, retail sales, etc.)
- Central bank decisions or speeches that moved markets
- Government policy announcements
- Major corporate earnings
- Mergers & acquisitions
- Trade policy, tariffs, sanctions
- Significant geopolitical developments affecting financial markets
- Major moves in financial markets, commodities, or crypto

Avoid:
- Opinion articles, editorials, commentary, explainers, long-form features, lifestyle pieces.
- Generic "trend" articles and speculative forecasts without a new catalyst.

Before selecting a story, ask:
"Would Bloomberg or Reuters likely consider this one of today's important market headlines?"
If the answer is no, skip it.

For the Macroeconomy section, prioritize in this order:
1. Inflation, 2. Employment, 3. GDP, 4. PMI, 5. Retail Sales, 6. Manufacturing, 7. Consumer Confidence, 8. Fiscal Policy.

Prioritize these sections:
🌍 Macroeconomy
🏦 Central Banks & Interest Rates
📈 Financial Markets
₿ Crypto & Digital Assets
🛢️ Energy & Commodities
🤖 Corporate & Global Industry
⚠️ Geopolitics (only if market-relevant)

Rules:
- Each section should include a maximum of 1–2 stories.
- Skip sections with no important news. Do NOT force stories into sections.
- Merge duplicate coverage from multiple sources.
- Prefer official reporting over commentary. Prefer Reuters, Bloomberg, Financial Times, Wall Street Journal when multiple sources report the same story.

URL RULES (IMPORTANT):
- First, select all news and structure the briefing normally.
- AFTER selection, decide which stories deserve a link.
- Include URLs for ONLY 2–4 stories in the entire report.
- Prioritize linking: Most important macro story, major markets/central bank story, geopolitical/energy story.
- Do NOT attach URLs to every story.
- Never output a URL whose domain is ft.com. If a selected story only has an ft.com link available, do not include a source link for that story.

When adding a URL, place it under the story as:
🔗 Source
<URL>

Output format:

🌍 Global Economic News 💰📈

🌍 Macroeconomy
1. Story title + 1–2 relevant emojis
Short explanation (2–3 sentences including key figures when available)
🔗 Read more:
<URL>

🏦 Central Banks & Interest Rates
1. Story title + 1–2 relevant emojis
Short explanation
🔗 Read more:
<URL>

📈 Financial Markets
1. Story title + 1–2 relevant emojis
Short explanation
🔗 Read more:
<URL>

₿ Crypto & Digital Assets
1. Story title + 1–2 relevant emojis
Short explanation
🔗 Read more:
<URL>

🛢️ Energy & Commodities
1. Story title + 1–2 relevant emojis
Short explanation
🔗 Read more:
<URL>

🤖 Corporate & Global Industry
1. Story title + 1–2 relevant emojis
Short explanation
🔗 Read more:
<URL>

⚠️ Geopolitics
1. Story title + 1–2 relevant emojis
Short explanation
🔗 Read more:
<URL>

📌 Market Summary:
Write 2–3 sentences connecting the most important stories above.
- Explain how the reported events are related to each other or how they influenced different markets/investor sentiment.
- Do not introduce new information.

📚 Daily Econ Word (Education Bonus):
- Analyze today's news headlines and extract exactly ONE highly relevant, advanced economic or financial concept that is mentioned or clearly implied in the text.
- If you find a relevant advanced term, select it, explain it simply, and keep it intuitive.

EXAMPLES OF WHAT TO LOOK FOR IN TODAY'S HEADLINES:
• If investors are selling off tech to buy other assets: "Sector Rotation"
• If two big competitors are merging (like Stripe & PayPal): "Horizontal Integration" or "Consolidation"
• If a central bank hikes or moves unexpectedly: "Monetary Tightening"
• If trade conflicts escalate: "Bilateral Trade Friction" or "Protectionism"
• If port strikes block grains: "Supply Chain Disruption" or "Commodity Volatility"

AVOID OBVIOUS/BASIC TERMS:
Do NOT select baseline introductory terms like GDP, Inflation, Tariff, Interest Rates, Stock, Bond, or Tax unless there is a deeper concept behind them. Look for the professional terms.

If—and ONLY if—absolutely no professional economic concepts can be found or implied in today's news, you must output EXACTLY the following text in this section:
NO_WORTH_READING_WORD_FOUND

General Constraints:
- Keep total output between 200 and 250 words (excluding URLs).
- Use clear, professional English. Do NOT invent facts or numbers.
- Each story should use different, highly specific, descriptive emojis (e.g. 💻 for semiconductors, 🤝 for mergers, 🚢 for shipping).
- Telegram formatting rules (IMPORTANT): Do NOT use any Markdown formatting. Do NOT use asterisks (*) anywhere. Do NOT bold, italicize, or underline any text. Output plain text only.
- If a selected story is primarily analysis, label it as:
📝 Analysis
before its explanation.
"""

    prompt = f"""
Here are today's headlines to analyze and summarize:

{headlines}
"""

    client = genai.Client(api_key=GEMINI_KEY)
    
    primary_model = "gemini-3.5-flash"
    backup_model = "gemini-2.5-flash"
    max_retries = 3
    delay = 2  # wait 2 seconds initially

    raw_response = None

    # --- Try generating with the newer Gemini 3.5 Flash first ---
    for attempt in range(max_retries):
        try:
            print(f"Attempting econ summary with {primary_model} (Attempt {attempt + 1}/{max_retries})...")
            response = client.models.generate_content(
                model=primary_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.3
                )
            )
            raw_response = response.text
            break
            
        except APIError as e:
            if e.code == 503:
                print(f"Gemini 3.5 is busy (503). Retrying in {delay} seconds...")
                time.sleep(delay)
                delay *= 2  # Exponential backoff
            else:
                raise e
        except Exception as e:
            print(f"Connection issue on attempt {attempt + 1}: {e}. Retrying...")
            time.sleep(delay)
            delay *= 2

    # --- Fallback Option ---
    if raw_response is None:
        print(f"Gemini 3.5 was unavailable. Falling back to the highly reliable {backup_model}...")
        try:
            response = client.models.generate_content(
                model=backup_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.3
                )
            )
            raw_response = response.text
        except Exception as fallback_err:
            raw_response = f"Gemini Error: Both {primary_model} and {backup_model} failed. Details: {fallback_err}"

    # Check if we need to replace the word section with our local curated word
    if "NO_WORTH_READING_WORD_FOUND" in raw_response:
        print("Gemini did not find a high-quality word. Applying local JSON curated fallback...")
        curated_word_block = get_curated_word_fallback()
        # Find where the word section starts and replace it
        split_marker = "📚 Daily Econ Word (Education Bonus):"
        if split_marker in raw_response:
            parts = raw_response.split(split_marker)
            # Replace everything after the marker with the curated JSON word block
            raw_response = parts[0] + curated_word_block
        else:
            # If the output format was slightly mangled, append it cleanly to the end
            raw_response = raw_response.replace("NO_WORTH_READING_WORD_FOUND", "").strip() + "\n\n" + curated_word_block

    return raw_response


def send_to_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    # --- 1. DYNAMICALLY SCAN ALL ACTIVE CHANNEL ENVS ---
    # Scans all system environment variables starting with "CHANNEL_ID" (e.g. CHANNEL_ID, CHANNEL_ID_2, CHANNEL_ID_3)
    active_channels = []
    for key, value in os.environ.items():
        if key.startswith("CHANNEL_ID"):
            clean_value = value.strip() if value else ""
            if clean_value:
                active_channels.append(clean_value)

    # De-duplicate the list in case the same ID is used across different keys
    active_channels = list(set(active_channels))

    if not active_channels:
        print("Warning: No active CHANNEL_ID environment variables found.")
        return

    # --- 2. DISPATCH MESSAGES SAFELY ---
    for chat_id in active_channels:
        payload = {
            "chat_id": chat_id,
            "text": message
        }

        try:
            result = requests.post(url, json=payload)
            result.raise_for_status()
            print(f"Successfully posted to Telegram channel: {chat_id}")
        except Exception as e:
            print(f"Failed to post to Telegram channel {chat_id}: {e}")


def main():
    print("Getting news...")

    articles = get_news()

    print(f"Found {len(articles)} articles")

    summary = summarize_news(articles)

    snapshot = get_market_snapshot()

    final_message = f"""{summary}

{snapshot}"""

    print("Summary created")

    send_to_telegram(final_message)

    print("Posted to Telegram")


if __name__ == "__main__":
    main()
