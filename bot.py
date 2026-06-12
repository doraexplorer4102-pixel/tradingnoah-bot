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

# ─── CONFIG ───────────────────────────────────────────────────────────────────
TOKEN        = "8972809832:AAEyWhpky-MUIY9Q7pm1pOTQzKgYbk1gRcw"
VIP_LINK     = "https://t.me/+H3isrme8c3BiNDg1"
AFFILIATE    = "https://broker-qx.pro/sign-up/?lid=1504736"
SUPPORT      = "https://t.me/TRADELIKENOAH"
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:DEfYBWltENxssYQNpworlKPeKVSKUuyQ@acela.proxy.rlwy.net:19828/railway")
MIN_DEPOSIT  = 20

VIDEO_REMINDER = "BAACAgUAAxkBAAFMQIxqLCy8iLgzzjwMiMFm4ahJi-N-iwACQCQAAmS9YFWS4sMNJoZYFjwE"
VIDEO_DEPOSIT  = "BQACAgUAAxkBAAFMQI5qLCzLxgL0oM6v_DRoWsq0R6ecMAACQiQAAmS9YFXmR4aJiqZyKjwE"
BONUS_PHOTO    = "AgACAgUAAxkBAAMZaidQ8AAB-XcWZ92dfh1Nyj12vp9tAAL9D2sb2mc5VTJ5ySC9Sop4AQADAgADeQADOwQ"

# ─── PREMIUM EMOJIS ───────────────────────────────────────────────────────────
def pe(eid, fb): return f'<tg-emoji emoji-id="{eid}">{fb}</tg-emoji>'

E_FIRE    = pe("5424972470023104089", "🔥")
E_DIAMOND = pe("5427168083074628963", "💎")
E_ROCKET  = pe("5188481279963715781", "🚀")
E_MONEY   = pe("5224257782013769471", "💰")
E_STAR    = pe("5438496463044752972", "⭐")
E_CROWN   = pe("5217822164362739968", "👑")
E_TROPHY  = pe("5413566144986503832", "🏆")
E_CHART   = pe("5244837092042750681", "📈")  # NEW ID
E_GIFT    = pe("5203996991054432397", "🎁")
E_CHECK   = pe("5206607081334906820", "✅")
E_CROSS   = pe("5210952531676504517", "❌")
E_WARN    = pe("5420323339723881652", "⚠️")
E_SHIELD  = pe("5197288647275071607", "🛡")
E_KEY     = pe("5307843983102204243", "🔑")
E_LINK    = pe("5271604874419647061", "🔗")
E_PHONE   = pe("5253742260054409879", "✉️")
E_CLOCK   = pe("5431807687136395567", "⏰")
E_PARTY   = pe("5461151367559141950", "🎉")
E_HAND    = pe("5305522282695768654", "👇")
E_EYES    = pe("5210956306952758910", "👀")
E_TARGET  = pe("6185808707985608949", "🎯")  # NEW
E_THUMBS  = pe("5337080053119336309", "👍")  # NEW
E_CHAT    = pe("5443038326535759644", "💬")  # NEW

user_state: dict = {}

# ─── DATABASE ─────────────────────────────────────────────────────────────────

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
        print(f"DB get error: {e}")
        return None

# ─── STATE ────────────────────────────────────────────────────────────────────

def get_state(chat_id):
    if chat_id not in user_state:
        user_state[chat_id] = {"step": "start", "trader_id": None, "deposit": 0.0, "reminder_task": None}
    return user_state[chat_id]

def cancel_reminder(state):
    if state.get("reminder_task") and not state["reminder_task"].done():
        state["reminder_task"].cancel()

# ─── COLORED KEYBOARDS ────────────────────────────────────────────────────────
# Button colors in Telegram are determined by the FIRST emoji in button text:
# 🟢 Green  = ✅ 🟢 💚
# 🔴 Red    = ❌ 🔴 
# 🟡 Yellow = ⭐ 🌟 ⚠️
# 🔵 Blue   = 🔵 💙 📘
# 🟣 Purple = 💜 🔮
# ⚫ Dark   = 🖤 ⚫

def support_btn():
    return InlineKeyboardButton("🔵 Contact Support 24/7 💬", url=SUPPORT)

