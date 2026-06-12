from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters
from telegram.constants import ParseMode

TOKEN = "8972809832:AAHKRaXFTjyVvCSgQP7Rfcrk97vRXL2nO90"

async def get_file_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.photo:
        fid = update.message.photo[-1].file_id
        print(f"PHOTO: {fid}")
        await update.message.reply_text(f"📸 PHOTO FILE ID:\n`{fid}`", parse_mode=ParseMode.MARKDOWN)
    elif update.message.video:
        fid = update.message.video.file_id
        print(f"VIDEO: {fid}")
        await update.message.reply_text(f"🎥 VIDEO FILE ID:\n`{fid}`", parse_mode=ParseMode.MARKDOWN)
    elif update.message.document:
        fid = update.message.document.file_id
        print(f"DOCUMENT: {fid}")
        await update.message.reply_text(f"📄 DOCUMENT FILE ID:\n`{fid}`", parse_mode=ParseMode.MARKDOWN)

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(MessageHandler(
    filters.PHOTO | filters.VIDEO | filters.Document.ALL,
    get_file_id
))

print("✅ Collector Running...")
app.run_polling(drop_pending_updates=True)
