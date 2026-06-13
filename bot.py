import os
import asyncio
import ssl
import signal
import logging
import traceback
import time
from datetime import datetime, timezone

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
    InputMediaVideo,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from telegram.constants import ParseMode
from telegram.error import NetworkError, TimedOut, RetryAfter, TelegramError
import pg8000.native
from aiohttp import web
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.memory import MemoryJobStore

# ─── LOGGING ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
log = logging.getLogger("noah_bot")
logging.getLogger("apscheduler").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)

# ─── CONFIG ───────────────────────────────────────────────────────────────────
TOKEN        = os.getenv("BOT_TOKEN", "8972809832:AAHKRaXFTjyVvCSgQP7Rfcrk97vRXL2nO90")
VIP_LINK     = "https://t.me/+H3isrme8c3BiNDg1"
AFFILIATE    = "https://broker-qx.pro/sign-up/?lid=1504736"
SUPPORT      = "https://t.me/TRADELIKENOAH"
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:DEfYBWltENxssYQNpworlKPeKVSKUuyQ@acela.proxy.rlwy.net:19828/railway")
MIN_DEPOSIT  = 20
OWNER_ID     = int(os.getenv("OWNER_ID", "8837911637"))
PORT         = int(os.getenv("PORT", 8080))

# ─── MEDIA IDs ────────────────────────────────────────────────────────────────
VIDEO_TUTORIAL = "BAACAgUAAxkBAAFMR_JqLHQgDfdvetmVFCu4tVoEmXayHwACkSEAAm6QYFUZ3EZET5TOdjwE"
VIDEO_REMINDER = "BAACAgUAAxkBAAFMQIxqLCy8iLgzzjwMiMFm4ahJi-N-iwACQCQAAmS9YFWS4sMNJoZYFjwE"
VIDEO_DEPOSIT  = "BQACAgUAAxkBAAFMQI5qLCzLxgL0oM6v_DRoWsq0R6ecMAACQiQAAmS9YFXmR4aJiqZyKjwE"
BONUS_PHOTO    = "AgACAgUAAxkBAAIIE2osaUQb9q2xShFHMQQXqQOhpy6IAAKaE2sbeuFgVY1Aj7qvPgy_AQADAgADeQADPAQ"

# ─── CUSTOM EMOJI HELPER ──────────────────────────────────────────────────────
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

# ─── GLOBALS ──────────────────────────────────────────────────────────────────
tg_app    = None
scheduler = None
_shutdown_event = None

# ─── DATABASE ─────────────────────────────────────────────────────────────────
def _parse_db_url(url: str):
    url = url.replace("postgresql://", "").replace("postgres://", "")
    userpass, rest = url.split("@", 1)
    user, password = userpass.split(":", 1)
    hostport, database = rest.split("/", 1)
    parts = hostport.split(":")
    host = parts[0]
    port = int(parts[1]) if len(parts) > 1 else 5432
    return host, port, user, password, database


def _make_ssl():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def get_db():
    host, port, user, password, database = _parse_db_url(DATABASE_URL)
    return pg8000.native.Connection(
        host=host, port=port, user=user,
        password=password, database=database,
        ssl_context=_make_ssl()
    )


def get_db_with_retry(max_retries: int = 5):
    """Synchronous DB connection with exponential backoff."""
    delay = 1
    last_exc = None
    for attempt in range(1, max_retries + 1):
        try:
            conn = get_db()
            if attempt > 1:
                log.info("DB connected after %d attempt(s)", attempt)
            return conn
        except Exception as exc:
            last_exc = exc
            log.warning("DB connect attempt %d/%d failed: %s", attempt, max_retries, exc)
            if attempt < max_retries:
                time.sleep(min(delay, 30))
                delay *= 2
    log.error("DB connection failed after %d attempts: %s", max_retries, last_exc)
    raise last_exc


def _ensure_schema():
    """Create required tables if they don't exist."""
    try:
        conn = get_db_with_retry()
        conn.run("""
            CREATE TABLE IF NOT EXISTS user_state (
                chat_id    BIGINT PRIMARY KEY,
                step       VARCHAR(50)  DEFAULT 'start',
                trader_id  BIGINT,
                deposit    FLOAT        DEFAULT 0.0,
                country    VARCHAR(100),
                updated_at TIMESTAMP    DEFAULT NOW()
            )
        """)
        conn.run("""
            CREATE TABLE IF NOT EXISTS scheduled_reminders (
                id           SERIAL PRIMARY KEY,
                chat_id      BIGINT,
                reminder_num INT,
                next_send_at TIMESTAMP,
                created_at   TIMESTAMP DEFAULT NOW(),
                UNIQUE(chat_id, reminder_num)
            )
        """)
        conn.run("""
            CREATE TABLE IF NOT EXISTS sent_reminders (
                chat_id      BIGINT,
                reminder_num INT,
                sent_at      TIMESTAMP DEFAULT NOW(),
                PRIMARY KEY (chat_id, reminder_num)
            )
        """)
        conn.close()
        log.info("DB schema verified/created")
    except Exception as exc:
        log.error("Schema init error: %s", exc)


# ─── DB STATE HELPERS ─────────────────────────────────────────────────────────
def db_load_user_state(chat_id: int) -> dict:
    try:
        conn = get_db_with_retry()
        rows = conn.run(
            "SELECT step, trader_id, deposit FROM user_state WHERE chat_id = :cid",
            cid=chat_id
        )
        conn.close()
        if rows:
            return {"step": rows[0][0] or "start", "trader_id": rows[0][1], "deposit": float(rows[0][2] or 0)}
    except Exception as exc:
        log.error("load_user_state(%s) error: %s", chat_id, exc)
    return {"step": "start", "trader_id": None, "deposit": 0.0}


