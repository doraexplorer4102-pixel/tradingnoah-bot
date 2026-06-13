import os
import asyncio
import ssl
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
    InputMediaVideo
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)
from telegram.constants import ParseMode
import pg8000.native

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AQ.Ab8RN6I9TTCCG9XXHQjlvZtNacGmtCL-C4m1Sb0PMl8B1gfohQ")
GEMINI_URL     = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-latest:generateContent"

TOKEN        = "8972809832:AAHKRaXFTjyVvCSgQP7Rfcrk97vRXL2nO90"
VIP_LINK     = "https://t.me/+H3isrme8c3BiNDg1"
AFFILIATE    = "https://broker-qx.pro/sign-up/?lid=1504736"
SUPPORT      = "https://t.me/TRADELIKENOAH"
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:DEfYBWltENxssYQNpworlKPeKVSKUuyQ@acela.proxy.rlwy.net:19828/railway")
MIN_DEPOSIT  = 20
OWNER_ID     = int(os.getenv("OWNER_ID", "8837911637"))

VIDEO_TUTORIAL = "BAACAgUAAxkBAAFMR_JqLHQgDfdvetmVFCu4tVoEmXayHwACkSEAAm6QYFUZ3EZET5TOdjwE"
VIDEO_REMINDER = "BAACAgUAAxkBAAFMQIxqLCy8iLgzzjwMiMFm4ahJi-N-iwACQCQAAmS9YFWS4sMNJoZYFjwE"
VIDEO_DEPOSIT  = "BQACAgUAAxkBAAFMQI5qLCzLxgL0oM6v_DRoWsq0R6ecMAACQiQAAmS9YFXmR4aJiqZyKjwE"
BONUS_PHOTO    = "AgACAgUAAxkBAAIIE2osaUQb9q2xShFHMQQXqQOhpy6IAAKaE2sbeuFgVY1Aj7qvPgy_AQADAgADeQADPAQ"

def pe(eid, fb): return f'<tg-emoji emoji-id="{eid}">{fb}</tg-emoji>'

E_FIRE    = pe("5424972470023104089", "🔥")
E_DIAMOND = pe("5427168083074628963", "💎")
E_ROCKET  = pe("5188481279963715781", "🚀")
E_MONEY   = pe("5224257782013769471", "💰")
E_STAR    = pe("5438496463044752972", "⭐")
E_CROWN   = pe("5217822164362739968", "👑")
E_TROPHY  = pe("5413566144986503832", "🏆")
E_CHART   = pe("5244837092042750681", "📈")
E_GIFT    = pe("5203996991054432397", "🎁")
E_CHECK   = pe("5206607081334906820", "✅")
E_CROSS   = pe("5210952531676504517", "❌")
E_WARN    = pe("5420323339723881652", "⚠️")
E_KEY     = pe("5307843983102204243", "🔑")
E_LINK    = pe("5271604874419647061", "🔗")
E_PHONE   = pe("5253742260054409879", "✉️")
E_CLOCK   = pe("5431807687136395567", "⏰")
E_PARTY   = pe("5461151367559141950", "🎉")
E_HAND    = pe("5305522282695768654", "👇")
E_EYES    = pe("5210956306952758910", "👀")
E_THUMBS  = pe("5337080053119336309", "👍")
E_CHAT    = pe("5443038326535759644", "💬")
E_GLOBE   = pe("5224450179368767019", "🌍")
E_NEW     = pe("5382357040008021292", "🆕")
E_PERSON  = pe("5217797330861826981", "👩‍💻")

user_state: dict = {}
ai_history: dict = {}  # Stores per-user conversation history for Gemini

AI_SYSTEM_PROMPT = """You are a helpful assistant for Trading Noah Bot — a Telegram bot run by Noah, a professional trader.

Your job is to chat with users in a friendly, natural way. Users may write in Hindi, English, or Hinglish (mix of both). Always reply in the SAME language the user writes in. If they write in Hindi, reply in Hindi. If English, reply in English. If Hinglish, reply in Hinglish.

Key information about this bot:
- Noah is a professional Quotex trader who runs VIP trading signals
- To join VIP, users must register on Quotex using Noah's link and deposit minimum $20
- VIP gives access to 10-20 daily sureshot trading signals
- Promo code NOAH50 gives 50% deposit bonus
- Support contact: @TRADELIKENOAH

Your rules:
1. Be friendly, casual and encouraging like a helpful friend
2. Always push users toward registering on Quotex and joining VIP
3. If someone asks about VIP, tell them to register and deposit $20 minimum
4. If someone asks about signals, tell them VIP members get 10-20 daily signals
5. Keep replies SHORT — max 3-4 lines
6. Use emojis naturally
7. Never share personal info or make up trading results
8. If someone seems confused, guide them to click the buttons in the bot"""


async def ask_gemini(chat_id: int, user_text: str) -> str:
    """Send message to Gemini and return reply, keeping conversation history"""
    import json, urllib.request, urllib.error
    # Keep last 10 messages per user to stay within free limits
    if chat_id not in ai_history:
        ai_history[chat_id] = []
    ai_history[chat_id].append({"role": "user", "parts": [{"text": user_text}]})
    if len(ai_history[chat_id]) > 10:
        ai_history[chat_id] = ai_history[chat_id][-10:]
    payload = json.dumps({
        "system_instruction": {"parts": [{"text": AI_SYSTEM_PROMPT}]},
        "contents": ai_history[chat_id]
    }).encode("utf-8")
    try:
        loop = asyncio.get_event_loop()
        def call_gemini():
            req = urllib.request.Request(
                GEMINI_URL,
                data=payload,
                headers={
                    "Content-Type": "application/json",
                    "X-goog-api-key": GEMINI_API_KEY
                },
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read())
        data = await loop.run_in_executor(None, call_gemini)
        reply = data["candidates"][0]["content"]["parts"][0]["text"].strip()
        ai_history[chat_id].append({"role": "model", "parts": [{"text": reply}]})
        print(f"✅ Gemini replied to chat {chat_id}")
        return reply
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        print(f"Gemini HTTP error {e.code}: {body}")
        return "Sorry bro, AI is busy right now. Please try again in a moment! 🙏"
    except Exception as e:
        print(f"Gemini error: {type(e).__name__}: {e}")
        return "Sorry bro, AI is busy right now. Please try again in a moment! 🙏"

