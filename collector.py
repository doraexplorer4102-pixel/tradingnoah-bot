from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters

TOKEN = "8972809832:AAE1iqYmcpwcGb0TOdfidJ0owsIcCLheBAo"

async def get_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.video:
        print("VIDEO FILE ID:")
        print(update.message.video.file_id)

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(MessageHandler(filters.VIDEO, get_id))

print("VIDEO COLLECTOR RUNNING...")
app.run_polling()