def db_save_user_state(chat_id: int, step: str, trader_id=None, deposit: float = 0.0):
    try:
        conn = get_db_with_retry()
        conn.run("""
            INSERT INTO user_state (chat_id, step, trader_id, deposit, updated_at)
            VALUES (:cid, :step, :tid, :dep, NOW())
            ON CONFLICT (chat_id) DO UPDATE SET
                step       = EXCLUDED.step,
                trader_id  = EXCLUDED.trader_id,
                deposit    = EXCLUDED.deposit,
                updated_at = NOW()
        """, cid=chat_id, step=step, tid=trader_id, dep=float(deposit))
        conn.close()
        log.debug("Saved state chat_id=%s step=%s", chat_id, step)
    except Exception as exc:
        log.error("save_user_state(%s) error: %s", chat_id, exc)


def db_get_trader(uid) -> dict | None:
    try:
        conn = get_db_with_retry()
        rows = conn.run(
            "SELECT uid, deposit FROM verified_traders WHERE uid = :uid",
            uid=uid
        )
        conn.close()
        if rows:
            return {"uid": rows[0][0], "deposit": float(rows[0][1] or 0)}
    except Exception as exc:
        log.error("db_get_trader(%s) error: %s", uid, exc)
    return None


def db_save_trader(uid, deposit: float = 0.0, status: str = "", country: str = ""):
    try:
        conn = get_db_with_retry()
        conn.run("""
            INSERT INTO verified_traders (uid, deposit, status, country, updated_at)
            VALUES (:uid, :dep, :status, :country, NOW())
            ON CONFLICT (uid) DO UPDATE SET
                deposit    = GREATEST(verified_traders.deposit, EXCLUDED.deposit),
                status     = EXCLUDED.status,
                updated_at = NOW()
        """, uid=uid, dep=float(deposit), status=status, country=country)
        conn.close()
        log.info("Saved trader uid=%s dep=$%.2f status=%s", uid, deposit, status)
    except Exception as exc:
        log.error("db_save_trader(%s) error: %s", uid, exc)


def db_reminder_already_sent(chat_id: int, reminder_num: int) -> bool:
    """Idempotency check — was this reminder already sent?"""
    try:
        conn = get_db_with_retry()
        rows = conn.run(
            "SELECT 1 FROM sent_reminders WHERE chat_id = :cid AND reminder_num = :rn",
            cid=chat_id, rn=reminder_num
        )
        conn.close()
        return bool(rows)
    except Exception as exc:
        log.error("reminder_already_sent check error: %s", exc)
        return False


def db_mark_reminder_sent(chat_id: int, reminder_num: int):
    try:
        conn = get_db_with_retry()
        conn.run("""
            INSERT INTO sent_reminders (chat_id, reminder_num)
            VALUES (:cid, :rn)
            ON CONFLICT DO NOTHING
        """, cid=chat_id, rn=reminder_num)
        conn.close()
    except Exception as exc:
        log.error("mark_reminder_sent error: %s", exc)


# ─── IN-MEMORY STATE CACHE (backed by DB) ─────────────────────────────────────
_state_cache: dict = {}


def get_state(chat_id: int) -> dict:
    if chat_id not in _state_cache:
        _state_cache[chat_id] = db_load_user_state(chat_id)
    return _state_cache[chat_id]


def set_state(chat_id: int, **kwargs):
    state = get_state(chat_id)
    state.update(kwargs)
    db_save_user_state(
        chat_id,
        step=state.get("step", "start"),
        trader_id=state.get("trader_id"),
        deposit=state.get("deposit", 0.0),
    )


# ─── SAFE MESSAGE SENDER ──────────────────────────────────────────────────────
async def safe_send(coro, retries: int = 3):
    """Execute a Telegram API coroutine with retry on transient errors."""
    delay = 1
    for attempt in range(1, retries + 1):
        try:
            return await coro
        except RetryAfter as exc:
            wait = exc.retry_after + 1
            log.warning("Rate-limited by Telegram, waiting %ds", wait)
            await asyncio.sleep(wait)
        except (TimedOut, NetworkError) as exc:
            log.warning("Telegram transient error (attempt %d/%d): %s", attempt, retries, exc)
            if attempt < retries:
                await asyncio.sleep(min(delay, 30))
                delay *= 2
        except TelegramError as exc:
            log.error("Telegram API error: %s", exc)
            return None
        except Exception as exc:
            log.error("Unexpected send error: %s\n%s", exc, traceback.format_exc())
            return None
    return None


# ─── KEYBOARDS ────────────────────────────────────────────────────────────────
def support_btn():
    return InlineKeyboardButton("✉️ Contact Support 24/7", url=SUPPORT)

def register_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔗 REGISTER FREE NOW ⭐", url=AFFILIATE)],
        [InlineKeyboardButton("🔑 I HAVE REGISTERED ✨", callback_data="registered")],
        [InlineKeyboardButton("✉️ CONTACT SUPPORT 24/7", url=SUPPORT)],
    ])

def deposit_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎁 Claim 50% Bonus NOW", callback_data="claim_bonus")],
        [InlineKeyboardButton("📹 How To Deposit (Tutorial)", callback_data="tutorial")],
        [InlineKeyboardButton("🔄 I Have Deposited (Re-Check)", callback_data="deposited")],
        [InlineKeyboardButton("✉️ Contact Support 24/7", url=SUPPORT)],
    ])

def reject_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔗 Register With Our Link", url=AFFILIATE)],
        [InlineKeyboardButton("🔄 Try Again With Correct ID", callback_data="try_again")],
        [InlineKeyboardButton("✉️ Contact Support 24/7", url=SUPPORT)],
    ])

def reminder_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 Create Free Account Now", url=AFFILIATE)],
        [InlineKeyboardButton("🔥 Click Here To Join VIP", url=AFFILIATE)],
        [InlineKeyboardButton("✉️ Contact Support 24/7", url=SUPPORT)],
    ])

def bonus_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💰 Deposit Now & Get 50% Bonus", url=AFFILIATE)],
        [InlineKeyboardButton("📹 How To Deposit (Tutorial)", callback_data="tutorial")],
        [InlineKeyboardButton("✅ I Have Deposited", callback_data="deposited")],
        [InlineKeyboardButton("✉️ Contact Support 24/7", url=SUPPORT)],
    ])

