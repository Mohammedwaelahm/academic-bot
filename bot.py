import logging
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import gspread
from google.oauth2.service_account import Credentials

app = Flask(__name__)

SHEET_ID = "1yJfHYX7VpBF1d0bY5XMNqb3L15J6mPk79UrXLPYmSwY"
SHEET_NAME = "Sheet1"
TOKEN = "8198733355:AAF4vAs0PPKlS3SqmSHee_efrlYT7Wt2yRk"

# إعداد Google Sheets
scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_file("credentials.json", scopes=scope)
client = gspread.authorize(creds)
sheet = client.open_by_key(SHEET_ID).worksheet(SHEET_NAME)

all_values = sheet.get_all_values()
headers = all_values[0]
data_rows = all_values[1:]

user_states = {}

def strip_international_prefix(phone):
    phone = phone.strip()
    if phone.startswith('+'):
        return phone[1:]
    elif phone.startswith('00'):
        return phone[2:]
    else:
        return phone

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_username = update.effective_user.username
    if not tg_username:
        await update.message.reply_text("يرجى ضبط اسم المستخدم في تيليجرام الخاص بك ثم إعادة المحاولة.")
        return

    matched = next(
        (row for row in data_rows if row[3].replace('@', '').strip().lower() == tg_username.lower()),
        None
    )

    if matched:
        name = matched[0]
        academic_id = matched[4]

        message = (
            f"🌸 *حياكِ الله يا طيبة*\n\n"
            f"👩‍🔬 *مهندسة الأجيال:* `{name}`\n"
            f"🎓 *الرقم الأكاديمي:* `{academic_id}`\n\n"
            f"📝 يرجى *الاحتفاظ برقمك الأكاديمي* ونسخه مباشرة عند الحاجة بدلاً من كتابته يدويًا لضمان الدقة وتفادي الأخطاء.\n"
            f"📋 يمكنك النسخ بسهولة عبر الضغط المطوّل على الرقم.\n\n"
            f"🔁 *ملاحظة:* إذا كنتِ طالبة سابقة، تأكدي من *مطابقة الرقم الأكاديمي* لرقمك السابق.\n\n"
            f"📩 في حال وجود مشكلة بالبيانات يمكنكِ التواصل عبر: [اضغطي هنا للتواصل](https://t.me/AJYACADST_BOT)\n\n"
            f"🤍 *نتمنى لكِ رحلة موفقة ومباركة*"
        )
        await update.message.reply_text(message, parse_mode='Markdown')
    else:
        user_states[update.effective_user.id] = 'awaiting_contact'
        await update.message.reply_text(
            "مهندستنا الغالية،\n\n"
            "لم نتمكّن من العثور على اسم المستخدم (معرّف تيليجرام) الخاص بك.\n\n"
            "للمساعدة في العثور على رقمك الأكاديمي، يُرجى إرسال أحد الخيارين التاليين:\n"
            "1. البريد الإلكتروني المستخدم في التسجيل.\n"
            "2. رقم الهاتف المرتبط بواتساب، بصيغة مثل: 962780144811.\n"
            "📌 لا تكتبي + أو 00 في بداية الرقم.\n"
            "مع أطيب الأمنيات بالتوفيق 🌷"
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_states.get(user_id) != 'awaiting_contact':
        await update.message.reply_text("اضغطي على /start لبدء التحقق.")
        return

    input_text = update.message.text.strip().lower()

    matched = None
    for row in data_rows:
        email = row[1].strip().lower()
        phone = strip_international_prefix(row[2].strip()).lower()
        if input_text == email or input_text == phone:
            matched = row
            break

    if matched:
        name = matched[0]
        academic_id = matched[4]
        row_index = data_rows.index(matched) + 2

        tg_username = update.effective_user.username
        if tg_username:
            sheet.update_cell(row_index, 6, f"@{tg_username}")

        message = (
            f"🌸 *حياكِ الله يا طيبة*\n\n"
            f"👩‍🔬 *مهندسة الأجيال:* `{name}`\n"
            f"🎓 *الرقم الأكاديمي:* `{academic_id}`\n\n"
            f"📝 يرجى *الاحتفاظ برقمك الأكاديمي*.\n"
            f"📩 لأي استفسار: [اضغطي هنا للتواصل](https://t.me/AJYACADST_BOT)\n"
        )
        await update.message.reply_text(message, parse_mode='Markdown')
        user_states.pop(user_id)
    else:
        await update.message.reply_text(
            "📌 لم يتم العثور على بيانات.\n"
            "تأكدي من كتابة الرقم أو الإيميل بشكل مطابق لما أدخلتيه في التسجيل.\n"
            "🔁 حاولي مرة أخرى أو راجعي التعليمات."
        )

# إعداد التطبيق والتيليجرام
application = ApplicationBuilder().token(TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    if request.method == "POST":
        update = Update.de_json(request.get_json(force=True), application.bot)
        application.update_queue.put(update)
        return 'OK', 200

@app.route('/')
def index():
    return "البوت يعمل بنجاح 🎉"

# ✅ هذه الدالة يتم استدعاؤها لتفعيل webhook وتشغيل Flask
async def main():
    await application.bot.set_webhook(url=f"https://academic-bot.onrender.com/{TOKEN}")
    print("✅ Webhook تم تفعيله.")
    app.run(host='0.0.0.0', port=8080)

# ✅ تشغيل البوت
if __name__ == '__main__':
    asyncio.run(main())