def get_db():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    url = DATABASE_URL.replace("postgresql://", "").replace("postgres://", "")
    userpass, rest = url.split("@", 1)
    user, password = userpass.split(":", 1)
    hostport, database = rest.split("/", 1)
    host, port = (hostport.split(":") + ["5432"])[:2]
    return pg8000.native.Connection(
        host=host, port=int(port), user=user,
        password=password, database=database, ssl_context=ctx
    )

def db_get_trader(uid):
    try:
        conn = get_db()
        rows = conn.run("SELECT uid, deposit FROM verified_traders WHERE uid = :uid", uid=uid)
        conn.close()
        if rows:
            return {"uid": rows[0][0], "deposit": float(rows[0][1] or 0)}
        return None
    except Exception as e:
        print(f"DB error: {e}")
        return None


def db_save_trader(uid, deposit=0.0, status="", country=""):
    try:
        conn = get_db()
        conn.run("""
            INSERT INTO verified_traders (uid, deposit, status, country, updated_at)
            VALUES (:uid, :dep, :status, :country, NOW())
            ON CONFLICT (uid) DO UPDATE SET
                deposit = GREATEST(verified_traders.deposit, EXCLUDED.deposit),
                status = EXCLUDED.status,
                updated_at = NOW()
        """, uid=uid, dep=float(deposit), status=status, country=country)
        conn.close()
        print(f"✅ Saved trader: {uid} dep=${deposit} status={status}")
    except Exception as e:
        print(f"DB save error: {e}")


def db_save_reminder_state(chat_id, reminder_num, started_at):
    """Save reminder state to DB so it survives restarts"""
    try:
        conn = get_db()
        conn.run("""
            INSERT INTO reminder_state (chat_id, reminder_num, started_at, updated_at)
            VALUES (:chat_id, :reminder_num, :started_at, NOW())
            ON CONFLICT (chat_id) DO UPDATE SET
                reminder_num = EXCLUDED.reminder_num,
                started_at = EXCLUDED.started_at,
                updated_at = NOW()
        """, chat_id=str(chat_id), reminder_num=reminder_num, started_at=started_at)
        conn.close()
    except Exception as e:
        print(f"DB reminder save error: {e}")

def db_get_all_reminders():
    """Get all active reminder states from DB"""
    try:
        conn = get_db()
        rows = conn.run("SELECT chat_id, reminder_num, started_at FROM reminder_state")
        conn.close()
        return rows or []
    except Exception as e:
        print(f"DB reminder get error: {e}")
        return []

def db_delete_reminder(chat_id):
    """Remove reminder state when user joins VIP"""
    try:
        conn = get_db()
        conn.run("DELETE FROM reminder_state WHERE chat_id = :chat_id", chat_id=str(chat_id))
        conn.close()
    except Exception as e:
        print(f"DB reminder delete error: {e}")

def db_create_tables():
    """Create tables if they don't exist"""
    try:
        conn = get_db()
        conn.run("""
            CREATE TABLE IF NOT EXISTS reminder_state (
                chat_id TEXT PRIMARY KEY,
                reminder_num INTEGER DEFAULT 1,
                started_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
        """)
        conn.close()
        print("✅ Tables ready")
    except Exception as e:
        print(f"DB table creation error: {e}")

def get_state(chat_id):
    if chat_id not in user_state:
        user_state[chat_id] = {"step": "start", "trader_id": None, "deposit": 0.0, "reminder_task": None}
    return user_state[chat_id]

def cancel_reminder(state, chat_id=None):
    if state.get("reminder_task") and not state["reminder_task"].done():
        state["reminder_task"].cancel()
    if chat_id:
        db_delete_reminder(chat_id)

def support_btn():
    return InlineKeyboardButton("✉️ Contact Support 24/7", url=SUPPORT, style="primary")

def register_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔗 REGISTER FREE NOW ⭐", url=AFFILIATE, style="danger")],
        [InlineKeyboardButton("🔑 I HAVE REGISTERED ✨", callback_data="registered", style="success")],
        [InlineKeyboardButton("✉️ CONTACT SUPPORT 24/7", url=SUPPORT, style="primary")],
    ])

def deposit_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎁 Claim 50% Bonus NOW", callback_data="claim_bonus", style="success")],
        [InlineKeyboardButton("📹 How To Deposit (Tutorial)", callback_data="tutorial", style="primary")],
        [InlineKeyboardButton("🔄 I Have Deposited (Re-Check)", callback_data="deposited", style="danger")],
        [InlineKeyboardButton("✉️ Contact Support 24/7", url=SUPPORT, style="primary")],
    ])

def reject_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔗 Register With Our Link", url=AFFILIATE, style="danger")],
        [InlineKeyboardButton("🔄 Try Again With Correct ID", callback_data="try_again", style="success")],
        [InlineKeyboardButton("✉️ Contact Support 24/7", url=SUPPORT, style="primary")],
    ])

def reminder_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 Create Free Account Now", url=AFFILIATE, style="success")],
        [InlineKeyboardButton("🔥 Click Here To Join VIP", url=AFFILIATE, style="danger")],
        [InlineKeyboardButton("✉️ Contact Support 24/7", url=SUPPORT, style="primary")],
    ])

def bonus_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💰 Deposit Now & Get 50% Bonus", url=AFFILIATE, style="danger")],
        [InlineKeyboardButton("📹 How To Deposit (Tutorial)", callback_data="tutorial", style="primary")],
        [InlineKeyboardButton("✅ I Have Deposited", callback_data="deposited", style="success")],
        [InlineKeyboardButton("✉️ Contact Support 24/7", url=SUPPORT, style="primary")],
    ])

