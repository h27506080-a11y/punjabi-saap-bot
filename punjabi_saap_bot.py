import os
import asyncio
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID_RAW = os.getenv("ADMIN_ID")
CONTACT_TEXT = os.getenv("CONTACT_TEXT", "@YOUR_USERNAME")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is missing.")
if not ADMIN_ID_RAW:
    raise RuntimeError("ADMIN_ID is missing.")

ADMIN_ID = int(ADMIN_ID_RAW)

# Media saved by the admin during the current bot run.
# For permanent storage, a database/file can be added later.
media_files = []


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    if not media_files:
        await update.message.reply_text("Abhi demo available nahi hai.")
        return

    sent_messages = []

    for media_type, file_id in media_files:
        try:
            if media_type == "photo":
                msg = await context.bot.send_photo(
                    chat_id=chat_id,
                    photo=file_id,
                    protect_content=True,
                )
            elif media_type == "video":
                msg = await context.bot.send_video(
                    chat_id=chat_id,
                    video=file_id,
                    protect_content=True,
                )
            else:
                continue

            sent_messages.append(msg.message_id)

        except Exception as e:
            print("Media error:", e)

    last_msg = await context.bot.send_message(
        chat_id=chat_id,
        text=f"Demo yahan tak hai.\n\nContact: {CONTACT_TEXT}",
        protect_content=True,
    )
    sent_messages.append(last_msg.message_id)

    await asyncio.sleep(300)

    for message_id in sent_messages:
        try:
            await context.bot.delete_message(
                chat_id=chat_id,
                message_id=message_id,
            )
        except Exception as e:
            print("Delete error:", e)


async def save_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    if update.message.photo:
        file_id = update.message.photo[-1].file_id
        media_files.append(("photo", file_id))
        await update.message.reply_text("✅ Photo save ho gayi.")

    elif update.message.video:
        file_id = update.message.video.file_id
        media_files.append(("video", file_id))
        await update.message.reply_text("✅ Video save ho gayi.")


async def clear_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    media_files.clear()
    await update.message.reply_text("✅ Saari photos/videos clear ho gayi.")


def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("clear", clear_media))
    app.add_handler(
        MessageHandler(filters.PHOTO | filters.VIDEO, save_media)
    )

    print("Bot started...")
    app.run_polling()


if __name__ == "__main__":
    main()