def register_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🟢 REGISTER FREE NOW ⭐", url=AFFILIATE)],
        [InlineKeyboardButton("🟡 I HAVE REGISTERED 🔑", callback_data="registered")],
        [InlineKeyboardButton("🔵 CONTACT SUPPORT 💬", url=SUPPORT)],
    ])

def deposit_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🟢 Claim 50% Bonus NOW 🎁", callback_data="claim_bonus")],
        [InlineKeyboardButton("🔴 I Have Deposited (Re-Check) 🔄", callback_data="deposited")],
        [InlineKeyboardButton("🔵 Contact Support 💬", url=SUPPORT)],
    ])

def reject_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🟢 Register With Our Link ⭐", url=AFFILIATE)],
        [InlineKeyboardButton("🟡 Try Again With Correct ID 🔄", callback_data="try_again")],
        [InlineKeyboardButton("🔵 Contact Support 💬", url=SUPPORT)],
    ])

def reminder_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🟢 Create Free Account Now 🚀", url=AFFILIATE)],
        [InlineKeyboardButton("🟢 Click Here To Join VIP 🔥", url=AFFILIATE)],
        [InlineKeyboardButton("🔵 Contact Support 💬", url=SUPPORT)],
    ])

def bonus_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🟢 Deposit Now & Get 50% Bonus 💥", url=AFFILIATE)],
        [InlineKeyboardButton("🔴 I Have Deposited ✅", callback_data="deposited")],
        [InlineKeyboardButton("🔵 Contact Support 💬", url=SUPPORT)],
    ])

def vip_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🟣 JOIN VIP SIGNALS GROUP 👑", url=VIP_LINK)],
        [InlineKeyboardButton("🔵 Contact Support 💬", url=SUPPORT)],
    ])

def support_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔵 Contact Support 24/7 💬", url=SUPPORT)]
    ])

def recheck_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🟢 Deposit Now 💰", url=AFFILIATE)],
        [InlineKeyboardButton("🔴 I Have Deposited (Re-Check) 🔄", callback_data="deposited")],
        [InlineKeyboardButton("🔵 Contact Support 💬", url=SUPPORT)],
    ])

# ─── REMINDER ─────────────────────────────────────────────────────────────────

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
                f"<b>{E_EYES} Bro, it looks like you still haven't created your account! {E_WARN}\n\n"
                f"{E_FIRE} See the LIVE benefits and results of my VIP members who are making money DAILY! {E_CHART}\n\n"
                f"{E_MONEY} My members are doubling their accounts RIGHT NOW! {E_ROCKET}\n\n"
                f"{E_HAND} Create your account NOW using this link and send me your Trader ID!\n\n"
                f"{E_CLOCK} Don't miss out — this opportunity won't last forever! {E_WARN}</b>"
            ),
            parse_mode=ParseMode.HTML,
            reply_markup=reminder_keyboard()
        )
    except Exception as e:
        print(f"Reminder error: {e}")

# ─── ID VERIFICATION ──────────────────────────────────────────────────────────

