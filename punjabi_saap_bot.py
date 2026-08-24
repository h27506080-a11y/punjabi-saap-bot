import os
import asyncio
import json
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters, ContextTypes
)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID_RAW = os.environ.get("ADMIN_ID")
CONTACT_TEXT = os.environ.get("CONTACT_TEXT", "@YOUR_USERNAME")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN variable missing")
if not ADMIN_ID_RAW:
    raise ValueError("ADMIN_ID variable missing")

ADMIN_ID = int(ADMIN_ID_RAW)
DATA_FILE = "media_data.json"

admin_mode = {}

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "hindi": {"media": [], "voices": []},
        "punjabi": {"media": [], "voices": []}
    }

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

db = load_data()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("🇮🇳 Hindi", callback_data="lang_hindi"),
            InlineKeyboardButton("ੴ Punjabi", callback_data="lang_punjabi")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Please select your language / ਆਪਣੀ ਭਾਸ਼ਾ ਚੁਣੋ:",
        reply_markup=reply_markup
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    lang = query.data.replace("lang_", "")

    if not db[lang]["media"] and not db[lang]["voices"]:
        await query.message.reply_text("Abhi is bhasha me koi demo ya voice nahi hai.")
        return

    temporary_media_messages = []

    if lang == "hindi":
        intro_text = f"👇 Niche Audio Voice Suno 👇\nContact: {CONTACT_TEXT}"
    else:
        intro_text = f"👇 ਹੇਠਾਂ ਦਿੱਤੀ ਆਵਾਜ਼ ਸੁਣੋ 👇\nContact: {CONTACT_TEXT}"

    for item in db[lang]["media"]:
        if item["type"] == "photo":
            msg = await query.message.reply_photo(photo=item["file_id"])
            temporary_media_messages.append(msg)
        elif item["type"] == "video":
            msg = await query.message.reply_video(video=item["file_id"])
            temporary_media_messages.append(msg)

    await query.message.reply_text(intro_text)

    if db[lang]["voices"]:
        selected_voice = random.choice(db[lang]["voices"])
        await query.message.reply_voice(voice=selected_voice)

    triple_username_text = f"{CONTACT_TEXT}\n{CONTACT_TEXT}\n{CONTACT_TEXT}"
    await query.message.reply_text(triple_username_text)

    await asyncio.sleep(180)

    for msg in temporary_media_messages:
        try:
            await msg.delete()
        except Exception as e:
            print(f"Error deleting media message: {e}")

async def set_hindi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id == ADMIN_ID:
        admin_mode[ADMIN_ID] = "hindi"
        await update.message.reply_text(
            "✅ Now adding content to HINDI category. Send photo/video/voice."
        )

async def set_punjabi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id == ADMIN_ID:
        admin_mode[ADMIN_ID] = "punjabi"
        await update.message.reply_text(
            "✅ Now adding content to PUNJABI category. Send photo/video/voice."
        )

async def handle_admin_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        return

    current_lang = admin_mode.get(ADMIN_ID, "hindi")

    if update.message.photo:
        file_id = update.message.photo[-1].file_id
        db[current_lang]["media"].append(
            {"type": "photo", "file_id": file_id}
        )
        save_data(db)
        await update.message.reply_text(
            f"✅ Photo saved in [{current_lang.upper()}]!"
        )

    elif update.message.video:
        file_id = update.message.video.file_id
        db[current_lang]["media"].append(
            {"type": "video", "file_id": file_id}
        )
        save_data(db)
        await update.message.reply_text(
            f"✅ Video saved in [{current_lang.upper()}]!"
        )

    elif update.message.voice:
        file_id = update.message.voice.file_id
        db[current_lang]["voices"].append(file_id)
        save_data(db)
        await update.message.reply_text(
            f"✅ Voice Note saved in [{current_lang.upper()}]!"
        )

async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        return

    db["hindi"] = {"media": [], "voices": []}
    db["punjabi"] = {"media": [], "voices": []}
    save_data(db)
    await update.message.reply_text(
        "🧹 Sabhi Hindi aur Punjabi items delete kar diye gaye hain."
    )

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("set_hindi", set_hindi))
    app.add_handler(CommandHandler("set_punjabi", set_punjabi))
    app.add_handler(CommandHandler("clear", clear))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(
        MessageHandler(filters.PHOTO | filters.VIDEO | filters.VOICE,
                       handle_admin_media)
    )

    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
