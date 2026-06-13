"""
╔══════════════════════════════════════════╗
║   CRYPTO NEWS AUTO-TRANSLATOR BOT v2     ║
║   Channel @news_crypto → Roman Urdu      ║
║   No login needed — just 2 env vars!     ║
╚══════════════════════════════════════════╝
"""

import os, time, json, requests, anthropic
from bs4 import BeautifulSoup
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# ── Config ─────────────────────────────────────────
BOT_TOKEN      = os.environ['BOT_TOKEN']
CHAT_ID        = int(os.environ['CHAT_ID'])
CLAUDE_KEY     = os.environ['ANTHROPIC_API_KEY']
CHANNEL        = os.environ.get('CHANNEL', 'news_crypto')
CHECK_EVERY    = int(os.environ.get('CHECK_EVERY_SECONDS', '180'))  # 3 min default

SEEN_FILE      = 'seen.json'
claude         = anthropic.Anthropic(api_key=CLAUDE_KEY)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

# ── Seen messages ──────────────────────────────────
def load_seen():
    try:
        with open(SEEN_FILE) as f: return set(json.load(f))
    except: return set()

def save_seen(seen):
    with open(SEEN_FILE, 'w') as f:
        json.dump(list(seen)[-300:], f)

# ── Fetch channel posts ────────────────────────────
def fetch_posts():
    url = f"https://t.me/s/{CHANNEL}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')
        posts = []

        for wrap in soup.find_all('div', class_='tgme_widget_message_wrap'):
            text_el = wrap.find('div', class_='tgme_widget_message_text')
            date_el = wrap.find('a', class_='tgme_widget_message_date')
            if not text_el: continue

            text = text_el.get_text('\n').strip()
            href = date_el['href'] if date_el else ''
            post_id = href.rstrip('/').split('/')[-1] if href else text[:30]
            posts.append({'id': str(post_id), 'text': text})

        return posts
    except Exception as e:
        print(f"❌ Fetch error: {e}")
        return []

# ── Skip filter ────────────────────────────────────
def worth_translating(text):
    if len(text.strip()) < 25: return False
    words = [w for w in text.split() if w.isalpha() and len(w) > 1]
    return len(words) >= 4

# ── Claude translate ───────────────────────────────
def translate(text):
    try:
        r = claude.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=700,
            messages=[{"role": "user", "content": f"""Yeh crypto/trading news ko Roman Urdu mein analyze karo.
SIRF yeh format use karo — koi extra text nahi:

🔄 <b>TARJUMA:</b>
[Roman Urdu translation — 1-2 lines]

💡 <b>SAMJHAO:</b>
[Simple explanation — 2-3 lines, jaise dost ko samjhao]

📊 <b>MARKET:</b> Bullish 📈 / Bearish 📉 / Neutral ⚖️
[Wajah — ek line]

⚡ <b>MAIN BAAT:</b>
[Sabse important cheez — ek sentence]

News yeh hai:
\"{text[:600]}\""""}]
        )
        return r.content[0].text
    except Exception as e:
        return f"⚠️ Translation error: {e}"

# ── Send to Telegram ───────────────────────────────
def notify(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        r = requests.post(url, json={
            'chat_id': CHAT_ID,
            'text': text,
            'parse_mode': 'HTML',
            'disable_web_page_preview': True
        }, timeout=15)
        return r.json().get('ok', False)
    except Exception as e:
        print(f"❌ Notify error: {e}")
        return False

# ── Main loop ──────────────────────────────────────
def main():
    mins = CHECK_EVERY // 60
    print(f"\n🚀 Trading News AI Bot — Starting")
    print(f"📡 Channel : @{CHANNEL}")
    print(f"⏱  Interval: har {mins} minute\n")

    seen = load_seen()

    notify(f"""🟢 <b>Trading News AI — ONLINE!</b>

📡 <b>Channel:</b> @{CHANNEL}
🤖 <b>AI:</b> Claude Sonnet
⏱  <b>Check:</b> Har {mins} minute

<i>Ab har nai crypto news automatically Roman Urdu mein tere paas ayegi! 🚀</i>

<code>Start: {datetime.now().strftime('%Y-%m-%d %H:%M')}</code>""")

    while True:
        try:
            posts = fetch_posts()
            new_posts = [p for p in posts if p['id'] not in seen]

            if new_posts:
                print(f"📩 {len(new_posts)} naye posts!")
                for post in new_posts[-5:]:   # max 5 at once
                    text = post['text']
                    seen.add(post['id'])

                    if not worth_translating(text):
                        continue

                    print(f"🔄 Translating: {text[:70]}...")
                    translation = translate(text)
                    preview = text[:380] + ('…' if len(text) > 380 else '')

                    msg = f"""📡 <b>CRYPTO NEWS — {datetime.now().strftime('%I:%M %p')}</b>
━━━━━━━━━━━━━━━━━━

📰 <b>Original:</b>
<code>{preview}</code>

━━━━━━━━━━━━━━━━━━
{translation}
━━━━━━━━━━━━━━━━━━
<i>🤖 @{CHANNEL} → Trading News AI</i>"""

                    ok = notify(msg)
                    print("✅ Sent!" if ok else "❌ Failed")
                    time.sleep(3)

                save_seen(seen)
            else:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Koi nai post nahi.")

        except Exception as e:
            print(f"❌ Loop error: {e}")

        time.sleep(CHECK_EVERY)

if __name__ == '__main__':
    main()