async def verify_id_then_respond(uid, chat_id, bot):
    state = get_state(chat_id)
    cancel_reminder(state)

    msg = await bot.send_message(
        chat_id=chat_id,
        text=f"<b>{E_EYES} Verifying ID <code>{uid}</code>... Please wait!</b>",
        parse_mode=ParseMode.HTML
    )

    trader = db_get_trader(uid)
    if not trader:
        for _ in range(10):
            await asyncio.sleep(3)
            trader = db_get_trader(uid)
            if trader:
                break

    if not trader:
        state["step"] = "awaiting_id"
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=msg.message_id,
            text=(
                f"<b>{E_CROSS} Bro, this account is NOT registered through my link! {E_WARN}\n\n"
                f"Please re-check and send the correct Trader ID. {E_EYES}\n\n"
                f"{E_CHAT} If you are facing any problem, please contact us anytime.\n"
                f"{E_CLOCK} Our team is available 24/7!</b>"
            ),
            parse_mode=ParseMode.HTML,
            reply_markup=reject_keyboard()
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
            chat_id=chat_id,
            message_id=msg.message_id,
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
            parse_mode=ParseMode.HTML,
            reply_markup=vip_keyboard()
        )
    else:
        state["step"] = "awaiting_deposit"
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=msg.message_id,
            text=f"<b>{E_CHECK} ID <code>{uid}</code> linked! {E_EYES} Checking deposit...</b>",
            parse_mode=ParseMode.HTML
        )
        await bot.send_video(
            chat_id=chat_id,
            video=VIDEO_DEPOSIT,
            caption=(
                f"<b>{E_WARN} ACCOUNT LINKED — $0.00 BALANCE {E_WARN}\n\n"
                f"👆 Watch the video on how to deposit, or contact support for help.\n\n"
                f"{E_EYES} I found your Quotex ID <code>{uid}</code>, but your balance is still ZERO!\n\n"
                f"━━━━━━━━━━━━━━━━━━━\n\n"
                f"{E_GIFT} SPECIAL BONUS UNLOCKED! {E_PARTY}\n\n"
                f"Use this 50% bonus code:\n"
                f"{E_FIRE} Promo Code: <code>NOAH50</code> {E_FIRE}\n\n"
                f"{E_WARN} This code automatically EXPIRES within 15 minutes!\n\n"
                f"{E_MONEY} Deposit the required amount and click Re-Check {E_CHECK}</b>"
            ),
            parse_mode=ParseMode.HTML,
            reply_markup=deposit_keyboard()
        )

