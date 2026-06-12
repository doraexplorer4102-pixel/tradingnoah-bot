import os
import asyncio
import ssl
from datetime import datetime
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

# Video file IDs
VIDEO_REMINDER = "BAACAgUAAxkBAAFMQIxqLCy8iLgzzjwMiMFm4ahJi-N-iwACQCQAAmS9YFWS4sMNJoZYFjwE"
VIDEO_DEPOSIT  = "BQACAgUAAxkBAAFMQI5qLCzLxgL0oM6v_DRoWsq0R6ecMAACQiQAAmS9YFXmR4aJiqZyKjwE"
BONUS_PHOTO    = "AgACAgUAAxkBAAMZaidQ8AAB-XcWZ92dfh1Nyj12vp9tAAL9D2sb2mc5VTJ5ySC9Sop4AQADAgADeQADOwQ"

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
        rows = conn.run(
            "SELECT uid, deposit FROM verified_traders WHERE uid = :uid",
            uid=uid
        )
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
        user_state[chat_id] = {
            "step": "start",
            "trader_id": None,
            "deposit": 0.0,
            "reminder_task": None
        }
    return user_state[chat_id]

# ─── KEYBOARDS ────────────────────────────────────────────────────────────────

def support_button():
    return [InlineKeyboardButton("📩 Contact Support", url=SUPPORT)]

def deposit_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎁 Claim 50% Bonus Now", callback_data="claim_bonus")],
        [InlineKeyboardButton("✅ I Have Deposited", callback_data="deposited")],
        [InlineKeyboardButton("📩 Contact Support", url=SUPPORT)],
    ])

def reject_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔗 Register with Our Link", url=AFFILIATE)],
        [InlineKeyboardButton("🔄 Try Again with Correct ID", callback_data="try_again")],
        support_button(),
    ])

def reminder_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 Create Free Account Now", url=AFFILIATE)],
        [InlineKeyboardButton("👆 Click Here", url=AFFILIATE)],
        support_button(),
    ])

def bonus_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎁 Claim 50% Bonus Now", url=AFFILIATE)],
        [InlineKeyboardButton("✅ I Have Deposited", callback_data="deposited")],
        support_button(),
    ])

# ─── REMINDER TASK ────────────────────────────────────────────────────────────

async def send_reminder(chat_id, bot):
    await asyncio.sleep(600)  # 10 minutes
    state = get_state(chat_id)
    if state["step"] not in ("start", "awaiting_id"):
        return
    try:
        await bot.send_video(
            chat_id=chat_id,
            video=VIDEO_REMINDER,
            caption=(
                "<b>Bro, it looks like you still haven't created your account. 😕\n\n"
                "See the live benefits and results of my VIP members who are making money daily! 💰📈\n\n"
                "Create your account now using this link and send me your Trader ID. 👇</b>"
            ),
            parse_mode=ParseMode.HTML,
            reply_markup=reminder_keyboard()
        )
    except Exception as e:
        print(f"Reminder error: {e}")

def cancel_reminder(state):
    if state.get("reminder_task") and not state["reminder_task"].done():
        state["reminder_task"].cancel()

# ─── ID VERIFICATION ──────────────────────────────────────────────────────────