def vip_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👑 JOIN VIP SIGNALS GROUP 🏆", url=VIP_LINK)],
        [InlineKeyboardButton("✉️ Contact Support 24/7", url=SUPPORT)],
    ])

def support_keyboard():
    return InlineKeyboardMarkup([[support_btn()]])

def recheck_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💰 Deposit Now", url=AFFILIATE)],
        [InlineKeyboardButton("🔄 I Have Deposited (Re-Check)", callback_data="deposited")],
        [InlineKeyboardButton("✉️ Contact Support 24/7", url=SUPPORT)],
    ])


# ─── REMINDER CAPTIONS ────────────────────────────────────────────────────────
REM1_CAP = (
    '<b><tg-emoji emoji-id="5397782960512444700">📌</tg-emoji> ZERO TO HERO JOURNEY VIDEO '
    '<tg-emoji emoji-id="5397782960512444700">📌</tg-emoji>\n'
    '<tg-emoji emoji-id="5274099962655816924">❗️</tg-emoji>'
    '<tg-emoji emoji-id="5274099962655816924">❗️</tg-emoji>'
    '<tg-emoji emoji-id="5274099962655816924">❗️</tg-emoji>'
    '<tg-emoji emoji-id="5274099962655816924">❗️</tg-emoji>'
    '<tg-emoji emoji-id="5274099962655816924">❗️</tg-emoji>'
    '<tg-emoji emoji-id="5274099962655816924">❗️</tg-emoji>'
    '<tg-emoji emoji-id="5274099962655816924">❗️</tg-emoji>'
    '<tg-emoji emoji-id="5274099962655816924">❗️</tg-emoji>\n\n'
    'https://youtu.be/q1a8FZ8T4XU?si=bMvgGhQ1Ru6nLayx\n\n'
    '👆👆 WATCH MY TRADING JOURNEY VIDEO\n'
    '( MUST WATCH ) <tg-emoji emoji-id="5424972470023104089">🔥</tg-emoji> 📣</b>'
)
REM2_CAP = (
    '<b><tg-emoji emoji-id="5395695537687123235">🚨</tg-emoji> DON\u2019T SKIP | VIDEO OPEN KAR '
    '<tg-emoji emoji-id="5395695537687123235">🚨</tg-emoji>\n'
    '<tg-emoji emoji-id="5210956306952758910">👀</tg-emoji> Proof dekh le pehle, phir decision lena\n\n'
    '<tg-emoji emoji-id="5231200819986047254">📊</tg-emoji> TODAY\'S LIVE TRADING RESULTS\n\n'
    '<tg-emoji emoji-id="5402477260982731644">☀️</tg-emoji> Morning Session\n'
    '<tg-emoji emoji-id="6185707729009512236">👉</tg-emoji> 2 Signals → 2/2 WIN\n'
    '<tg-emoji emoji-id="5210952531676504517">❌</tg-emoji> No Martingale | '
    '<tg-emoji emoji-id="5424972470023104089">🔥</tg-emoji> Deep Win\n\n'
    '<tg-emoji emoji-id="5402477260982731644">☀️</tg-emoji> Afternoon Session\n'
    '<tg-emoji emoji-id="6185707729009512236">👉</tg-emoji> 2 Signals → 2/2 WIN\n'
    '<tg-emoji emoji-id="5210952531676504517">❌</tg-emoji> No Martingale | '
    '<tg-emoji emoji-id="5427168083074628963">💎</tg-emoji> Deep Win\n\n'
    '<tg-emoji emoji-id="5449569374065152798">🌛</tg-emoji> Evening Session\n'
    '<tg-emoji emoji-id="6185707729009512236">👉</tg-emoji> 3 Signals\n'
    '<tg-emoji emoji-id="5389006967937184376">🤔</tg-emoji> 3 Direct Win\n'
    '<tg-emoji emoji-id="5210952531676504517">❌</tg-emoji> No Martingale | '
    '<tg-emoji emoji-id="5427168083074628963">💎</tg-emoji> Deep Win\n\n'
    '<tg-emoji emoji-id="5210956306952758910">👀</tg-emoji> YESTERDAY RESULT\n'
    '- 17 WIN / 0 LOSS <tg-emoji emoji-id="5424972470023104089">🔥</tg-emoji>'
    '<tg-emoji emoji-id="5409048419211682843">💵</tg-emoji>'
    '<tg-emoji emoji-id="5244837092042750681">📈</tg-emoji>\n\n'
    '<tg-emoji emoji-id="5443038326535759644">💬</tg-emoji> VIP join karna hai?\n'
    '<tg-emoji emoji-id="5253742260054409879">✉️</tg-emoji> Message "VIP" '
    '<tg-emoji emoji-id="5416117059207572332">➡️</tg-emoji> @TRADELIKENOAH</b>'
)
REM3_CAP = (
    '<b>TRADER OF THE WEEK '
    '<tg-emoji emoji-id="5316961893728926221">🦁</tg-emoji>'
    '<tg-emoji emoji-id="5413566144986503832">🏆</tg-emoji>\n'
    '<tg-emoji emoji-id="5274099962655816924">❗️</tg-emoji>'
    '<tg-emoji emoji-id="5274099962655816924">❗️</tg-emoji>'
    '<tg-emoji emoji-id="5274099962655816924">❗️</tg-emoji>'
    '<tg-emoji emoji-id="5274099962655816924">❗️</tg-emoji>'
    '<tg-emoji emoji-id="5274099962655816924">❗️</tg-emoji>'
    '<tg-emoji emoji-id="5274099962655816924">❗️</tg-emoji>'
    '<tg-emoji emoji-id="5274099962655816924">❗️</tg-emoji>'
    '<tg-emoji emoji-id="5274099962655816924">❗️</tg-emoji>\n\n'
    'https://youtu.be/q1a8FZ8T4XU?si=bMvgGhQ1Ru6nLayx\n\n'
    '👆👆 WATCH HOW I MADE $40,000\n'
    '( ₹35,00,000 ) IN A WEEK '
    '<tg-emoji emoji-id="5424972470023104089">🔥</tg-emoji>'
    '<tg-emoji emoji-id="5395695537687123235">🚨</tg-emoji></b>'
)
REM4_CAP = (
    '<b>₹1,000 se ₹5,00,000 — sirf mere VIP signals follow karke '
    '<tg-emoji emoji-id="5409048419211682843">💵</tg-emoji>'
    '<tg-emoji emoji-id="5244837092042750681">📈</tg-emoji>\n\n'
    'Ye koi kahani nahi, real results hain. '
    '<tg-emoji emoji-id="5224607267797606837">☄️</tg-emoji>\n\n'
    'My VIP member booked Z900 bike '
    '<tg-emoji emoji-id="5260295181852225992">😱</tg-emoji>'
    '<tg-emoji emoji-id="5256228126995787725">🏍</tg-emoji>\n\n'
    '<tg-emoji emoji-id="5264919878082509254">▶️</tg-emoji> LIVE VIDEO PROOF CHECK NOW 👆👆\n\n'
    'Aaj bhi agar tum VIP channel join nahi kar rahe,\n'
    'toh honestly tum apna hi nuksaan kar rahe ho.\n\n'
    '⌛ Time waste mat karo.\n'
    '<tg-emoji emoji-id="5188481279963715781">🚀</tg-emoji> Next success story tumhari ho sakti hai\n\n'
    '<tg-emoji emoji-id="5253742260054409879">✉️</tg-emoji> JOIN NOW — Message me "VIP"\n'
    '<tg-emoji emoji-id="5201990176175299013">📱</tg-emoji> MESSAGE HERE '
    '<tg-emoji emoji-id="5416117059207572332">➡️</tg-emoji> @TRADELIKENOAH</b>'
)
REM5_CAP = (
    '<b>Bhai, aaj is photo mein tu mere maa-baap ko dekh raha hoga '
    '<tg-emoji emoji-id="5337080053119336309">👍</tg-emoji>\n'
    'Unke face ki khushi notice kar… aaj woh kitna proud feel karte hain '
    '<tg-emoji emoji-id="5391320026869408028">🫂</tg-emoji>\n'
    'Unhone mere saath kitni gaadiyaan dekhi '
    '<tg-emoji emoji-id="5253752975997803460">🚘</tg-emoji>\n'
    'Kitni jagah world mein ghoome '
    '<tg-emoji emoji-id="5224450179368767019">🌍</tg-emoji>\n'
    'Aaj woh khud bolte hain — "tere jaisa beta sabko mile."\n\n'
    'Lekin sach kya hai?\n'
    'Yeh sab ek din mein nahi hua.\n'
    'Iske peeche sirf ek cheez thi — PAISA '
    '<tg-emoji emoji-id="5409048419211682843">💵</tg-emoji>\n\n'
    'Agar tu bhi chahta hai ki ek din tere maa-baap bhi proud feel karein,\n'
    'Log bolein — "Bhai, kya beta paida kiya hai!"\n\n'
    'Aur agar tujhe genuinely paisa kamana hai,\n'
    'High quality trading signals chahiye,\n'
    'Toh abhi meri ID par message kar — " VIP " '
    '<tg-emoji emoji-id="5416117059207572332">➡️</tg-emoji> @TRADELIKENOAH</b>'
)

