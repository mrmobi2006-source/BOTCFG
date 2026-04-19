import os
import json
import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryContext, filters, ContextTypes, CallbackQueryHandler

# إعدادات البوت
TOKEN = "8741656871:AAEFrxiiRqvDYBxT7sS7FofW0YSP6VYGJXQ"
MAIN_ADMIN = 123456789  # ⚠️ ضع الآيدي الخاص بك هنا ⚠️

DATA_FILE = "mobo_data.json"

# إعداد تسجيل الأخطاء
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# تحميل البيانات (الإدمنية، القنوات، أحدث الملفات)
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r") as f:
        bot_data = json.load(f)
else:
    bot_data = {"admins": [MAIN_ADMIN], "channels": {}, "latest_files": {}}

def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump(bot_data, f)

# دالة البداية (Start) وتلقي الملف عبر الرابط العميق
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    args = context.args

    # التحقق مما إذا كان المستخدم قادماً من زر التفاعل (Deep Link)
    if args and args[0].startswith("getfile_"):
        channel_id = args[0].replace("getfile_", "")
        
        # التحقق من وجود ملف حديث لهذه القناة
        if channel_id in bot_data["latest_files"]:
            file_id = bot_data["latest_files"][channel_id]
            await update.message.reply_text("✅ شكراً لتفاعلك! جاري إرسال الملف...")
            # إرسال الملف للمستخدم (سواء كان مستند، فيديو، الخ)
            await context.bot.copy_message(chat_id=user_id, from_chat_id=channel_id, message_id=file_id)
        else:
            await update.message.reply_text("❌ عذراً، لا يوجد ملف متاح حالياً أو أن الملف قديم.")
        return

    await update.message.reply_text(
        "مرحباً بك في بوت MOBO TUNNEL 🚀\n\n"
        "أنا بوت مخصص لإدارة الملفات ونشرها في القنوات مع ميزة التفاعل الإجباري."
    )

# دالة لإضافة أدمن جديد (للمدير الأساسي فقط)
async def add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != MAIN_ADMIN:
        await update.message.reply_text("❌ هذا الأمر مخصص للمدير الأساسي فقط.")
        return
    
    if not context.args:
        await update.message.reply_text("الرجاء إرسال الآيدي بعد الأمر، مثال:\n/add_admin 987654321")
        return
    
    new_admin = int(context.args[0])
    if new_admin not in bot_data["admins"]:
        bot_data["admins"].append(new_admin)
        save_data()
        await update.message.reply_text(f"✅ تم إضافة الآيدي {new_admin} كأدمن بنجاح!")
    else:
        await update.message.reply_text("⚠️ هذا المستخدم أدمن بالفعل.")

# دالة لربط قناة بالأدمن
async def add_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in bot_data["admins"]:
        return
    
    if not context.args:
        await update.message.reply_text("الرجاء إرسال معرف القناة بعد الأمر (تأكد من رفع البوت كأدمن فيها)، مثال:\n/add_channel @MyChannel")
        return
    
    channel_username = context.args[0]
    bot_data["channels"][str(user_id)] = channel_username
    save_data()
    await update.message.reply_text(f"✅ تم ربط القناة {channel_username} بحسابك بنجاح. أي ملف ترسله الآن سيُنشر هناك.")

# دالة استلام الملفات من الإدمنية ونشرها
async def handle_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in bot_data["admins"]:
        return

    # التحقق مما إذا كان الأدمن قد ربط قناة بحسابه
    if str(user_id) not in bot_data["channels"]:
        await update.message.reply_text("❌ لم تقم بربط أي قناة بحسابك. استخدم الأمر /add_channel أولاً.")
        return

    channel_username = bot_data["channels"][str(user_id)]
    bot_username = context.bot.username

    # إعداد الأزرار أسفل المنشور في القناة
    keyboard = [
        [InlineKeyboardButton("تفاعل للحصول على الملف 📥", url=f"https://t.me/{bot_username}?start=getfile_{user_id}")],
        [InlineKeyboardButton("للانضمام للبوت 🤖", url=f"https://t.me/{bot_username}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        # إرسال رسالة للقناة تحتوي على الأزرار
        sent_message = await context.bot.send_message(
            chat_id=channel_username,
            text="✨ تم نشر ملف جديد (MOBO TUNNEL)!\n\nاضغط على الزر بالأسفل للحصول عليه ⬇️",
            reply_markup=reply_markup
        )
        
        # حفظ الرسالة التي تحتوي على الملف في القناة (كمرجع صامت) أو إرسال الملف مباشرة للقناة بصمت
        # سنقوم بنسخ الملف المرسل من الأدمن إلى القناة وحفظ الـ message_id الخاص به
        forwarded_file = await update.message.copy(
            chat_id=channel_username,
            disable_notification=True
        )
        
        # حفظ رقم الملف (message_id) في التخزين لكي يسحبه البوت لاحقاً للمستخدم
        bot_data["latest_files"][str(user_id)] = forwarded_file.message_id
        save_data()
        
        await update.message.reply_text("✅ تم نشر الملف في قناتك بنجاح مع أزرار التفاعل!")

    except Exception as e:
        await update.message.reply_text(f"❌ حدث خطأ أثناء النشر. تأكد أن البوت مرفوع كـ (مشرف/Admin) في القناة.\nالخطأ: {e}")

def main():
    app = Application.builder().token(TOKEN).build()

    # الأوامر الأساسية
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add_admin", add_admin))
    app.add_handler(CommandHandler("add_channel", add_channel))
    
    # استقبال جميع أنواع الملفات (مستندات، صور، فيديو، صوتيات)
    app.add_handler(MessageHandler(filters.Document.ALL | filters.VIDEO | filters.AUDIO | filters.PHOTO, handle_files))

    print("🤖 MOBO TUNNEL قيد التشغيل...")
    app.run_polling()

if __name__ == '__main__':
    main()