async def verify_id_then_respond(uid, chat_id, bot):
    state = get_state(chat_id)
    cancel_reminder(state)

    msg = await bot.send_message(
        chat_id=chat_id,
        text=f"🔍 <b>Verifying ID <code>{uid}</code>...</b>",
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
        # Not from affiliate link
        state["step"] = "awaiting_id"
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=msg.message_id,
            text=(
                "<b>❌ Bro, this account is not registered through my link.\n\n"
                "Please re-check and send the correct Trader ID.\n\n"
                "If you are facing any problem, please contact us anytime.\n"
                "Our team is available 24/7. 🕐</b>"
            ),
            parse_mode=ParseMode.HTML,
            reply_markup=reject_keyboard()
        )
        # Restart reminder
        state["reminder_task"] = asyncio.create_task(send_reminder(chat_id, bot))
        return

    dep = trader["deposit"]
    state["trader_id"] = uid
    state["deposit"] = dep

    if dep >= MIN_DEPOSIT:
        # Already deposited — grant VIP
        state["step"] = "done"
        cancel_reminder(state)
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=msg.message_id,
            text=f"<b>✅ ID <code>{uid}</code> verified! Deposit confirmed! Granting VIP... 🚀</b>",
            parse_mode=ParseMode.HTML
        )
        await bot.send_message(
            chat_id=chat_id,
            text=(
                "<b>🎉 Welcome to VIP!\n\n"
                "━━━━━━━━━━━━━━━━━━━\n"
                f"🚀 Join our Exclusive VIP Signals Group:\n\n"
                f"👉 {VIP_LINK}\n\n"
                "Welcome to the winning team! 🏆</b>"
            ),
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([support_button()])
        )
    else:
        # Registered but no deposit
        state["step"] = "awaiting_deposit"
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=msg.message_id,
            text=f"<b>✅ ID <code>{uid}</code> linked! Checking deposit...</b>",
            parse_mode=ParseMode.HTML
        )
        await bot.send_video(
            chat_id=chat_id,
            video=VIDEO_DEPOSIT,
            caption=(
                "<b>👆 Watch the video on how to deposit, or contact support for help.\n\n"
                "‼️ ACCOUNT LINKED — $0.00 BALANCE\n\n"
                f"I found your Quotex ID <code>{uid}</code>, but your balance is still zero.\n\n"
                "😀 SPECIAL BONUS UNLOCKED\n\n"
                "Use this 50% bonus code:\n"
                "🎁 Promo Code: <code>NOAH50</code>\n\n"
                "⚠️ Warning: This code automatically expires within 15 minutes.\n\n"
                "Deposit the required amount and click Re-Check ✅</b>"
            ),
            parse_mode=ParseMode.HTML,
            reply_markup=deposit_keyboard()
        )