def vip_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👑 JOIN VIP SIGNALS GROUP 🏆", url=VIP_LINK, style="danger")],
        [InlineKeyboardButton("✉️ Contact Support 24/7", url=SUPPORT, style="primary")],
    ])

def support_keyboard():
    return InlineKeyboardMarkup([[support_btn()]])

def recheck_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💰 Deposit Now", url=AFFILIATE, style="danger")],
        [InlineKeyboardButton("🔄 I Have Deposited (Re-Check)", callback_data="deposited", style="success")],
        [InlineKeyboardButton("✉️ Contact Support 24/7", url=SUPPORT, style="primary")],
    ])



# ─── REMINDER CAPTIONS ────────────────────────────────────────────
REM1_CAP = '<b><tg-emoji emoji-id="5397782960512444700">📌</tg-emoji> ZERO TO HERO JOURNEY VIDEO <tg-emoji emoji-id="5397782960512444700">📌</tg-emoji>\n<tg-emoji emoji-id="5274099962655816924">❗️</tg-emoji><tg-emoji emoji-id="5274099962655816924">❗️</tg-emoji><tg-emoji emoji-id="5274099962655816924">❗️</tg-emoji><tg-emoji emoji-id="5274099962655816924">❗️</tg-emoji><tg-emoji emoji-id="5274099962655816924">❗️</tg-emoji><tg-emoji emoji-id="5274099962655816924">❗️</tg-emoji><tg-emoji emoji-id="5274099962655816924">❗️</tg-emoji><tg-emoji emoji-id="5274099962655816924">❗️</tg-emoji>\n\nhttps://youtu.be/q1a8FZ8T4XU?si=bMvgGhQ1Ru6nLayx\n\n👆👆 WATCH MY TRADING JOURNEY VIDEO\n( MUST WATCH ) <tg-emoji emoji-id="5424972470023104089">🔥</tg-emoji> 📣</b>'
REM2_CAP = """<b><tg-emoji emoji-id="5395695537687123235">🚨</tg-emoji> DON'T SKIP | VIDEO OPEN KAR <tg-emoji emoji-id="5395695537687123235">🚨</tg-emoji>\n<tg-emoji emoji-id="5210956306952758910">👀</tg-emoji> Proof dekh le pehle, phir decision lena\n\n<tg-emoji emoji-id="5231200819986047254">📊</tg-emoji> TODAY'S LIVE TRADING RESULTS\n\n<tg-emoji emoji-id="5402477260982731644">☀️</tg-emoji> Morning Session\n<tg-emoji emoji-id="6185707729009512236">👉</tg-emoji> 2 Signals → 2/2 WIN\n<tg-emoji emoji-id="5210952531676504517">❌</tg-emoji> No Martingale | <tg-emoji emoji-id="5424972470023104089">🔥</tg-emoji> Deep Win\n\n<tg-emoji emoji-id="5402477260982731644">☀️</tg-emoji> Afternoon Session\n<tg-emoji emoji-id="6185707729009512236">👉</tg-emoji> 2 Signals → 2/2 WIN\n<tg-emoji emoji-id="5210952531676504517">❌</tg-emoji> No Martingale | <tg-emoji emoji-id="5427168083074628963">💎</tg-emoji> Deep Win\n\n<tg-emoji emoji-id="5449569374065152798">🌛</tg-emoji> Evening Session\n<tg-emoji emoji-id="6185707729009512236">👉</tg-emoji> 3 Signals\n<tg-emoji emoji-id="5389006967937184376">🤔</tg-emoji> 3 Direct Win\n<tg-emoji emoji-id="5210952531676504517">❌</tg-emoji> No Martingale | <tg-emoji emoji-id="5427168083074628963">💎</tg-emoji> Deep Win\n\n<tg-emoji emoji-id="5210956306952758910">👀</tg-emoji> YESTERDAY RESULT\n- 17 WIN / 0 LOSS <tg-emoji emoji-id="5424972470023104089">🔥</tg-emoji><tg-emoji emoji-id="5409048419211682843">💵</tg-emoji><tg-emoji emoji-id="5244837092042750681">📈</tg-emoji>\n\n<tg-emoji emoji-id="5443038326535759644">💬</tg-emoji> VIP join karna hai?\n<tg-emoji emoji-id="5253742260054409879">✉️</tg-emoji> Message “VIP” <tg-emoji emoji-id="5416117059207572332">➡️</tg-emoji> @TRADELIKENOAH</b>"""
REM3_CAP = '<b>TRADER OF THE WEEK <tg-emoji emoji-id="5316961893728926221">🦁</tg-emoji><tg-emoji emoji-id="5413566144986503832">🏆</tg-emoji>\n<tg-emoji emoji-id="5274099962655816924">❗️</tg-emoji><tg-emoji emoji-id="5274099962655816924">❗️</tg-emoji><tg-emoji emoji-id="5274099962655816924">❗️</tg-emoji><tg-emoji emoji-id="5274099962655816924">❗️</tg-emoji><tg-emoji emoji-id="5274099962655816924">❗️</tg-emoji><tg-emoji emoji-id="5274099962655816924">❗️</tg-emoji><tg-emoji emoji-id="5274099962655816924">❗️</tg-emoji><tg-emoji emoji-id="5274099962655816924">❗️</tg-emoji>\n\nhttps://youtu.be/q1a8FZ8T4XU?si=bMvgGhQ1Ru6nLayx\n\n👆👆 WATCH HOW I MADE $40,000\n( ₹35,00,000 ) IN A WEEK <tg-emoji emoji-id="5424972470023104089">🔥</tg-emoji><tg-emoji emoji-id="5395695537687123235">🚨</tg-emoji></b>'
REM4_CAP = '<b>₹1,000 se ₹5,00,000 — sirf mere VIP signals follow karke <tg-emoji emoji-id="5409048419211682843">💵</tg-emoji><tg-emoji emoji-id="5244837092042750681">📈</tg-emoji>\n\nYe koi kahani nahi, real results hain. <tg-emoji emoji-id="5224607267797606837">☄️</tg-emoji>\n\nMy VIP member booked Z900 bike <tg-emoji emoji-id="5260295181852225992">😱</tg-emoji><tg-emoji emoji-id="5256228126995787725">🏍</tg-emoji>\n\n<tg-emoji emoji-id="5264919878082509254">▶️</tg-emoji> LIVE VIDEO PROOF CHECK NOW 👆👆\n\nAaj bhi agar tum VIP channel join nahi kar rahe,\ntoh honestly tum apna hi nuksaan kar rahe ho.\n\n⌛ Time waste mat karo.\n<tg-emoji emoji-id="5188481279963715781">🚀</tg-emoji> Next success story tumhari ho sakti hai\n\n<tg-emoji emoji-id="5253742260054409879">✉️</tg-emoji> JOIN NOW — Message me “VIP”\n<tg-emoji emoji-id="5201990176175299013">📱</tg-emoji> MESSAGE HERE <tg-emoji emoji-id="5416117059207572332">➡️</tg-emoji> @TRADELIKENOAH</b>'
REM5_CAP = '<b>Bhai, aaj is photo mein tu mere maa-baap ko dekh raha hoga <tg-emoji emoji-id="5337080053119336309">👍</tg-emoji>\nUnke face ki khushi notice kar… aaj woh kitna proud feel karte hain <tg-emoji emoji-id="5391320026869408028">🫂</tg-emoji>\nUnhone mere saath kitni gaadiyaan dekhi <tg-emoji emoji-id="5253752975997803460">🚘</tg-emoji>\nKitni jagah world mein ghoome <tg-emoji emoji-id="5224450179368767019">🌍</tg-emoji>\nAaj woh khud bolte hain — “tere jaisa beta sabko mile.”\n\nLekin sach kya hai?\nYeh sab ek din mein nahi hua.\nIske peeche sirf ek cheez thi — PAISA <tg-emoji emoji-id="5409048419211682843">💵</tg-emoji>\n\nAgar tu bhi chahta hai ki ek din tere maa-baap bhi proud feel karein,\nLog bolein — “Bhai, kya beta paida kiya hai!”\n\nAur agar tujhe genuinely paisa kamana hai,\nHigh quality trading signals chahiye,\nToh abhi meri ID par message kar — “ VIP ” <tg-emoji emoji-id="5416117059207572332">➡️</tg-emoji> @TRADELIKENOAH</b>'
REM_BTN_PLAY = '▶️ Watch Video Click Here'
REM_BTN_KEY = '🔑 Register Your Account'
REM_BTN_MAIL = '✉️ Contact Support 24/7'

