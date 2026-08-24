import os
import sqlite3
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters, ContextTypes
)

# Environment Variables
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID_RAW = os.environ.get("ADMIN_ID")
CONTACT_TEXT = os.environ.get("CONTACT_TEXT", "@YOUR_USERNAME")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN variable missing")
if not ADMIN_ID_RAW:
    raise ValueError("ADMIN_ID variable missing")

ADMIN_ID = int(ADMIN_ID_RAW.strip())
DB_FILE = "bot_data.db"

# Temporary memory storage for admin uploads while waiting for category selection
admin_pending_media = {}

# ----------------- DATABASE FUNCTIONS ----------------- #

def init_db():
    """Database tables initialize karein"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS media (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lang TEXT NOT NULL,
            type TEXT NOT NULL,
            file_id TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

def save_media_to_db(lang, media_type, file_id):
    """Media item ko database me insert karein"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO media (lang, type, file_id) VALUES (?, ?, ?)",
        (lang, media_type, file_id)
    )
    conn.commit()
    conn.close()

def get_media_from_db(lang):
    """Specific language ke saare media aur voices database se laayein"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute("SELECT type, file_id FROM media WHERE lang = ? AND type IN ('photo', 'video')", (lang,))
    media_list = [{"type": row[0], "file_id": row[1]} for row in cursor.fetchall()]

    cursor.execute("SELECT file_id FROM media WHERE lang = ? AND type = 'voice'", (lang,))
    voices_list = [row[0] for row in cursor.fetchall()]

    conn.close()
    return media_list, voices_list

def clear_db():
    """Saara database clear karein"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM media")
    conn.commit()
    conn.close()

# Initialize DB on start
init_db()

# ----------------- BOT HANDLERS ----------------- #

# User /start handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("🇮🇳 Hindi", callback_data="user_lang_hindi"),
            InlineKeyboardButton("ੴ Punjabi", callback_data="user_lang_punjabi")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Please select your language / ਆਪਣੀ ਭਾਸ਼ਾ ਚੁਣੋ:",
        reply_markup=reply_markup
    )

# Helper function to delete temporary media messages
async def delete_messages_later(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    for msg in job.data:
        try:
            await msg.delete()
        except Exception as e:
            print(f"Error deleting media message: {e}")

# Admin media upload handler
async def handle_admin_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        return

    file_id = None
    media_type = None

    if update.message.photo:
        file_id = update.message.photo[-1].file_id
        media_type = "photo"
    elif update.message.video:
        file_id = update.message.video.file_id
        media_type = "video"
    elif update.message.voice:
        file_id = update.message.voice.file_id
        media_type = "voice"

    if not file_id:
        return

    # Store media temporarily in memory for category selection
    admin_pending_media[user_id] = {
        "file_id": file_id,
        "type": media_type
    }

    keyboard = [
        [
            InlineKeyboardButton("🇮🇳 Hindi Me Save Karein", callback_data="save_media_hindi"),
            InlineKeyboardButton("ੴ Punjabi Me Save Karein", callback_data="save_media_punjabi")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"Is {media_type.upper()} ko kis category me save karna chahte hain?",
        reply_markup=reply_markup
    )

# Callback Query Handler for Buttons
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    user_id = query.from_user.id

    # 1. Admin Category Selection Logic
    if data.startswith("save_media_"):
        if user_id != ADMIN_ID:
            await query.message.reply_text("Aap admin nahi hain.")
            return

        lang = data.replace("save_media_", "")
        pending = admin_pending_media.get(user_id)

        if not pending:
            await query.message.reply_text("Koi pending file nahi mili. Kripya firse bhejein.")
            return

        # Database me Save karein
        save_media_to_db(lang, pending["type"], pending["file_id"])
        del admin_pending_media[user_id]

        await query.edit_message_text(
            f"✅ {pending['type'].upper()} successfully Database [{lang.upper()}] category me save ho gaya!"
        )
        return

    # 2. User Language Selection Logic
    if data.startswith("user_lang_"):
        lang = data.replace("user_lang_", "")

        # Database se fetch karein
        media_list, voices_list = get_media_from_db(lang)

        if not media_list and not voices_list:
            await query.message.reply_text("Abhi is bhasha me koi media ya voice available nahi hai.")
            return

        temporary_media_messages = []

        # Step 1: Send All Photos/Videos (Protected Content: Screenshot & Save Blocked)
        for item in media_list:
            if item["type"] == "photo":
                msg = await query.message.reply_photo(
                    photo=item["file_id"],
                    protect_content=True
                )
                temporary_media_messages.append(msg)
            elif item["type"] == "video":
                msg = await query.message.reply_video(
                    video=item["file_id"],
                    protect_content=True
                )
                temporary_media_messages.append(msg)

        # Step 2: Send Text Intro
        if lang == "hindi":
            intro_text = f"👇 Niche Audio Voice Suno 👇\nContact: {CONTACT_TEXT}"
        else:
            intro_text = f"👇 ਹੇਠਾਂ ਦਿੱਤੀ ਆਵਾਜ਼ ਸੁਣੋ 👇\nContact: {CONTACT_TEXT}"

        await query.message.reply_text(intro_text)

        # Step 3: Send Voice Note (Random Choice)
        if voices_list:
            selected_voice = random.choice(voices_list)
            await query.message.reply_voice(
                voice=selected_voice,
                protect_content=True
            )

        # Step 4: Send Username 3 times at the very end
        triple_username_text = f"{CONTACT_TEXT}\n{CONTACT_TEXT}\n{CONTACT_TEXT}"
        await query.message.reply_text(triple_username_text)

        # Schedule Auto-Delete after 180 seconds (3 minutes) for photos/videos
        if temporary_media_messages and context.job_queue:
            context.job_queue.run_once(
                delete_messages_later,
                when=180,
                data=temporary_media_messages
            )

# Clear Command (Admin Only)
async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        return

    clear_db()
    await update.message.reply_text(
        "🧹 Database se sabhi Hindi aur Punjabi photos, videos aur voice notes delete kar diye gaye hain."
    )

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("clear", clear))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(
        MessageHandler(filters.PHOTO | filters.VIDEO | filters.VOICE,
                       handle_admin_media)
    )

    print("Bot is running with SQLite DB...")
    app.run_polling()

if __name__ == "__main__":
    main()
