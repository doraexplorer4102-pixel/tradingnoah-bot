from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters
from telegram.constants import ParseMode

TOKEN = "8972809832:AAE1iqYmcpwcGb0TOdfidJ0owsIcCLheBAo"

async def get_file_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.video:
        fid = update.message.video.file_id
        print(f"VIDEO FILE ID: {fid}")
        await update.message.reply_text(f"VIDEO FILE ID:\n`{fid}`", parse_mode=ParseMode.MARKDOWN)
    elif update.message.document:
        fid = update.message.document.file_id
        print(f"DOCUMENT FILE ID: {fid}")
        await update.message.reply_text(f"DOCUMENT FILE ID:\n`{fid}`", parse_mode=ParseMode.MARKDOWN)

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(MessageHandler(filters.VIDEO | filters.Document.ALL, get_file_id))

print("Collector Running...")
app.run_polling(drop_pending_updates=True)