async def send_one_reminder(chat_id, bot, reminder_num):
    """Send a single reminder by number (1-5)"""
    r1_cap = REM1_CAP
    r2_cap = REM2_CAP
    r3_cap = REM3_CAP
    r4_cap = REM4_CAP
    r5_cap = REM5_CAP
    yt = "https://youtu.be/q1a8FZ8T4XU?si=bMvgGhQ1Ru6nLayx"
    btn_13 = InlineKeyboardMarkup([
        [InlineKeyboardButton(REM_BTN_PLAY, url=yt, style="danger")],
        [InlineKeyboardButton(REM_BTN_KEY, callback_data="registered", style="success")],
        [InlineKeyboardButton(REM_BTN_MAIL, url=SUPPORT, style="primary")],
    ])
    btn_245 = InlineKeyboardMarkup([
        [InlineKeyboardButton(REM_BTN_KEY, callback_data="registered", style="success")],
        [InlineKeyboardButton(REM_BTN_MAIL, url=SUPPORT, style="primary")],
    ])
    try:
        if reminder_num == 1:
            await bot.send_photo(chat_id=chat_id, photo="AgACAgUAAxkBAAIIhmosfzneQ76I3CuhlSHtj80p5vazAALCEGsbrGtoVSAOT8CWevovAQADAgADeQADPAQ", caption=r1_cap, parse_mode="HTML")
            await bot.send_video_note(chat_id=chat_id, video_note="DQACAgUAAxkBAAFMSQhqLIb67doN1uewmuPt5oUt44kzOQACdR4AAqxraFW9yKKdMgc2AjwE", reply_markup=btn_13)
        elif reminder_num == 2:
            await bot.send_video(chat_id=chat_id, video="BAACAgUAAxkBAAFMSPJqLIWlmSn5W5Vl0YtME2reEchEvgACoB0AAmnTSFQUiVIEIzqvlDwE", caption=r2_cap, parse_mode="HTML", reply_markup=btn_245)
        elif reminder_num == 3:
            await bot.send_photo(chat_id=chat_id, photo="AgACAgUAAxkBAAIIh2osfzsGVAMzCEnZf_8G2pjVFN3oAALDEGsbrGtoVYaoZ4WKYIjGAQADAgADeQADPAQ", caption=r3_cap, parse_mode="HTML")
            await bot.send_video_note(chat_id=chat_id, video_note="DQACAgUAAxkBAAFMSQpqLIcHtKjTGEyoV6FLw6eHtiakFAACdh4AAqxraFXB9SIHnO1XujwE", reply_markup=btn_13)
        elif reminder_num == 4:
            await bot.send_video(chat_id=chat_id, video="BAACAgUAAxkBAAFMSPZqLIWx4pTuzb98rHinaimoXeAyUQACnCEAAtCiOFSei_vCioOGDzwE", caption=r4_cap, parse_mode="HTML", reply_markup=btn_245)
        elif reminder_num == 5:
            await bot.send_photo(chat_id=chat_id, photo="AgACAgUAAxkBAAIIoWoshS8UEUP49vFEPnYbcVsdp1G7AALEEGsbrGtoVeld-Rt8y727AQADAgADeQADPAQ", caption=r5_cap, parse_mode="HTML", reply_markup=btn_245)
    except Exception as e:
        print(f"Reminder {reminder_num} error: {e}")