REM_BTN_PLAY = "▶️ Watch Video Click Here"
REM_BTN_KEY  = "🔑 Register Your Account"
REM_BTN_MAIL = "✉️ Contact Support 24/7"


# ─── REMINDER SENDER ──────────────────────────────────────────────────────────
async def send_one_reminder(chat_id: int, bot, reminder_num: int):
    """Send a single reminder (1-5). Idempotent — skips if already sent."""
    if db_reminder_already_sent(chat_id, reminder_num):
        log.info("Reminder %d already sent to %s — skipping", reminder_num, chat_id)
        return

    yt = "https://youtu.be/q1a8FZ8T4XU?si=bMvgGhQ1Ru6nLayx"
    btn_13 = InlineKeyboardMarkup([
        [InlineKeyboardButton(REM_BTN_PLAY, url=yt)],
        [InlineKeyboardButton(REM_BTN_KEY, callback_data="registered")],
        [InlineKeyboardButton(REM_BTN_MAIL, url=SUPPORT)],
    ])
    btn_245 = InlineKeyboardMarkup([
        [InlineKeyboardButton(REM_BTN_KEY, callback_data="registered")],
        [InlineKeyboardButton(REM_BTN_MAIL, url=SUPPORT)],
    ])

    try:
        if reminder_num == 1:
            await safe_send(bot.send_photo(
                chat_id=chat_id,
                photo="AgACAgUAAxkBAAIIhmosfzneQ76I3CuhlSHtj80p5vazAALCEGsbrGtoVSAOT8CWevovAQADAgADeQADPAQ",
                caption=REM1_CAP, parse_mode="HTML"
            ))
            await safe_send(bot.send_video_note(
                chat_id=chat_id,
                video_note="DQACAgUAAxkBAAFMSQhqLIb67doN1uewmuPt5oUt44kzOQACdR4AAqxraFW9yKKdMgc2AjwE",
                reply_markup=btn_13
            ))
        elif reminder_num == 2:
            await safe_send(bot.send_video(
                chat_id=chat_id,
                video="BAACAgUAAxkBAAFMSPJqLIWlmSn5W5Vl0YtME2reEchEvgACoB0AAmnTSFQUiVIEIzqvlDwE",
                caption=REM2_CAP, parse_mode="HTML", reply_markup=btn_245
            ))
        elif reminder_num == 3:
            await safe_send(bot.send_photo(
                chat_id=chat_id,
                photo="AgACAgUAAxkBAAIIh2osfzsGVAMzCEnZf_8G2pjVFN3oAALDEGsbrGtoVYaoZ4WKYIjGAQADAgADeQADPAQ",
                caption=REM3_CAP, parse_mode="HTML"
            ))
            await safe_send(bot.send_video_note(
                chat_id=chat_id,
                video_note="DQACAgUAAxkBAAFMSQpqLIcHtKjTGEyoV6FLw6eHtiakFAACdh4AAqxraFXB9SIHnO1XujwE",
                reply_markup=btn_13
            ))
        elif reminder_num == 4:
            await safe_send(bot.send_video(
                chat_id=chat_id,
                video="BAACAgUAAxkBAAFMSPZqLIWx4pTuzb98rHinaimoXeAyUQACnCEAAtCiOFSei_vCioOGDzwE",
                caption=REM4_CAP, parse_mode="HTML", reply_markup=btn_245
            ))
        elif reminder_num == 5:
            await safe_send(bot.send_photo(
                chat_id=chat_id,
                photo="AgACAgUAAxkBAAIIoWoshS8UEUP49vFEPnYbcVsdp1G7AALEEGsbrGtoVeld-Rt8y727AQADAgADeQADPAQ",
                caption=REM5_CAP, parse_mode="HTML", reply_markup=btn_245
            ))

        db_mark_reminder_sent(chat_id, reminder_num)
        log.info("Sent reminder %d to chat_id=%s", reminder_num, chat_id)
    except Exception as exc:
        log.error(
            "send_one_reminder(%s, %d) error: %s\n%s",
            chat_id, reminder_num, exc, traceback.format_exc()
        )


