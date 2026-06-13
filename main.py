"""
Crypto News Auto-Translator Bot
Render Free Web Service version
"""

import os, time, json, requests, threading, anthropic
from bs4 import BeautifulSoup
from datetime import datetime
from flask import Flask
from dotenv import load_dotenv

load_dotenv()

# ── Config ─────────────────────────────────
BOT_TOKEN   = os.environ['BOT_TOKEN']
CHAT_ID     = int(os.environ['CHAT_ID'])
CLAUDE_KEY  = os.environ['ANTHROPIC_API_KEY']
CHANNEL     = os.environ.get('CHANNEL', 'news_crypto')
CHECK_EVERY = int(os.environ.get('CHECK_EVERY_SECONDS', '180'))

SEEN_FILE = '/tmp/seen.json'
claude    = anthropic.Anthropic(api_key=CLAUDE_KEY)
app       = Flask(__name__)

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

# ── Flask routes (keep alive) ───────────────
@app.route('/')
def home():
    return f"✅ Crypto News Bot Live! | Channel: @{CHANNEL}"

@app.route('/health')
def health():
    return {"status": "running", "channel": CHANNEL}, 200

# ── Seen messages ───────────────────────────
def load_seen():
    try:
        with open(SEEN_FILE) as f: return set(json.load(f))
    except: return set()

def save_seen(seen):
    with open(SEEN_FILE, 'w') as f:
        json.dump(list(seen)[-300:], f)

# ── Fetch channel posts ─────────────────────
def fetch_posts():
    try:
        r = requests.get(f"https://t.me/s/{CHANNEL}", headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')
        posts = []
        for wrap in soup.find_all('div', class_='tgme_widget_message_wrap'):
            text_el = wrap.find('div', class_='tgme_widget_message_text')
            date_el = wrap.find('a', class_='tgme_widget_message_date')
            if not text_el: continue
            text    = text_el.get_text('\n').strip()
            href    = date_el['href'] if date_el else ''
            post_id = href.rstrip('/').split('/')[-1] if href else text[:30]
            posts.append({'id': str(post_id), 'text': text})
        return posts
    except Exception as e:
        print(f"❌ Fetch error: {e}")
        return []

# ── Claude translate ────────────────────────
def translate(text):
    try:
        r = claude.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=700,
            messages=[{"role": "user", "content": f"""Yeh crypto/trading news ko Roman Urdu mein samjhao.
SIRF yeh format use karo:

🔄 <b>TARJUMA:</b>
[Roman Urdu translation]

💡 <b>SAMJHAO:</b>
[2-3 lines simple explanation]

📊 <b>MARKET:</b> Bullish 📈 / Bearish 📉 / Neutral ⚖️
[Ek line wajah]

⚡ <b>MAIN BAAT:</b>
[Ek sentence]

News: \"{text[:600]}\""""}]
        )
        return r.content[0].text
    except Exception as e:
        return f"⚠️ Translation error: {e}"

# ── Send to Telegram ────────────────────────
def notify(text):
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={'chat_id': CHAT_ID, 'text': text,
                  'parse_mode': 'HTML', 'disable_web_page_preview': True},
            timeout=15
        )
        return r.json().get('ok', False)
    except: return False

# ── Bot main loop ───────────────────────────
def bot_loop():
    time.sleep(5)  # wait for flask to start
    print(f"🚀 Bot loop starting — monitoring @{CHANNEL}")

    seen = load_seen()
    notify(f"""🟢 <b>Crypto News Bot — ONLINE!</b>

📡 Channel: @{CHANNEL}
🤖 Claude AI: Active
⏱ Check: Har {CHECK_EVERY//60} minute

<i>Ab har nai news Roman Urdu mein tere paas ayegi! 🚀</i>""")

    while True:
        try:
            posts   = fetch_posts()
            new_ones = [p for p in posts if p['id'] not in seen]

            if new_ones:
                print(f"📩 {len(new_ones)} naye posts!")
                for post in new_ones[-5:]:
                    text = post['text']
                    seen.add(post['id'])
                    if len(text.strip()) < 25: continue

                    print(f"🔄 Translating: {text[:60]}...")
                    translation = translate(text)
                    preview = text[:380] + ('…' if len(text) > 380 else '')

                    msg = f"""📡 <b>CRYPTO NEWS — {datetime.now().strftime('%I:%M %p')}</b>
━━━━━━━━━━━━━━━━

📰 <b>Original:</b>
<code>{preview}</code>

━━━━━━━━━━━━━━━━
{translation}
━━━━━━━━━━━━━━━━
<i>🤖 @{CHANNEL} → Corecrypto News Bot</i>"""

                    ok = notify(msg)
                    print("✅ Sent!" if ok else "❌ Failed")
                    time.sleep(3)

                save_seen(seen)
            else:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] No new posts.")

        except Exception as e:
            print(f"❌ Error: {e}")

        time.sleep(CHECK_EVERY)

# ── Start ───────────────────────────────────
if __name__ == '__main__':
    t = threading.Thread(target=bot_loop, daemon=True)
    t.start()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