# ─── BOT HANDLERS ─────────────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    state = get_state(chat_id)
    cancel_reminder(state)
    state["step"] = "start"
    state["trader_id"] = None
    state["deposit"] = 0.0

    # 1) Sticker
    await update.message.reply_sticker(
        sticker="CAACAgUAAxkBAAFL9cVqKCa70-hZ2BsucTxBmLtRI2PFMAACBxIAArIYAAFXuG3a4VpEuLw7BA"
    )

    # 2) Round Video
    await update.message.reply_video_note(
        video_note="DQACAgUAAxkBAAMbaidRKZuu4TnoWbcqd3A_KLQByFEAAs4cAAJfGjFXsw34l8lliF47BA"
    )

    # 3) Photo + Buttons
    await update.message.reply_photo(
        photo="AgACAgUAAxkBAAMZaidQ8AAB-XcWZ92dfh1Nyj12vp9tAAL9D2sb2mc5VTJ5ySC9Sop4AQADAgADeQADOwQ",
        caption=(
            "<b>🥇 You're Here Because You Want To Earn Money 💵\n\n"
            "👇 Join My All Channels 🌐 Below & Recover Your Lifetime Losses 📈\n\n"
            "🤑 Start Earning Money Today 🚀</b>"
        ),
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("FREE VIP GROUP 📈", url="https://t.me/+s_guD0HJ0B9kYWM1")],
            [InlineKeyboardButton("JOIN LOSS RECOVERY 🎯", url="https://t.me/+s_guD0HJ0B9kYWM1")],
            [InlineKeyboardButton("CONTACT FOR HELP 🤝", url=SUPPORT)],
        ])
    )

    await asyncio.sleep(10)

    # 5) Intro message
    await update.message.reply_text(
        "<b>Hello🤝 Are You Ready To Earn Money With Trading 🕯️ Without Experience\n\n"
        "📈 I Helped 10,000+ New Members To Start EARNING 🚀\n\n"
        "⚠️ I Shared The Result Of My Client Earning With Me 👇</b>",
        parse_mode=ParseMode.HTML
    )

    # 6) Media Album
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

    # 7) Ask name/country
    await update.message.reply_text(
        "<b>👩‍💻 Bro, What Is Your Name And What's Your Country? 🌍\n\n"
        "🆕 It Will Help Us To Understand Each Other Better 🤝</b>",
        parse_mode=ParseMode.HTML
    )

    await asyncio.sleep(20)

    # 9) Registration video
    await update.message.reply_video(
        video="BAACAgUAAxkBAAOKaidpD_-7HAnZ9D2d-yGBmsLMW_QAAjcYAAI1GzlXipdJ8rzcwTs7BA",
        caption=(
            "<b>Okay, So To Start Earning 💰 The First Step Is To Register "
            "A Trading Account 🔗\n\n"
            "👇 Watch The Video & Just Click On Here ⬇️</b>"
        ),
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔗 REGISTER", url=AFFILIATE)],
            [InlineKeyboardButton("🔑 I HAVE REGISTERED", callback_data="registered")],
            [InlineKeyboardButton("📩 CONTACT SUPPORT", url=SUPPORT)],
        ])
    )

    # Start 10-minute reminder
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
            "<b>🎉 Congratulations! You're just one step away.\n\n"
            "━━━━━━━━━━━━━━━━━━━\n\n"
            "Please follow these steps to find your Trader ID:\n\n"
            "1️⃣ Open your Quotex account\n"
            "2️⃣ Go to <b>My Account</b>\n"
            "3️⃣ You will see your <b>Trader ID</b> there\n"
            "4️⃣ Reply with that <b>8-digit code</b> 👇</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([support_button()])
        )

    elif query.data == "try_again":
        state["step"] = "awaiting_id"
        await query.message.reply_text(
            "<b>🔄 Please send your correct Trader ID\n\n"
            "👉 Find it in your Quotex dashboard → My Account\n\n"
            "Just type and send your ID number 👇</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([support_button()])
        )

    elif query.data == "claim_bonus":
        await query.message.reply_photo(
            photo=BONUS_PHOTO,
            caption=(
                "<b>🎁 50% Deposit Bonus Code FREE!!\n\n"
                "Code: <code>NOAH50</code>\n\n"
                "Simply enter the promo code <b>NOAH50</b> when making your deposit.\n\n"
                "⚠️ Promo codes can only be used by accounts created using this link.\n\n"
                "After depositing, please send me your Trader ID again or click "
                "'I Have Deposited' ✅</b>"
            ),
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💰 Deposit Now", url=AFFILIATE)],
                [InlineKeyboardButton("✅ I Have Deposited", callback_data="deposited")],
                support_button(),
            ])
        )

    elif query.data == "deposited":
        uid = state.get("trader_id")
        if not uid:
            await query.message.reply_text(
                "<b>⚠️ Please send your Trader ID first.</b>",
                parse_mode=ParseMode.HTML
            )
            return
        trader = db_get_trader(uid)
        dep = trader["deposit"] if trader else 0.0
        state["deposit"] = dep

        if dep >= MIN_DEPOSIT:
            state["step"] = "done"
            cancel_reminder(state)
            await query.message.reply_text(
                "<b>🎉 Deposit Confirmed! Welcome to VIP!\n\n"
                "━━━━━━━━━━━━━━━━━━━\n"
                f"🚀 Join our Exclusive VIP Signals Group:\n\n"
                f"👉 {VIP_LINK}\n\n"
                "Welcome to the winning team! 🏆</b>",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([support_button()])
            )
        else:
            await query.message.reply_text(
                "<b>😕 Bro, your balance is still zero.\n\n"
                f"Account (ID: <code>{uid}</code>) shows: <b>${dep:.2f}</b>\n\n"
                f"Please deposit <b>$20 or more</b> and send me your Trader ID again.</b>",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("💰 Deposit Now", url=AFFILIATE)],
                    [InlineKeyboardButton("✅ I Have Deposited", callback_data="deposited")],
                    support_button(),
                ])
            )


async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    state = get_state(chat_id)
    text = update.message.text.strip()

    if state["step"] == "awaiting_id":
        if not text.isdigit():
            await update.message.reply_text(
                "<b>⚠️ Please send only numbers (e.g. <code>89057949</code>)</b>",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([support_button()])
            )
            return
        state["step"] = "checking"
        asyncio.create_task(verify_id_then_respond(text, chat_id, context.bot))

    elif state["step"] == "awaiting_deposit":
        # If they send ID again while waiting for deposit — re-verify
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