def schedule_reminder(chat_id: int, reminder_num: int, delay_seconds: int):
    """Schedule a reminder via APScheduler."""
    if scheduler is None:
        return
    job_id = f"rem_{chat_id}_{reminder_num}"
    run_at = datetime.fromtimestamp(time.time() + delay_seconds, tz=timezone.utc)
    try:
        scheduler.add_job(
            _fire_reminder,
            "date",
            run_date=run_at,
            args=[chat_id, reminder_num],
            id=job_id,
            replace_existing=True,
            misfire_grace_time=3600,
        )
        log.info(
            "Scheduled reminder %d for chat_id=%s at %s",
            reminder_num, chat_id, run_at.isoformat()
        )
    except Exception as exc:
        log.error("schedule_reminder error: %s", exc)


async def _fire_reminder(chat_id: int, reminder_num: int):
    """APScheduler job: send reminder if user hasn't completed VIP yet."""
    try:
        state = get_state(chat_id)
        if state.get("step") == "done":
            log.info(
                "Skipping reminder %d for chat_id=%s — user is done",
                reminder_num, chat_id
            )
            return
        await send_one_reminder(chat_id, tg_app.bot, reminder_num)
        # Schedule the next reminder in the cycle (1→2→3→4→5→1→...)
        next_num = (reminder_num % 5) + 1
        schedule_reminder(chat_id, next_num, 10800)  # 3 hours
    except Exception as exc:
        log.error("_fire_reminder(%s, %d) error: %s", chat_id, reminder_num, exc)


def cancel_reminders(chat_id: int):
    """Remove all pending reminder jobs for a chat_id."""
    if scheduler is None:
        return
    for i in range(1, 6):
        job_id = f"rem_{chat_id}_{i}"
        try:
            scheduler.remove_job(job_id)
        except Exception:
            pass


# ─── START SEQUENCE ───────────────────────────────────────────────────────────
async def run_start_sequence(chat_id: int, bot):
    try:
        # ── SEQUENCE 1: Immediate ─────────────────────────────────────────
        await safe_send(bot.send_sticker(
            chat_id=chat_id,
            sticker="CAACAgUAAxkBAAFL9cVqKCa70-hZ2BsucTxBmLtRI2PFMAACBxIAArIYAAFXuG3a4VpEuLw7BA"
        ))
        await safe_send(bot.send_video_note(
            chat_id=chat_id,
            video_note="DQACAgUAAxkBAAMbaidRKZuu4TnoWbcqd3A_KLQByFEAAs4cAAJfGjFXsw34l8lliF47BA"
        ))
        await safe_send(bot.send_photo(
            chat_id=chat_id,
            photo="AgACAgUAAxkBAAMZaidQ8AAB-XcWZ92dfh1Nyj12vp9tAAL9D2sb2mc5VTJ5ySC9Sop4AQADAgADeQADOwQ",
            caption=(
                f"<b>{E_TROPHY} You're Here Because You Want To Earn Money {E_MONEY}\n\n"
                f"{E_HAND} Join My All Channels {E_CHART} Below & Recover Your Lifetime Losses\n\n"
                f"{E_FIRE} Start Earning Money Today {E_ROCKET}</b>"
            ),
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📈 FREE VIP GROUP", url="https://t.me/+s_guD0HJ0B9kYWM1")],
                [InlineKeyboardButton("🎯 JOIN LOSS RECOVERY", url="https://t.me/+s_guD0HJ0B9kYWM1")],
                [InlineKeyboardButton("💬 CONTACT SUPPORT 24/7", url=SUPPORT)],
            ])
        ))

        # ── WAIT 3 MINUTES ────────────────────────────────────────────────
        await asyncio.sleep(180)

        # ── SEQUENCE 2: +3 min ────────────────────────────────────────────
        await safe_send(bot.send_message(
            chat_id=chat_id,
            text=(
                f"<b>Hello {E_TROPHY} Are You Ready To Earn Money With Trading Without Experience\n\n"
                f"{E_CHART} I Helped 10,000+ New Members To Start EARNING {E_ROCKET}\n\n"
                f"{E_WARN} I Shared The Result Of My Client Earning With Me {E_HAND}</b>"
            ),
            parse_mode=ParseMode.HTML
        ))

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
        await safe_send(bot.send_media_group(chat_id=chat_id, media=media))

        await safe_send(bot.send_message(
            chat_id=chat_id,
            text=(
                f"<b>{E_PERSON} Bro, What Is Your Name And What's Your Country? {E_GLOBE}\n\n"
                f"{E_NEW} It Will Help Us To Understand Each Other Better {E_TROPHY}</b>"
            ),
            parse_mode=ParseMode.HTML,
            reply_markup=support_keyboard()
        ))

        # ── WAIT 4.5 MINUTES ──────────────────────────────────────────────
        await asyncio.sleep(270)

        # ── SEQUENCE 3: +4.5 min ──────────────────────────────────────────
        await safe_send(bot.send_video(
            chat_id=chat_id,
            video="BAACAgUAAxkBAAOKaidpD_-7HAnZ9D2d-yGBmsLMW_QAAjcYAAI1GzlXipdJ8rzcwTs7BA",
            caption=(
                f"<b>{E_MONEY} Okay, So To Start Earning {E_MONEY} The First Step Is To Register "
                f"A Trading Account {E_LINK}\n\n"
                f"{E_HAND} Watch The Video & Just Click On Here {E_HAND}</b>"
            ),
            parse_mode=ParseMode.HTML,
            reply_markup=register_keyboard()
        ))

        # Schedule first reminder in 3 hours
        schedule_reminder(chat_id, 1, 10800)
        log.info("Start sequence complete for chat_id=%s", chat_id)

    except asyncio.CancelledError:
        log.info("Start sequence cancelled for chat_id=%s", chat_id)
    except Exception as exc:
        log.error(
            "run_start_sequence(%s) error: %s\n%s",
            chat_id, exc, traceback.format_exc()
        )


