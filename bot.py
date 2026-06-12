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

TOKEN        = "8972809832:AAHKRaXFTjyVvCSgQP7Rfcrk97vRXL2nO90"
VIP_LINK     = "https://t.me/+H3isrme8c3BiNDg1"
AFFILIATE    = "https://broker-qx.pro/sign-up/?lid=1504736"
SUPPORT      = "https://t.me/TRADELIKENOAH"
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:DEfYBWltENxssYQNpworlKPeKVSKUuyQ@acela.proxy.rlwy.net:19828/railway")
MIN_DEPOSIT  = 20
OWNER_ID     = int(os.getenv("OWNER_ID", "8837911637"))

VIDEO_TUTORIAL = "BAACAgUAAxkBAAFMR_JqLHQgDfdvetmVFCu4tVoEmXayHwACkSEAAm6QYFUZ3EZET5TOdjwE"
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

def get_state(chat_id):
    if chat_id not in user_state:
        user_state[chat_id] = {"step": "start", "trader_id": None, "deposit": 0.0, "reminder_task": None}
    return user_state[chat_id]

def cancel_reminder(state):
    if state.get("reminder_task") and not state["reminder_task"].done():
        state["reminder_task"].cancel()

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

async def send_reminder(chat_id, bot):
    await asyncio.sleep(600)
    state = get_state(chat_id)
    if state["step"] not in ("start", "awaiting_id"):
        return
    try:
        await bot.send_video(
            chat_id=chat_id,
            video=VIDEO_REMINDER,
            caption=(
                f"<b>{E_EYES} Bro, you still haven't created your account! {E_WARN}\n\n"
                f"{E_FIRE} See LIVE results of my VIP members making money DAILY! {E_CHART}\n\n"
                f"{E_MONEY} My members are doubling accounts RIGHT NOW! {E_ROCKET}\n\n"
                f"{E_HAND} Create your account NOW and send me your Trader ID!\n\n"
                f"{E_CLOCK} Don't miss out! {E_WARN}</b>"
            ),
            parse_mode=ParseMode.HTML,
            reply_markup=reminder_keyboard()
        )
    except Exception as e:
        print(f"Reminder error: {e}")

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
                [InlineKeyboardButton("📈 FREE VIP GROUP", url="https://t.me/+s_guD0HJ0B9kYWM1")],
                [InlineKeyboardButton("🎯 JOIN LOSS RECOVERY", url="https://t.me/+s_guD0HJ0B9kYWM1")],
                [InlineKeyboardButton("💬 CONTACT SUPPORT 24/7", url=SUPPORT)],
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

        state["reminder_task"] = asyncio.create_task(send_reminder(chat_id, bot))

    except Exception as e:
        import traceback
        print(f"START SEQ ERROR: {e}")
        traceback.print_exc()

async def verify_id_then_respond(uid, chat_id, bot):
    state = get_state(chat_id)
    cancel_reminder(state)

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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    state = get_state(chat_id)
    cancel_reminder(state)
    state.update({"step": "start", "trader_id": None, "deposit": 0.0})
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
                [InlineKeyboardButton("💰 Deposit Now", url=AFFILIATE)],
                [InlineKeyboardButton("🔄 I Have Deposited (Re-Check)", callback_data="deposited")],
                [InlineKeyboardButton("✉️ Contact Support 24/7", url=SUPPORT)],
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
            await update.message.reply_text(
                f"<b>{E_WARN} Please send only numbers (e.g. <code>89057949</code>) {E_HAND}</b>",
                parse_mode=ParseMode.HTML, reply_markup=support_keyboard()
            )
            return
        state["step"] = "checking"
        asyncio.create_task(verify_id_then_respond(text, chat_id, context.bot))
    elif state["step"] == "awaiting_deposit":
        if text.isdigit():
            state["step"] = "checking"
            asyncio.create_task(verify_id_then_respond(text, chat_id, context.bot))


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

async def main():
    global tg_app
    tg_app = ApplicationBuilder().token(TOKEN).build()
    tg_app.add_handler(CommandHandler("start", start))
    tg_app.add_handler(CallbackQueryHandler(button_handler))
    tg_app.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO | filters.Document.ALL, photo_handler))
    tg_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    await tg_app.initialize()
    await tg_app.start()

    # Set webhook
    webhook_url = f"https://worker-production-b340.up.railway.app/telegram/{TOKEN}"
    await tg_app.bot.set_webhook(webhook_url, drop_pending_updates=True)
    print(f"✅ Webhook set: {webhook_url}")

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
