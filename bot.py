import os
import json
import logging
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# --- إعدادات البوت ---
TOKEN = "8741656871:AAEFrxiiRqvDYBxT7sS7FofW0YSP6VYGJXQ"
# استبدل الرقم أدناه بآيدي حسابك في تلجرام (يمكنك الحصول عليه من بوت @userinfobot)
MAIN_ADMIN = 6154678499 

DATA_FILE = "mobo_data.json"

# --- خادم وهمي لإبقاء البوت حياً على الاستضافات ---
class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(b"MOBO TUNNEL is running!")

def run_dummy_server():
    port = int(os.environ.get('PORT', 8080))
    server = HTTPServer(('0.0.0.0', port), DummyHandler)
    server.serve_forever()

threading.Thread(target=run_dummy_server, daemon=True).start()

# --- إدارة البيانات ---
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r") as f:
        bot_data = json.load(f)
else:
    bot_data = {"admins": [MAIN_ADMIN], "channels": {}, "latest_files": {}}

def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump(bot_data, f)

# --- الدوال الأساسية ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    args = context.args

    if args and args[0].startswith("getfile_"):
        admin_id_str = args[0].replace("getfile_", "")
        if admin_id_str in bot_data["latest_files"]:
            file_data = bot_data["latest_files"][admin_id_str]
            await update.message.reply_text("✅ تفاعلك مقبول! إليك أحدث ملف تم نشره:")
            await context.bot.copy_message(
                chat_id=user_id,
                from_chat_id=file_data['channel'],
                message_id=file_data['file_id']
            )
        else:
            await update.message.reply_text("❌ عذراً، لا يوجد ملف متاح حالياً.")
        return

    await update.message.reply_text(
        "🚀 مرحباً بك في **MOBO TUNNEL**\n\n"
        "أنا بوت لإدارة نشر الملفات في القنوات مع نظام التفاعل الإجباري."
    )

async def add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != MAIN_ADMIN: return
    if not context.args: return await update.message.reply_text("أرسل الآيدي بعد الأمر.")
    
    new_admin = int(context.args[0])
    if new_admin not in bot_data["admins"]:
        bot_data["admins"].append(new_admin)
        save_data()
        await update.message.reply_text(f"✅ تم إضافة المشرف {new_admin}")

async def add_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in bot_data["admins"]: return
    if not context.args: return await update.message.reply_text("أرسل معرف القناة @ChannelName")
    
    bot_data["channels"][str(user_id)] = context.args[0]
    save_data()
    await update.message.reply_text(f"✅ تم ربط القناة {context.args[0]}")

async def handle_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if str(user_id) not in bot_data["channels"]: return

    channel = bot_data["channels"][str(user_id)]
    bot_user = (await context.bot.get_me()).username

    keyboard = [
        [InlineKeyboardButton("تفاعل للحصول على الملف 📥", url=f"https://t.me/{bot_user}?start=getfile_{user_id}")],
        [InlineKeyboardButton("انضم للبوت 🤖", url=f"https://t.me/{bot_user}")]
    ]

    try:
        # نشر رسالة التفاعل في القناة
        msg = await context.bot.send_message(
            chat_id=channel,
            text="✨ **تم رفع ملف جديد!**\n\nاضغط على الزر أدناه للحصول عليه مباشرة عبر البوت.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        # إرسال الملف للقناة (مخفي) لحفظه
        file_msg = await update.message.copy(chat_id=channel, disable_notification=True)
        
        # حفظ البيانات
        bot_data["latest_files"][str(user_id)] = {"file_id": file_msg.message_id, "channel": channel}
        save_data()
        await update.message.reply_text("✅ تم النشر بنجاح!")
    except Exception as e:
        await update.message.reply_text(f"❌ خطأ: تأكد أن البوت أدمن في {channel}\n{e}")

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add_admin", add_admin))
    app.add_handler(CommandHandler("add_channel", add_channel))
    app.add_handler(MessageHandler(filters.Document.ALL | filters.VIDEO | filters.PHOTO, handle_files))
    
    print("MOBO TUNNEL Is Active...")
    app.run_polling()

if __name__ == '__main__':
    main()