# ─── ID VERIFICATION ──────────────────────────────────────────────────────────
async def verify_id_then_respond(uid: str, chat_id: int, bot):
    try:
        msg = await safe_send(bot.send_message(
            chat_id=chat_id,
            text=f"<b>{E_EYES} Verifying ID <code>{uid}</code>... Please wait!</b>",
            parse_mode=ParseMode.HTML
        ))
        if not msg:
            return

        trader = db_get_trader(uid)
        if not trader:
            for _ in range(2):
                await asyncio.sleep(5)
                trader = db_get_trader(uid)
                if trader:
                    break

        if not trader:
            set_state(chat_id, step="awaiting_id")
            await safe_send(bot.edit_message_text(
                chat_id=chat_id, message_id=msg.message_id,
                text=(
                    f"<b>{E_CROSS} Bro, this account is NOT registered through my link! {E_WARN}\n\n"
                    f"Please re-check and send the correct Trader ID. {E_EYES}\n\n"
                    f"{E_CHAT} Contact us anytime — our team is available 24/7! {E_CLOCK}</b>"
                ),
                parse_mode=ParseMode.HTML, reply_markup=reject_keyboard()
            ))
            schedule_reminder(chat_id, 1, 10800)
            return

        dep = trader["deposit"]
        set_state(chat_id, step="checking", trader_id=uid, deposit=dep)

        if dep >= MIN_DEPOSIT:
            set_state(chat_id, step="done", trader_id=uid, deposit=dep)
            cancel_reminders(chat_id)
            await safe_send(bot.edit_message_text(
                chat_id=chat_id, message_id=msg.message_id,
                text=(
                    f"<b>{E_CHECK} ID <code>{uid}</code> verified! "
                    f"{E_PARTY} Deposit confirmed! {E_ROCKET}</b>"
                ),
                parse_mode=ParseMode.HTML
            ))
            await safe_send(bot.send_message(
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
            ))
            log.info(
                "User chat_id=%s verified VIP (uid=%s dep=$%.2f)",
                chat_id, uid, dep
            )
        else:
            set_state(chat_id, step="awaiting_deposit", trader_id=uid, deposit=dep)
            if dep > 0:
                await safe_send(bot.edit_message_text(
                    chat_id=chat_id, message_id=msg.message_id,
                    text=(
                        f"<b>{E_CHECK} ID <code>{uid}</code> verified! {E_WARN}\n\n"
                        f"Your current balance: <b>${dep:.2f}</b>\n\n"
                        f"{E_MONEY} You need to deposit minimum <b>${MIN_DEPOSIT}</b> to unlock VIP!\n\n"
                        f"Please deposit <b>${MIN_DEPOSIT - dep:.2f} more</b> and click Re-Check {E_HAND}</b>"
                    ),
                    parse_mode=ParseMode.HTML, reply_markup=recheck_keyboard()
                ))
            else:
                await safe_send(bot.edit_message_text(
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
                ))
                await safe_send(bot.send_document(
                    chat_id=chat_id, document=VIDEO_DEPOSIT,
                    caption="<b>👆 Watch this video to learn how to deposit!</b>",
                    parse_mode=ParseMode.HTML
                ))
    except Exception as exc:
        log.error(
            "verify_id_then_respond(%s, %s) error: %s\n%s",
            uid, chat_id, exc, traceback.format_exc()
        )