async def send_reminder(chat_id, bot, start_reminder_num=1, sleep_first=True):
    """Send 5 reminders every 3 hours in an infinite loop - survives restarts via DB"""
    from datetime import datetime
    reminder_num = start_reminder_num
    while True:
        state = get_state(chat_id)
        if state.get("step") == "done":
            db_delete_reminder(chat_id)
            return

        if sleep_first:
            await asyncio.sleep(10800)  # Wait 3 hours
        sleep_first = True  # Always sleep after first iteration

        state = get_state(chat_id)
        if state.get("step") == "done":
            db_delete_reminder(chat_id)
            return

        # Save current reminder number to DB before sending
        db_save_reminder_state(chat_id, reminder_num, datetime.now(datetime.UTC).isoformat())

        await send_one_reminder(chat_id, bot, reminder_num)
        reminder_num = (reminder_num % 5) + 1

async def run_start_sequence(chat_id, bot, state):
    try:
        # ── SEQUENCE 1: Immediate ─────────────────────────────────────────
        # Sticker + video note + photo with buttons
        await bot.send_sticker(
            chat_id=chat_id,
            sticker="CAACAgUAAxkBAAFL9cVqKCa70-hZ2BsucTxBmLtRI2PFMAACBxIAArIYAAFXuG3a4VpEuLw7BA"
        )
        await bot.send_video_note(
            chat_id=chat_id,
            video_note="DQACAgUAAxkBAAMbaidRKZuu4TnoWbcqd3A_KLQByFEAAs4cAAJfGjFXsw34l8lliF47BA"
        )
        await bot.send_photo(
            chat_id=chat_id,
            photo="AgACAgUAAxkBAAMZaidQ8AAB-XcWZ92dfh1Nyj12vp9tAAL9D2sb2mc5VTJ5ySC9Sop4AQADAgADeQADOwQ",
            caption=(
                f"<b>{E_TROPHY} You're Here Because You Want To Earn Money {E_MONEY}\n\n"
                f"{E_HAND} Join My All Channels {E_CHART} Below & Recover Your Lifetime Losses\n\n"
                f"{E_FIRE} Start Earning Money Today {E_ROCKET}</b>"
            ),
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📈 FREE VIP GROUP", url="https://t.me/+s_guD0HJ0B9kYWM1", style="danger")],
                [InlineKeyboardButton("🎯 JOIN LOSS RECOVERY", url="https://t.me/+s_guD0HJ0B9kYWM1", style="primary")],
                [InlineKeyboardButton("💬 CONTACT SUPPORT 24/7", url=SUPPORT, style="success")],
            ])
        )

        # ── WAIT 3 MINUTES ────────────────────────────────────────────────
        await asyncio.sleep(180)

        # ── SEQUENCE 2: +3 min ────────────────────────────────────────────
        # Text message 1
        await bot.send_message(
            chat_id=chat_id,
            text=(
                f"<b>Hello {E_TROPHY} Are You Ready To Earn Money With Trading Without Experience\n\n"
                f"{E_CHART} I Helped 10,000+ New Members To Start EARNING {E_ROCKET}\n\n"
                f"{E_WARN} I Shared The Result Of My Client Earning With Me {E_HAND}</b>"
            ),
            parse_mode=ParseMode.HTML
        )

        # Photo/Video Album
        media = [
            InputMediaVideo(media="BAACAgUAAxkBAAMtaidXNeAzsfiXzbzTipXYriM1QccAAr4fAALaZzlV3a9DaWKShwg7BA"),
            InputMediaVideo(media="BAACAgUAAxkBAAMuaidXP2WTrAFQHjfNb2BEEyFIFNEAAr8fAALaZzlVMwnVMRZdSwQ7BA"),
            InputMediaVideo(media="BAACAgUAAxkBAAM2aidbF2H6x4MPd8yJvVaav3-1Rx0AAk4TAAKE-wlUE1J9aR22UGs7BA"),
            InputMediaPhoto(media="AgACAgUAAxkBAAMvaidZOKraitAwpTkzLOyuE8asGGQAAngOaxubnDlVOk0XXZUnDVsBAAMCAAN5AAM7BA"),
            InputMediaPhoto(media="AgACAgUAAxkBAAMwaidZOD-Rpe2T-663b06c3fSpQ6QAAnkOaxubnDlVadz6EiT1F0QBAAMCAAN5AAM7BA"),
            InputMediaPhoto(media="AgACAgUAAxkBAAMxaidZOCzrgkKfUKO130MGuwd8yi0AAnoOaxubnDlV4lsIOqHFWHUBAAMCAAN5AAM7BA"),
            InputMediaPhoto(media="AgACAgUAAxkBAAMyaidZOOj3QW-KF9u4jm0Q6p__negAAnsOaxubnDlVQwg-WgLkC_kBAAMCAAN5AAM7BA"),
            InputMediaPhoto(media="AgACAgUAAxkBAAMzaidZOJYjCJwT3jrBie1q3bftyPIAAnwOaxubnDlVm9pFyqPCuGgBAAMCAAN5AAM7BA"),
            InputMediaPhoto(media="AgACAgUAAxkBAAM0aidZOAIic1LUisuabVtoG-zjErcAAn0OaxubnDlVLe9EI0F79TwBAAMCAAN5AAM7BA"),
            InputMediaPhoto(media="AgACAgUAAxkBAAM1aidZONtvc134Omxzz_K_5ENML0EAAn4OaxubnDlVA7ThG7qOcGQBAAMCAAN3AAM7BA"),
        ]
        await bot.send_media_group(chat_id=chat_id, media=media)

        # Text message with button (name/country)
        await bot.send_message(
            chat_id=chat_id,
            text=(
                f"<b>{E_PERSON} Bro, What Is Your Name And What's Your Country? {E_GLOBE}\n\n"
                f"{E_NEW} It Will Help Us To Understand Each Other Better {E_TROPHY}</b>"
            ),
            parse_mode=ParseMode.HTML,
            reply_markup=support_keyboard()
        )

        # ── WAIT 4-5 MINUTES ──────────────────────────────────────────────
        await asyncio.sleep(270)  # 4.5 minutes

        # ── SEQUENCE 3: +4-5 min ──────────────────────────────────────────
        # Registration tutorial video
        await bot.send_video(
            chat_id=chat_id,
            video="BAACAgUAAxkBAAOKaidpD_-7HAnZ9D2d-yGBmsLMW_QAAjcYAAI1GzlXipdJ8rzcwTs7BA",
            caption=(
                f"<b>{E_MONEY} Okay, So To Start Earning {E_MONEY} The First Step Is To Register "
                f"A Trading Account {E_LINK}\n\n"
                f"{E_HAND} Watch The Video & Just Click On Here {E_HAND}</b>"
            ),
            parse_mode=ParseMode.HTML,
            reply_markup=register_keyboard()
        )

        from datetime import datetime
        db_save_reminder_state(chat_id, 1, datetime.now(datetime.UTC).isoformat())
        state["reminder_task"] = asyncio.create_task(send_reminder(chat_id, bot))

    except Exception as e:
        import traceback
        print(f"START SEQ ERROR: {e}")
        traceback.print_exc()

