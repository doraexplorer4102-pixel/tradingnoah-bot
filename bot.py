from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
    InputMediaVideo
)
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from telegram.constants import ParseMode
import asyncio

# Paste your Bot Token here
TOKEN = "8972809832:AAEyWhpky-MUIY9Q7pm1pOTQzKgYbk1gRcw"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    # 1) Premium Animated Sticker
    await update.message.reply_sticker(
        sticker="CAACAgUAAxkBAAFL9cVqKCa70-hZ2BsucTxBmLtRI2PFMAACBxIAArIYAAFXuG3a4VpEuLw7BA"
    )

    # 2) Round Video
    await update.message.reply_video_note(
        video_note="DQACAgUAAxkBAAMbaidRKZuu4TnoWbcqd3A_KLQByFEAAs4cAAJfGjFXsw34l8lliF47BA"
    )

    # 3) Photo + Buttons
    keyboard = [
        [
            InlineKeyboardButton(
                "FREE VIP GROUP 📈",
                url="https://t.me/+s_guD0HJ0B9kYWM1"
            )
        ],
        [
            InlineKeyboardButton(
                "JOIN LOSS RECOVERY 🎯",
                url="https://t.me/+s_guD0HJ0B9kYWM1"
            )
        ],
        [
            InlineKeyboardButton(
                "CONTACT FOR HELP 🤝",
                url="https://t.me/TRADELIKENOAH"
            )
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

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
        reply_markup=reply_markup
    )

    # 4) Wait 10 Seconds
    await asyncio.sleep(10)

    # 5) Intro Message
    await update.message.reply_text(
        "<b>"
        "Hello🤝 Are You Ready To Earn Money With Trading 🕯️ Without Experience\n\n"
        "📈 I Helped 10,000+ New Members To Start EARNING 🚀\n\n"
        "⚠️ I Shared The Result Of My Client Earning With Me 👇"
        "</b>",
        parse_mode=ParseMode.HTML
    )

    # 6) Media Album (3 Videos + 7 Photos)
    media = [
        InputMediaVideo(
            media="BAACAgUAAxkBAAMtaidXNeAzsfiXzbzTipXYriM1QccAAr4fAALaZzlV3a9DaWKShwg7BA"
        ),
        InputMediaVideo(
            media="BAACAgUAAxkBAAMuaidXP2WTrAFQHjfNb2BEEyFIFNEAAr8fAALaZzlVMwnVMRZdSwQ7BA"
        ),
        InputMediaVideo(
            media="BAACAgUAAxkBAAM2aidbF2H6x4MPd8yJvVaav3-1Rx0AAk4TAAKE-wlUE1J9aR22UGs7BA"
        ),

        InputMediaPhoto(
            media="AgACAgUAAxkBAAMvaidZOKraitAwpTkzLOyuE8asGGQAAngOaxubnDlVOk0XXZUnDVsBAAMCAAN5AAM7BA"
        ),
        InputMediaPhoto(
            media="AgACAgUAAxkBAAMwaidZOD-Rpe2T-663b06c3fSpQ6QAAnkOaxubnDlVadz6EiT1F0QBAAMCAAN5AAM7BA"
        ),
        InputMediaPhoto(
            media="AgACAgUAAxkBAAMxaidZOCzrgkKfUKO130MGuwd8yi0AAnoOaxubnDlV4lsIOqHFWHUBAAMCAAN5AAM7BA"
        ),
        InputMediaPhoto(
            media="AgACAgUAAxkBAAMyaidZOOj3QW-KF9u4jm0Q6p__negAAnsOaxubnDlVQwg-WgLkC_kBAAMCAAN5AAM7BA"
        ),
        InputMediaPhoto(
            media="AgACAgUAAxkBAAMzaidZOJYjCJwT3jrBie1q3bftyPIAAnwOaxubnDlVm9pFyqPCuGgBAAMCAAN5AAM7BA"
        ),
        InputMediaPhoto(
            media="AgACAgUAAxkBAAM0aidZOAIic1LUisuabVtoG-zjErcAAn0OaxubnDlVLe9EI0F79TwBAAMCAAN5AAM7BA"
        ),
        InputMediaPhoto(
            media="AgACAgUAAxkBAAM1aidZONtvc134Omxzz_K_5ENML0EAAn4OaxubnDlVA7ThG7qOcGQBAAMCAAN3AAM7BA"
        )
    ]

    await context.bot.send_media_group(
        chat_id=update.effective_chat.id,
        media=media
    )

    # 7) Ask User Details
    await update.message.reply_text(
        "<b>"
        "👩‍💻 Bro, What Is Your Name And What's Your Country? 🌍\n\n"
        "🆕 It Will Help Us To Understand Each Other Better 🤝"
        "</b>",
        parse_mode=ParseMode.HTML
    )

    # 8) Wait 20 Seconds
    await asyncio.sleep(20)

    # 9) Registration Video
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
            [
                InlineKeyboardButton(
                    "🔗 REGISTER",
                    url="https://broker-qx.pro/sign-up/?lid=1504736"
                )
            ],
            [
                InlineKeyboardButton(
                    "🔑 I HAVE REGISTERED",
                    callback_data="registered"
                )
            ],
            [
                InlineKeyboardButton(
                    "📩 CONTACT SUPPORT",
                    url="https://t.me/TRADELIKENOAH"
                )
            ]
        ])
    )


app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))

print("Bot Running...")

app.run_polling()