# ─── TELEGRAM HANDLERS ────────────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        chat_id = update.effective_chat.id
        cancel_reminders(chat_id)
        set_state(chat_id, step="start", trader_id=None, deposit=0.0)
        log.info("User chat_id=%s started bot", chat_id)
        asyncio.create_task(run_start_sequence(chat_id, context.bot))
    except Exception as exc:
        log.error("start handler error: %s", exc)


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()
        chat_id = query.message.chat_id
        state = get_state(chat_id)
        data = query.data

        if data in ("registered", "reg"):
            cancel_reminders(chat_id)
            set_state(chat_id, step="awaiting_id")
            await safe_send(context.bot.send_photo(
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
            ))

        elif data == "try_again":
            set_state(chat_id, step="awaiting_id")
            await safe_send(context.bot.send_photo(
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
            ))

        elif data == "tutorial":
            await safe_send(context.bot.send_video(
                chat_id=chat_id,
                video=VIDEO_TUTORIAL,
                caption=(
                    f"<b>{E_MONEY} How To Deposit Tutorial {E_CHART}\n\n"
                    f"👆 Watch this video to learn how to deposit on Quotex!\n\n"
                    f"{E_GIFT} Use code <code>NOAH50</code> for 50% bonus on deposit! {E_FIRE}</b>"
                ),
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("💰 Deposit Now", url=AFFILIATE)],
                    [InlineKeyboardButton("🔄 I Have Deposited (Re-Check)", callback_data="deposited")],
                    [InlineKeyboardButton("✉️ Contact Support 24/7", url=SUPPORT)],
                ])
            ))

        elif data == "claim_bonus":
            await safe_send(context.bot.send_photo(
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
            ))

        elif data == "deposited":
            uid = state.get("trader_id")
            if not uid:
                await safe_send(query.message.reply_text(
                    f"<b>{E_WARN} Please send your Trader ID first! {E_HAND}</b>",
                    parse_mode=ParseMode.HTML, reply_markup=support_keyboard()
                ))
                return
            trader = db_get_trader(uid)
            dep = trader["deposit"] if trader else 0.0
            set_state(chat_id, deposit=dep)
            if dep >= MIN_DEPOSIT:
                set_state(chat_id, step="done", deposit=dep)
                cancel_reminders(chat_id)
                await safe_send(query.message.reply_text(
                    f"<b>{E_PARTY} Deposit Confirmed! WELCOME TO VIP! {E_CROWN}\n\n"
                    f"━━━━━━━━━━━━━━━━━━━\n\n"
                    f"{E_TROPHY} You are now a verified VIP member!\n\n"
                    f"{E_FIRE} Join Exclusive VIP Signals Group NOW:\n\n"
                    f"{E_DIAMOND} {VIP_LINK} {E_DIAMOND}\n\n"
                    f"{E_THUMBS} Welcome to the winning team! {E_TROPHY}</b>",
                    parse_mode=ParseMode.HTML, reply_markup=vip_keyboard()
                ))
                log.info(
                    "User chat_id=%s confirmed deposit via button (uid=%s dep=$%.2f)",
                    chat_id, uid, dep
                )
            else:
                await safe_send(query.message.reply_text(
                    f"<b>{E_WARN} Bro, your balance shows <b>${dep:.2f}</b>! {E_CROSS}\n\n"
                    f"ID: <code>{uid}</code>\n\n"
                    f"{E_MONEY} Please deposit <b>$20 or more</b> and click Re-Check! {E_HAND}</b>",
                    parse_mode=ParseMode.HTML, reply_markup=recheck_keyboard()
                ))
    except Exception as exc:
        log.error("button_handler error: %s\n%s", exc, traceback.format_exc())


async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Return file IDs for media sent to the bot (owner only)."""
    try:
        if update.effective_user.id != OWNER_ID:
            return
        if update.message.photo:
            fid = update.message.photo[-1].file_id
            await update.message.reply_text("PHOTO FILE ID:\n" + fid)
        elif update.message.video:
            fid = update.message.video.file_id
            await update.message.reply_text("VIDEO FILE ID:\n" + fid)
        elif update.message.document:
            fid = update.message.document.file_id
            await update.message.reply_text("DOCUMENT FILE ID:\n" + fid)
    except Exception as exc:
        log.error("photo_handler error: %s", exc)


async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        chat_id = update.effective_chat.id
        state = get_state(chat_id)
        text = update.message.text.strip()

        if state["step"] == "awaiting_id":
            if not text.isdigit():
                await safe_send(update.message.reply_text(
                    f"<b>{E_WARN} Please send only numbers (e.g. <code>89057949</code>) {E_HAND}</b>",
                    parse_mode=ParseMode.HTML, reply_markup=support_keyboard()
                ))
                return
            set_state(chat_id, step="checking")
            asyncio.create_task(verify_id_then_respond(text, chat_id, context.bot))

        elif state["step"] == "awaiting_deposit":
            if text.isdigit():
                set_state(chat_id, step="checking")
                asyncio.create_task(verify_id_then_respond(text, chat_id, context.bot))
    except Exception as exc:
        log.error("message_handler error: %s", exc)


async def preview_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Preview any reminder instantly — /preview1 through /preview5 (owner only)."""
    try:
        if update.effective_user.id != OWNER_ID:
            return
        cmd = update.message.text.strip().lower()
        suffix = cmd.replace("/preview", "")
        if not suffix.isdigit() or not (1 <= int(suffix) <= 5):
            await update.message.reply_text("Use /preview1 to /preview5")
            return
        num = int(suffix)
        await update.message.reply_text(f"Sending reminder {num} preview...")
        await send_one_reminder(update.effective_chat.id, context.bot, num)
    except Exception as exc:
        log.error("preview_reminder error: %s", exc)


# ─── WEB HANDLERS ─────────────────────────────────────────────────────────────
async def handle_postback(request: web.Request) -> web.Response:
    try:
        params = request.rel_url.query

        def get_real(key):
            val = params.get(key, "").strip()
            return "" if (val.startswith("{") and val.endswith("}")) else val

        uid     = get_real("uid")
        status  = get_real("status")
        sumdep  = float(get_real("sumdep") or 0)
        country = get_real("country") or "N/A"

        log.info(
            "POSTBACK: uid=%s status=%s dep=%.2f country=%s",
            uid, status, sumdep, country
        )

        if uid:
            db_save_trader(uid, sumdep, status, country)
            if sumdep >= MIN_DEPOSIT:
                for chat_id, state in list(_state_cache.items()):
                    if str(state.get("trader_id")) == str(uid) and state.get("step") != "done":
                        set_state(chat_id, step="done", deposit=sumdep)
                        cancel_reminders(chat_id)
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
                            log.info(
                                "Auto-sent VIP to chat_id=%s via postback", chat_id
                            )
                        except Exception as exc:
                            log.error(
                                "VIP auto-send error for chat_id=%s: %s",
                                chat_id, exc
                            )
                        break
    except Exception as exc:
        log.error(
            "handle_postback error: %s\n%s", exc, traceback.format_exc()
        )
    return web.Response(text="OK")