async def verify_id_then_respond(uid, chat_id, bot):
    state = get_state(chat_id)
    cancel_reminder(state, chat_id)

    msg = await bot.send_message(
        chat_id=chat_id,
        text=f"<b>{E_EYES} Verifying ID <code>{uid}</code>... Please wait!</b>",
        parse_mode=ParseMode.HTML
    )

    # Check DB instantly first
    trader = db_get_trader(uid)
    if not trader:
        # Wait max 10 seconds for postback
        for i in range(2):
            await asyncio.sleep(5)
            trader = db_get_trader(uid)
            if trader:
                break

    if not trader:
        state["step"] = "awaiting_id"
        await bot.edit_message_text(
            chat_id=chat_id, message_id=msg.message_id,
            text=(
                f"<b>{E_CROSS} Bro, this account is NOT registered through my link! {E_WARN}\n\n"
                f"Please re-check and send the correct Trader ID. {E_EYES}\n\n"
                f"{E_CHAT} Contact us anytime — our team is available 24/7! {E_CLOCK}</b>"
            ),
            parse_mode=ParseMode.HTML, reply_markup=reject_keyboard()
        )
        state["reminder_task"] = asyncio.create_task(send_reminder(chat_id, bot))
        return

    dep = trader["deposit"]
    state["trader_id"] = uid
    state["deposit"] = dep

    if dep >= MIN_DEPOSIT:
        state["step"] = "done"
        cancel_reminder(state)
        await bot.edit_message_text(
            chat_id=chat_id, message_id=msg.message_id,
            text=f"<b>{E_CHECK} ID <code>{uid}</code> verified! {E_PARTY} Deposit confirmed! {E_ROCKET}</b>",
            parse_mode=ParseMode.HTML
        )
        await bot.send_message(
            chat_id=chat_id,
            text=(
                f"<b>{E_PARTY} WELCOME TO VIP! {E_CROWN}\n\n"
                f"━━━━━━━━━━━━━━━━━━━\n\n"
                f"{E_TROPHY} You are now a verified VIP member!\n\n"
                f"{E_FIRE} Join our Exclusive VIP Signals Group NOW:\n\n"
                f"{E_DIAMOND} {VIP_LINK} {E_DIAMOND}\n\n"
                f"{E_CHART} Daily 10-20 Sureshot Trades\n"
                f"{E_MONEY} Daily 5-10 Compounding Signals\n"
                f"{E_STAR} All Trades 100% NON-MTG\n\n"
                f"{E_THUMBS} Welcome to the winning team! {E_TROPHY}</b>"
            ),
            parse_mode=ParseMode.HTML, reply_markup=vip_keyboard()
        )
    else:
        state["step"] = "awaiting_deposit"
        # If deposit exists but less than minimum, tell them directly
        if dep > 0 and dep < MIN_DEPOSIT:
            await bot.edit_message_text(
                chat_id=chat_id, message_id=msg.message_id,
                text=(
                    f"<b>{E_CHECK} ID <code>{uid}</code> verified! {E_WARN}\n\n"
                    f"Your current balance: <b>${dep:.2f}</b>\n\n"
                    f"{E_MONEY} You need to deposit minimum <b>${MIN_DEPOSIT}</b> to unlock VIP!\n\n"
                    f"Please deposit <b>${MIN_DEPOSIT - dep:.2f} more</b> and click Re-Check {E_HAND}</b>"
                ),
                parse_mode=ParseMode.HTML,
                reply_markup=recheck_keyboard()
            )
            return
        await bot.edit_message_text(
            chat_id=chat_id, message_id=msg.message_id,
            text=(
                f"<b>{E_CHECK} ID <code>{uid}</code> verified! {E_WARN}\n\n"
                f"ACCOUNT LINKED — $0.00 BALANCE\n\n"
                f"{E_EYES} Found your Quotex ID but balance is ZERO!\n\n"
                f"━━━━━━━━━━━━━━━━━━━\n\n"
                f"{E_GIFT} SPECIAL BONUS UNLOCKED! {E_PARTY}\n\n"
                f"{E_FIRE} Promo Code: <code>NOAH50</code> {E_FIRE}\n\n"
                f"{E_WARN} Expires in 15 minutes!\n\n"
                f"{E_MONEY} Deposit minimum $20 & click Re-Check {E_CHECK}</b>"
            ),
            parse_mode=ParseMode.HTML, reply_markup=deposit_keyboard()
        )
        try:
            await bot.send_document(
                chat_id=chat_id, document=VIDEO_DEPOSIT,
                caption=f"<b>👆 Watch this video to learn how to deposit!</b>",
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            print(f"Video send error: {e}")


async def preview_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Preview any reminder instantly - /preview1 through /preview5"""
    user_id = update.effective_user.id
    if user_id != 8837911637:
        return
    cmd = update.message.text.strip().lower()
    num = int(cmd.replace("/preview", "")) if cmd.replace("/preview", "").isdigit() else 0
    if num < 1 or num > 5:
        await update.message.reply_text("Use /preview1 to /preview5")
        return
    await update.message.reply_text(f"Sending reminder {num} preview...")
    await send_one_reminder(update.effective_chat.id, context.bot, num)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    state = get_state(chat_id)
    cancel_reminder(state, chat_id)
    state.update({"step": "start", "trader_id": None, "deposit": 0.0, "reminder_task": None})
    # Reminder is started ONLY inside run_start_sequence() after intro completes
    asyncio.create_task(run_start_sequence(chat_id, context.bot, state))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    state = get_state(chat_id)

    if query.data in ("registered", "reg"):
        cancel_reminder(state)
        state["step"] = "awaiting_id"
        await context.bot.send_photo(
            chat_id=chat_id,
            photo="AgACAgUAAxkBAAIIEmosaUSmxDt3tDTubZdjoVbnKAABagACKg9rG26QYFXDW2olgCUHtwEAAwIAA3kAAzwE",
            caption=(
                f"<b>{E_PARTY} Congratulations! You're just one step away! {E_FIRE}\n\n"
                f"━━━━━━━━━━━━━━━━━━━\n\n"
                f"{E_EYES} Follow these steps to find your Trader ID:\n\n"
                f"1️⃣ Open your <b>Quotex account</b>\n"
                f"2️⃣ Go to <b>My Account</b>\n"
                f"3️⃣ You will see your <b>Trader ID</b> there\n"
                f"4️⃣ Reply with that <b>8-digit code</b> {E_HAND}</b>"
            ),
            parse_mode=ParseMode.HTML,
            reply_markup=support_keyboard()
        )

    elif query.data == "try_again":
        state["step"] = "awaiting_id"
        await context.bot.send_photo(
            chat_id=chat_id,
            photo="AgACAgUAAxkBAAIIEmosaUSmxDt3tDTubZdjoVbnKAABagACKg9rG26QYFXDW2olgCUHtwEAAwIAA3kAAzwE",
            caption=(
                f"<b>🔄 Please send your correct Trader ID {E_EYES}\n\n"
                f"━━━━━━━━━━━━━━━━━━━\n\n"
                f"{E_EYES} Follow these steps to find your Trader ID:\n\n"
                f"1️⃣ Open your <b>Quotex account</b>\n"
                f"2️⃣ Go to <b>My Account</b>\n"
                f"3️⃣ You will see your <b>Trader ID</b> there\n"
                f"4️⃣ Reply with that <b>8-digit code</b> {E_HAND}</b>"
            ),
            parse_mode=ParseMode.HTML, reply_markup=support_keyboard()
        )

    elif query.data == "tutorial":
        await context.bot.send_video(
            chat_id=chat_id,
            video="BAACAgUAAxkBAAFMR_JqLHQgDfdvetmVFCu4tVoEmXayHwACkSEAAm6QYFUZ3EZET5TOdjwE",
            caption=(
                f"<b>{E_MONEY} How To Deposit Tutorial {E_CHART}\n\n"
                f"👆 Watch this video to learn how to deposit on Quotex!\n\n"
                f"{E_GIFT} Use code <code>NOAH50</code> for 50% bonus! {E_FIRE}</b>"
            ),
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💰 Deposit Now", url=AFFILIATE, style="danger")],
                [InlineKeyboardButton("🔄 I Have Deposited (Re-Check)", callback_data="deposited", style="success")],
                [InlineKeyboardButton("✉️ Contact Support 24/7", url=SUPPORT, style="primary")],
            ])
        )

    elif query.data == "claim_bonus":
        await context.bot.send_photo(
            chat_id=chat_id,
            photo=BONUS_PHOTO,
            caption=(
                f"<b>{E_GIFT} 50% Deposit Bonus Code FREE!! {E_PARTY}\n\n"
                f"{E_FIRE} Code: <code>NOAH50</code> {E_FIRE}\n\n"
                f"Enter promo code <b>NOAH50</b> when depositing.\n\n"
                f"{E_WARN} Only for accounts created using our link.\n\n"
                f"{E_CHECK} After depositing, send your Trader ID or click 'I Have Deposited' {E_HAND}</b>"
            ),
            parse_mode=ParseMode.HTML, reply_markup=bonus_keyboard()
        )

    elif query.data == "deposited":
        uid = state.get("trader_id")
        if not uid:
            await query.message.reply_text(
                f"<b>{E_WARN} Please send your Trader ID first! {E_HAND}</b>",
                parse_mode=ParseMode.HTML, reply_markup=support_keyboard()
            )
            return
        trader = db_get_trader(uid)
        dep = trader["deposit"] if trader else 0.0
        state["deposit"] = dep
        if dep >= MIN_DEPOSIT:
            state["step"] = "done"
            cancel_reminder(state)
            await query.message.reply_text(
                f"<b>{E_PARTY} Deposit Confirmed! WELCOME TO VIP! {E_CROWN}\n\n"
                f"━━━━━━━━━━━━━━━━━━━\n\n"
                f"{E_TROPHY} You are now a verified VIP member!\n\n"
                f"{E_FIRE} Join Exclusive VIP Signals Group NOW:\n\n"
                f"{E_DIAMOND} {VIP_LINK} {E_DIAMOND}\n\n"
                f"{E_THUMBS} Welcome to the winning team! {E_TROPHY}</b>",
                parse_mode=ParseMode.HTML, reply_markup=vip_keyboard()
            )
        else:
            await query.message.reply_text(
                f"<b>{E_WARN} Bro, your balance shows <b>${dep:.2f}</b>! {E_CROSS}\n\n"
                f"ID: <code>{uid}</code>\n\n"
                f"{E_MONEY} Please deposit <b>$20 or more</b> and click Re-Check! {E_HAND}</b>",
                parse_mode=ParseMode.HTML, reply_markup=recheck_keyboard()
            )

async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Capture photo and video file IDs sent directly to bot"""
    if update.message.photo:
        fid = update.message.photo[-1].file_id
        await update.message.reply_text("PHOTO FILE ID:\n" + fid)
    elif update.message.video:
        fid = update.message.video.file_id
        await update.message.reply_text("VIDEO FILE ID:\n" + fid)
    elif update.message.document:
        fid = update.message.document.file_id
        await update.message.reply_text("DOCUMENT FILE ID:\n" + fid)

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    state = get_state(chat_id)
    text = update.message.text.strip()

    if state["step"] == "awaiting_id":
        if not text.isdigit():
            # Not a trader ID — let AI reply instead
            await context.bot.send_chat_action(chat_id=chat_id, action="typing")
            reply = await ask_gemini(chat_id, text)
            await update.message.reply_text(reply)
            return
        state["step"] = "checking"
        asyncio.create_task(verify_id_then_respond(text, chat_id, context.bot))

    elif state["step"] == "awaiting_deposit":
        if text.isdigit():
            state["step"] = "checking"
            asyncio.create_task(verify_id_then_respond(text, chat_id, context.bot))
        else:
            # Normal chat — AI replies
            await context.bot.send_chat_action(chat_id=chat_id, action="typing")
            reply = await ask_gemini(chat_id, text)
            await update.message.reply_text(reply)

    else:
        # Any other step (start, done, checking) — AI replies to normal messages
        await context.bot.send_chat_action(chat_id=chat_id, action="typing")
        reply = await ask_gemini(chat_id, text)
        await update.message.reply_text(reply)


async def handle_postback(request):
    """Receives postbacks directly from Quotex"""
    from aiohttp import web
    params = request.rel_url.query
    
    def get_real(key):
        val = params.get(key, "").strip()
        if val.startswith("{") and val.endswith("}"):
            return ""
        return val
    
    uid     = get_real("uid")
    status  = get_real("status") 
    sumdep  = float(get_real("sumdep") or 0)
    country = get_real("country") or "N/A"
    
    print(f"POSTBACK: uid={uid} status={status} dep={sumdep}")
    
    if uid:
        db_save_trader(uid, sumdep, status, country)
        # Auto send VIP if deposited
        if sumdep >= MIN_DEPOSIT:
            for chat_id, state in user_state.items():
                if state.get("trader_id") == uid and state["step"] != "done":
                    state["deposit"] = sumdep
                    state["step"] = "done"
                    try:
                        await tg_app.bot.send_message(
                            chat_id=chat_id,
                            text=(
                                f"<b>{E_PARTY} Deposit Confirmed! WELCOME TO VIP! {E_CROWN}\n\n"
                                f"{E_FIRE} Join VIP:\n{VIP_LINK}\n\n"
                                f"{E_THUMBS} Welcome! {E_TROPHY}</b>"
                            ),
                            parse_mode=ParseMode.HTML,
                            reply_markup=vip_keyboard()
                        )
                    except Exception as e:
                        print(f"VIP send error: {e}")
                    break
    
    return web.Response(text="OK")

async def handle_addid(request):
    from aiohttp import web
    uid = request.rel_url.query.get("uid", "").strip()
    key = request.rel_url.query.get("key", "")
    if key != "quotexadmin2024":
        return web.Response(text="Forbidden", status=403)
    if uid:
        db_save_trader(uid, 0.0, "manual", "")
        return web.Response(text=f"Added: {uid}")
    return web.Response(text="No uid")

async def run_web_server():
    from aiohttp import web
    app = web.Application()
    app.router.add_get("/postback", handle_postback)
    app.router.add_get("/addid", handle_addid)
    app.router.add_get("/", lambda r: web.Response(text="Trading Noah Bot Running"))
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"✅ Web server running on port {port}")

