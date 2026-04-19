import os
import json
import logging
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# --- الإعدادات ---
TOKEN = "8741656871:AAEFrxiiRqvDYBxT7sS7FofW0YSP6VYGJXQ"
# تأكد 100% أن هذا هو الآيدي الخاص بك
MAIN_ADMIN = 6154678499 

DATA_FILE = "mobo_data.json"

# --- خادم وهمي لاستقرار الاستضافة ---
class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"MOBO TUNNEL IS LIVE")

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

# --- وظيفة تسجيل الأوامر في قائمة التليجرام ---
async def set_commands(application: Application):
    commands = [
        BotCommand("start", "تشغيل البوت"),
        BotCommand("addadmin", "إضافة مشرف جديد (للمدير فقط)"),
        BotCommand("setchannel", "ربط قناتك بالبوت"),
        BotCommand("help", "تعليمات الاستخدام")
    ]
    await application.bot.set_my_commands(commands)

# --- الدوال ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    args = context.args

    if args and args[0].startswith("getfile_"):
        admin_id_str = args[0].replace("getfile_", "")
        if admin_id_str in bot_data["latest_files"]:
            file_info = bot_data["latest_files"][admin_id_str]
            await update.message.reply_text("✅ تم التحقق من التفاعل! إليك الملف:")
            await context.bot.copy_message(
                chat_id=user_id,
                from_chat_id=file_info['channel'],
                message_id=file_info['file_id']
            )
        else:
            await update.message.reply_text("❌ عذراً، هذا الرابط منتهي أو الملف غير موجود.")
        return

    await update.message.reply_text(
        "🚀 **مرحباً بك في MOBO TUNNEL**\n\n"
        "أنا بوت احترافي لنشر الملفات مع ميزة التفاعل الإجباري.\n"
        "استخدم زر القائمة (Menu) لرؤية الأوامر المتاحة لك."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 **تعليمات MOBO TUNNEL:**\n\n"
        "1️⃣ أضف البوت مشرفاً في قناتك.\n"
        "2️⃣ أرسل `/setchannel @YourChannel` لربطها.\n"
        "3️⃣ أرسل أي ملف للبوت وسيتم نشره تلقائياً بأزرار التفاعل."
    )

async def add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != MAIN_ADMIN:
        return # يتجاهل الأمر إذا لم تكن المدير الأساسي
    
    if not context.args:
        return await update.message.reply_text("⚠️ يرجى كتابة الآيدي، مثال:\n`/addadmin 1234567` (اضغط للنسخ)", parse_mode="Markdown")
    
    try:
        new_id = int(context.args[0])
        if new_id not in bot_data["admins"]:
            bot_data["admins"].append(new_id)
            save_data()
            await update.message.reply_text(f"✅ تم منح صلاحية أدمن للآيدي: {new_id}")
    except:
        await update.message.reply_text("❌ خطأ في الآيدي، يجب أن يكون أرقاماً فقط.")

async def set_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in bot_data["admins"]:
        return

    if not context.args:
        return await update.message.reply_text("⚠️ يرجى كتابة يوزر القناة، مثال:\n`/setchannel @MyChannel`", parse_mode="Markdown")
    
    channel_user = context.args[0]
    bot_data["channels"][str(user_id)] = channel_user
    save_data()
    await update.message.reply_text(f"✅ تم ربط القناة {channel_user} بحسابك بنجاح.")

async def handle_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if str(user_id) not in bot_data["channels"]:
        return

    channel = bot_data["channels"][str(user_id)]
    bot_info = await context.bot.get_me()

    keyboard = [
        [InlineKeyboardButton("تفاعل للحصول على الملف 📥", url=f"https://t.me/{bot_info.username}?start=getfile_{user_id}")],
        [InlineKeyboardButton("انضم للبوت 🤖", url=f"https://t.me/{bot_info.username}")]
    ]

    try:
        # نشر رسالة التفاعل
        await context.bot.send_message(
            chat_id=channel,
            text="✨ **تحديث جديد! تم رفع ملف (MOBO TUNNEL)**\n\nاضغط على الزر بالأسفل للحصول على الملف مباشرة من البوت.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        # حفظ الملف في القناة (بشكل صامت) لنسخه لاحقاً
        file_msg = await update.message.copy(chat_id=channel, disable_notification=True)
        
        bot_data["latest_files"][str(user_id)] = {"file_id": file_msg.message_id, "channel": channel}
        save_data()
        await update.message.reply_text("✅ تم النشر في القناة بنجاح!")
    except Exception as e:
        await update.message.reply_text(f"❌ خطأ: تأكد أن البوت مشرف في القناة {channel}\n\nالوصف: {e}")

def main():
    app = Application.builder().token(TOKEN).build()

    # الأوامر الجديدة بدون _ وبسيطة
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("addadmin", add_admin))
    app.add_handler(CommandHandler("setchannel", set_channel))
    
    app.add_handler(MessageHandler(filters.Document.ALL | filters.VIDEO | filters.PHOTO | filters.AUDIO, handle_files))

    # تشغيل ميزة تسجيل الأوامر تلقائياً
    print("Mobo Tunnel is Starting...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