async def handle_addid(request: web.Request) -> web.Response:
    try:
        uid = request.rel_url.query.get("uid", "").strip()
        key = request.rel_url.query.get("key", "")
        if key != "quotexadmin2024":
            return web.Response(text="Forbidden", status=403)
        if uid:
            db_save_trader(uid, 0.0, "manual", "")
            log.info("Manual add uid=%s", uid)
            return web.Response(text=f"Added: {uid}")
    except Exception as exc:
        log.error("handle_addid error: %s", exc)
    return web.Response(text="No uid")


async def handle_telegram(request: web.Request) -> web.Response:
    try:
        data = await request.json()
        update = Update.de_json(data, tg_app.bot)
        await tg_app.process_update(update)
    except Exception as exc:
        log.error("handle_telegram error: %s", exc)
    return web.Response(text="OK")


async def handle_health(request: web.Request) -> web.Response:
    """Health check endpoint for Railway monitoring."""
    try:
        conn = get_db_with_retry(max_retries=2)
        conn.close()
        db_ok = True
    except Exception:
        db_ok = False

    status = "ok" if db_ok else "degraded"
    code   = 200 if db_ok else 503
    return web.Response(
        text=f'{{"status":"{status}","db":{str(db_ok).lower()}}}',
        content_type="application/json",
        status=code
    )


# ─── GRACEFUL SHUTDOWN ────────────────────────────────────────────────────────
async def graceful_shutdown(sig_name: str):
    log.info("Received %s — shutting down gracefully...", sig_name)

    if scheduler and scheduler.running:
        scheduler.shutdown(wait=False)
        log.info("APScheduler stopped")

    if tg_app:
        try:
            await tg_app.stop()
            await tg_app.shutdown()
            log.info("Telegram application stopped")
        except Exception as exc:
            log.error("Error stopping Telegram app: %s", exc)

    # Cancel all remaining tasks
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    for task in tasks:
        task.cancel()
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)
        log.info("Cancelled %d pending tasks", len(tasks))

    if _shutdown_event:
        _shutdown_event.set()

    log.info("Shutdown complete")


# ─── MAIN ─────────────────────────────────────────────────────────────────────
async def main():
    import telegram
    log.info("python-telegram-bot version: %s", telegram.__version__)
    log.info("Starting Trading Noah Bot...")

    global tg_app, scheduler, _shutdown_event
    _shutdown_event = asyncio.Event()

    # ── Schema ────────────────────────────────────────────────────────────
    _ensure_schema()

    # ── APScheduler ───────────────────────────────────────────────────────
    scheduler = AsyncIOScheduler(
        jobstores={"default": MemoryJobStore()},
        job_defaults={"coalesce": True, "max_instances": 1},
        timezone="UTC",
    )
    scheduler.start()
    log.info("APScheduler started")

    # ── Telegram Application ──────────────────────────────────────────────
    tg_app = (
        ApplicationBuilder()
        .token(TOKEN)
        .connect_timeout(30)
        .read_timeout(30)
        .write_timeout(30)
        .pool_timeout(30)
        .build()
    )

    tg_app.add_handler(CommandHandler("start", start))
    for i in range(1, 6):
        tg_app.add_handler(CommandHandler(f"preview{i}", preview_reminder))
    tg_app.add_handler(CallbackQueryHandler(button_handler))
    tg_app.add_handler(
        MessageHandler(filters.PHOTO | filters.VIDEO | filters.Document.ALL, photo_handler)
    )
    tg_app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler)
    )

    await tg_app.initialize()
    await tg_app.start()

    # ── Webhook ───────────────────────────────────────────────────────────
    webhook_url = f"https://worker-production-b340.up.railway.app/telegram/{TOKEN}"
    await tg_app.bot.set_webhook(webhook_url, drop_pending_updates=True)
    log.info("Webhook set: %s", webhook_url)

    # ── Signal handlers ───────────────────────────────────────────────────
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(
            sig,
            lambda s=sig: asyncio.create_task(graceful_shutdown(s.name))
        )

    # ── Web server ────────────────────────────────────────────────────────
    web_app = web.Application()
    web_app.router.add_post(f"/telegram/{TOKEN}", handle_telegram)
    web_app.router.add_get("/postback", handle_postback)
    web_app.router.add_get("/addid", handle_addid)
    web_app.router.add_get("/health", handle_health)
    web_app.router.add_get("/", lambda r: web.Response(text="Trading Noah Bot Running ✅"))

    runner = web.AppRunner(web_app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    log.info("Web server running on port %d", PORT)
    log.info("Trading Noah Bot is live ✅")

    # ── Run until shutdown ────────────────────────────────────────────────
    try:
        await _shutdown_event.wait()
    except asyncio.CancelledError:
        pass
    finally:
        await runner.cleanup()
        log.info("Web server stopped")


if __name__ == "__main__":
    backoff = 1
    max_backoff = 30
    attempt = 0
    max_attempts = 10

    while True:
        attempt += 1
        try:
            log.info("Bot startup attempt %d", attempt)
            asyncio.run(main())
            log.info("Bot exited cleanly")
            break
        except KeyboardInterrupt:
            log.info("Interrupted by user — exiting")
            break
        except Exception as exc:
            log.critical(
                "Bot crashed (attempt %d/%d): %s\n%s",
                attempt, max_attempts, exc, traceback.format_exc()
            )
            if attempt >= max_attempts:
                log.critical(
                    "Max reconnection attempts reached — exiting for Railway to restart"
                )
                break
            log.info("Reconnecting in %ds...", backoff)
            time.sleep(backoff)
            backoff = min(backoff * 2, max_backoff)