# ─── HANDLERS ─────────────────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    state = get_state(chat_id)
    cancel_reminder(state)
    state.update({"step": "start", "trader_id": None, "deposit": 0.0})

    await update.message.reply_sticker(
        sticker="CAACAgUAAxkBAAFL9cVqKCa70-hZ2BsucTxBmLtRI2PFMAACBxIAArIYAAFXuG3a4VpEuLw7BA"
    )
    await update.message.reply_video_note(
        video_note="DQACAgUAAxkBAAMbaidRKZuu4TnoWbcqd3A_KLQByFEAAs4cAAJfGjFXsw34l8lliF47BA"
    )
    await update.message.reply_photo(
        photo="AgACAgUAAxkBAAMZaidQ8AAB-XcWZ92dfh1Nyj12vp9tAAL9D2sb2mc5VTJ5ySC9Sop4AQADAgADeQADOwQ",
        caption=(
            f"<b>{E_TROPHY} You're Here Because You Want To Earn Money {E_MONEY}\n\n"
            f"{E_HAND} Join My All Channels {E_CHART} Below & Recover Your Lifetime Losses {E_CHART}\n\n"
            f"{E_FIRE} Start Earning Money Today {E_ROCKET}</b>"
        ),
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🟢 FREE VIP GROUP 📈", url="https://t.me/+s_guD0HJ0B9kYWM1")],
            [InlineKeyboardButton("🔴 JOIN LOSS RECOVERY 🎯", url="https://t.me/+s_guD0HJ0B9kYWM1")],
            [InlineKeyboardButton("🔵 CONTACT FOR HELP 💬", url=SUPPORT)],
        ])
    )

    await asyncio.sleep(10)

    await update.message.reply_text(
        f"<b>Hello {E_TROPHY} Are You Ready To Earn Money With Trading 🕯️ Without Experience\n\n"
        f"{E_CHART} I Helped 10,000+ New Members To Start EARNING {E_ROCKET}\n\n"
        f"{E_WARN} I Shared The Result Of My Client Earning With Me {E_HAND}</b>",
        parse_mode=ParseMode.HTML
    )

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
    await context.bot.send_media_group(chat_id=chat_id, media=media)

    await update.message.reply_text(
        f"<b>👩‍💻 Bro, What Is Your Name And What's Your Country? 🌍\n\n"
        f"🆕 It Will Help Us To Understand Each Other Better {E_TROPHY}</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=support_keyboard()
    )

    await asyncio.sleep(20)

    await update.message.reply_video(
        video="BAACAgUAAxkBAAOKaidpD_-7HAnZ9D2d-yGBmsLMW_QAAjcYAAI1GzlXipdJ8rzcwTs7BA",
        caption=(
            f"<b>{E_MONEY} Okay, So To Start Earning {E_MONEY} The First Step Is To Register "
            f"A Trading Account {E_LINK}\n\n"
            f"{E_HAND} Watch The Video & Just Click On Here {E_HAND}</b>"
        ),
        parse_mode=ParseMode.HTML,
        reply_markup=register_keyboard()
    )

    state["reminder_task"] = asyncio.create_task(send_reminder(chat_id, context.bot))


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    state = get_state(chat_id)

    if query.data == "registered":
        cancel_reminder(state)
        state["step"] = "awaiting_id"
        await query.message.reply_text(
            f"<b>{E_PARTY} Congratulations! You're just one step away! {E_FIRE}\n\n"
            f"━━━━━━━━━━━━━━━━━━━\n\n"
            f"{E_EYES} Please follow these steps to find your Trader ID:\n\n"
            f"1️⃣ Open your <b>Quotex account</b>\n"
            f"2️⃣ Go to <b>My Account</b>\n"
            f"3️⃣ You will see your <b>Trader ID</b> there\n"
            f"4️⃣ Reply with that <b>8-digit code</b> {E_HAND}</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=support_keyboard()
        )

    elif query.data == "try_again":
        state["step"] = "awaiting_id"
        await query.message.reply_text(
            f"<b>🔄 Please send your correct Trader ID {E_EYES}\n\n"
            f"👉 Find it in your Quotex dashboard → <b>My Account</b>\n\n"
            f"Just type and send your ID number {E_HAND}</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=support_keyboard()
        )

    elif query.data == "claim_bonus":
        await query.message.reply_photo(
            photo=BONUS_PHOTO,
            caption=(
                f"<b>{E_GIFT} 50% Deposit Bonus Code FREE!! {E_PARTY}\n\n"
                f"{E_FIRE} Code: <code>NOAH50</code> {E_FIRE}\n\n"
                f"Simply enter the promo code <b>NOAH50</b> when making your deposit.\n\n"
                f"{E_WARN} Promo codes can only be used by accounts created using our link.\n\n"
                f"{E_CHECK} After depositing, please send me your Trader ID again\n"
                f"or click 'I Have Deposited' {E_HAND}</b>"
            ),
            parse_mode=ParseMode.HTML,
            reply_markup=bonus_keyboard()
        )

    elif query.data == "deposited":
        uid = state.get("trader_id")
        if not uid:
            await query.message.reply_text(
                f"<b>{E_WARN} Please send your Trader ID first! {E_HAND}</b>",
                parse_mode=ParseMode.HTML,
                reply_markup=support_keyboard()
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
                f"{E_FIRE} Join our Exclusive VIP Signals Group NOW:\n\n"
                f"{E_DIAMOND} {VIP_LINK} {E_DIAMOND}\n\n"
                f"{E_THUMBS} Welcome to the winning team! {E_TROPHY}</b>",
                parse_mode=ParseMode.HTML,
                reply_markup=vip_keyboard()
            )
        else:
            await query.message.reply_text(
                f"<b>{E_WARN} Bro, your balance is still ZERO! {E_CROSS}\n\n"
                f"Account (ID: <code>{uid}</code>) shows: <b>${dep:.2f}</b>\n\n"
                f"{E_MONEY} Please deposit <b>$20 or more</b> and click Re-Check! {E_HAND}</b>",
                parse_mode=ParseMode.HTML,
                reply_markup=recheck_keyboard()
            )


async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    state = get_state(chat_id)
    text = update.message.text.strip()

    if state["step"] == "awaiting_id":
        if not text.isdigit():
            await update.message.reply_text(
                f"<b>{E_WARN} Please send only numbers (e.g. <code>89057949</code>) {E_HAND}</b>",
                parse_mode=ParseMode.HTML,
                reply_markup=support_keyboard()
            )
            return
        state["step"] = "checking"
        asyncio.create_task(verify_id_then_respond(text, chat_id, context.bot))

    elif state["step"] == "awaiting_deposit":
        if text.isdigit():
            state["step"] = "checking"
            asyncio.create_task(verify_id_then_respond(text, chat_id, context.bot))


# ─── MAIN ─────────────────────────────────────────────────────────────────────

tg_app = ApplicationBuilder().token(TOKEN).build()
tg_app.add_handler(CommandHandler("start", start))
tg_app.add_handler(CallbackQueryHandler(button_handler))
tg_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

print("✅ Trading Noah Bot Running...")
tg_app.run_polling(drop_pending_updates=True)