async def handle_telegram(request):
    from aiohttp import web
    data = await request.json()
    update = Update.de_json(data, tg_app.bot)
    await tg_app.process_update(update)
    return web.Response(text="OK")


async def restore_reminders(bot):
    """On startup, restore all pending reminders from DB"""
    rows = db_get_all_reminders()
    if not rows:
        print("No pending reminders to restore")
        return
    print(f"Restoring {len(rows)} reminder(s) from DB...")
    for row in rows:
        chat_id_str, reminder_num, started_at = row[0], row[1], row[2]
        try:
            chat_id = int(chat_id_str)
            state = get_state(chat_id)
            if state.get("step") != "done":
                # Resume reminder immediately without sleeping first
                state["reminder_task"] = asyncio.create_task(
                    send_reminder(chat_id, bot, start_reminder_num=reminder_num, sleep_first=False)
                )
                print(f"✅ Restored reminder for chat {chat_id} at step {reminder_num}")
        except Exception as e:
            print(f"Restore error for {chat_id_str}: {e}")

async def main():
    import telegram
    print(f"python-telegram-bot version: {telegram.__version__}")
    db_create_tables()
    global tg_app
    tg_app = ApplicationBuilder().token(TOKEN).build()
    tg_app.add_handler(CommandHandler("start", start))
    for i in range(1, 6):
        tg_app.add_handler(CommandHandler(f"preview{i}", preview_reminder))
    tg_app.add_handler(CallbackQueryHandler(button_handler))
    tg_app.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO | filters.Document.ALL, photo_handler))
    tg_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    await tg_app.initialize()
    await tg_app.start()

    # Set webhook
    webhook_url = f"https://worker-production-b340.up.railway.app/telegram/{TOKEN}"
    await tg_app.bot.set_webhook(webhook_url, drop_pending_updates=True)
    print(f"✅ Webhook set: {webhook_url}")
    # Restore pending reminders from DB after restart
    await restore_reminders(tg_app.bot)

    # Start web server
    from aiohttp import web
    app = web.Application()
    app.router.add_post(f"/telegram/{TOKEN}", handle_telegram)
    app.router.add_get("/postback", handle_postback)
    app.router.add_get("/addid", handle_addid)
    app.router.add_get("/", lambda r: web.Response(text="Trading Noah Bot Running ✅"))

    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"✅ Web server running on port {port}")
    print("✅ Trading Noah Bot Running...")

    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
