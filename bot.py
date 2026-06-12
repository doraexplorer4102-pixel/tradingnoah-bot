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
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:DEfYBWltENxssYQNpworlKPeKVSKUuyQ@acela.proxy.rlwy.net:19828/railway")
MIN_DEPOSIT  = 20

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
        user_state[chat_id] = {"step": "start", "trader_id": None, "deposit": 0.0}
    return user_state[chat_id]

# ─── KEYBOARDS ────────────────────────────────────────────────────────────────

def deposit_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💰 Fund My Account ($20 min)", url=AFFILIATE)],
        [InlineKeyboardButton("✅ I Have Deposited", callback_data="deposited")],
    ])

def reject_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔗 Register with Our Link", url=AFFILIATE)],
        [InlineKeyboardButton("🔄 Try Again with Correct ID", callback_data="try_again")],
    ])

# ─── ID VERIFICATION ──────────────────────────────────────────────────────────

async def verify_id_then_respond(uid, chat_id, bot):
    state = get_state(chat_id)

    msg = await bot.send_message(
        chat_id=chat_id,
        text=f"🔍 <b>Verifying ID <code>{uid}</code>...</b>",
        parse_mode=ParseMode.HTML
    )

    # Check DB immediately, wait up to 30s for postback if not found
    trader = db_get_trader(uid)
    if not trader:
        for _ in range(10):
            await asyncio.sleep(3)
            trader = db_get_trader(uid)
            if trader:
                break

    if not trader:
        state["step"] = "start"
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=msg.message_id,
            text=(
                "<b>❌ ID Not Verified!\n\n"
                f"Trader ID <code>{uid}</code> was not registered through our link.\n\n"
                "To get VIP access, you must create an account using our link.\n\n"
                "👇 Register below and come back with your new ID:</b>"
            ),
            parse_mode=ParseMode.HTML,
            reply_markup=reject_keyboard()
        )
        return

    dep = trader["deposit"]
    state["trader_id"] = uid
    state["deposit"] = dep

    if dep >= MIN_DEPOSIT:
        state["step"] = "done"
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
            parse_mode=ParseMode.HTML
        )
    else:
        state["step"] = "awaiting_deposit"
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=msg.message_id,
            text=(
                f"<b>✅ ID <code>{uid}</code> verified!\n\n"
                "━━━━━━━━━━━━━━━━━━━\n"
                "📋 STEP 3 — Fund Your Account\n\n"
                f"💰 Deposit minimum <b>${MIN_DEPOSIT}</b> to unlock VIP access.\n\n"
                f"Your current balance: <b>${dep:.2f}</b>\n\n"
                "Click below once you have deposited ✅</b>"
            ),
            parse_mode=ParseMode.HTML,
            reply_markup=deposit_keyboard()
        )

# ─── HANDLERS ─────────────────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    state = get_state(chat_id)
    state["step"] = "start"

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
            "<b>"
            "🥇 You're Here Because You Want To Earn Money 💵\n\n"
            "👇 Join My All Channels 🌐 Below & Recover Your Lifetime Losses 📈\n\n"
            "🤑 Start Earning Money Today 🚀"
            "</b>"
        ),
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("FREE VIP GROUP 📈", url="https://t.me/+s_guD0HJ0B9kYWM1")],
            [InlineKeyboardButton("JOIN LOSS RECOVERY 🎯", url="https://t.me/+s_guD0HJ0B9kYWM1")],
            [InlineKeyboardButton("CONTACT FOR HELP 🤝", url="https://t.me/TRADELIKENOAH")],
        ])
    )

    # 4) Wait 10 seconds
    await asyncio.sleep(10)

    # 5) Intro message
    await update.message.reply_text(
        "<b>"
        "Hello🤝 Are You Ready To Earn Money With Trading 🕯️ Without Experience\n\n"
        "📈 I Helped 10,000+ New Members To Start EARNING 🚀\n\n"
        "⚠️ I Shared The Result Of My Client Earning With Me 👇"
        "</b>",
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
        "<b>"
        "👩‍💻 Bro, What Is Your Name And What's Your Country? 🌍\n\n"
        "🆕 It Will Help Us To Understand Each Other Better 🤝"
        "</b>",
        parse_mode=ParseMode.HTML
    )

    # 8) Wait 20 seconds
    await asyncio.sleep(20)

    # 9) Registration video with buttons
    await update.message.reply_video(
        video="BAACAgUAAxkBAAOKaidpD_-7HAnZ9D2d-yGBmsLMW_QAAjcYAAI1GzlXipdJ8rzcwTs7BA",
        caption=(
            "<b>"
            "Okay, So To Start Earning 💰 The First Step Is To Register "
            "A Trading Account 🔗\n\n"
            "👇 Watch The Video & Just Click On Here ⬇️"
            "</b>"
        ),
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔗 REGISTER", url=AFFILIATE)],
            [InlineKeyboardButton("🔑 I HAVE REGISTERED", callback_data="registered")],
            [InlineKeyboardButton("📩 CONTACT SUPPORT", url="https://t.me/TRADELIKENOAH")],
        ])
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    state = get_state(chat_id)

    if query.data == "registered":
        state["step"] = "awaiting_id"
        await query.message.reply_text(
            "<b>✅ Great! You're Registered!\n\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            "📋 STEP 2 — Share your Trader ID\n\n"
            "Please send me your <b>Quotex Trader ID</b>.\n\n"
            "👉 Find it in your Quotex dashboard (top-right corner).\n\n"
            "Just type and send your ID number 👇</b>",
            parse_mode=ParseMode.HTML
        )

    elif query.data == "try_again":
        state["step"] = "awaiting_id"
        await query.message.reply_text(
            "<b>🔄 Please send your correct Trader ID\n\n"
            "👉 Find it in your Quotex dashboard (top-right corner).\n\n"
            "Just type and send your ID number 👇</b>",
            parse_mode=ParseMode.HTML
        )

    elif query.data == "deposited":
        uid = state.get("trader_id")
        trader = db_get_trader(uid)
        dep = trader["deposit"] if trader else 0.0
        state["deposit"] = dep

        if dep >= MIN_DEPOSIT:
            state["step"] = "done"
            await query.message.reply_text(
                "<b>🎉 Deposit Confirmed! Welcome to VIP!\n\n"
                "━━━━━━━━━━━━━━━━━━━\n"
                f"🚀 Join our Exclusive VIP Signals Group:\n\n"
                f"👉 {VIP_LINK}\n\n"
                "Welcome to the winning team! 🏆</b>",
                parse_mode=ParseMode.HTML
            )
        else:
            await query.message.reply_text(
                "<b>⏳ Deposit Not Confirmed Yet\n\n"
                f"Account (ID: <code>{uid}</code>) shows: <b>${dep:.2f}</b>\n\n"
                f"Minimum required: <b>${MIN_DEPOSIT}</b>\n\n"
                "Please deposit at least $20 and try again.</b>",
                parse_mode=ParseMode.HTML,
                reply_markup=deposit_keyboard()
            )


async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    state = get_state(chat_id)
    text = update.message.text.strip()

    if state["step"] == "awaiting_id":
        if not text.isdigit():
            await update.message.reply_text(
                "<b>⚠️ Please send only numbers (e.g. 89057949)</b>",
                parse_mode=ParseMode.HTML
            )
            return
        state["step"] = "checking"
        asyncio.create_task(verify_id_then_respond(text, chat_id, context.bot))


# ─── MAIN ─────────────────────────────────────────────────────────────────────

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button_handler))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

print("✅ Trading Noah Bot Running...")
app.run_polling(drop_pending_updates=True)
