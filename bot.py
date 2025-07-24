import logging
from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import gspread
from google.oauth2.service_account import Credentials
import asyncio
import os

app = FastAPI()

SHEET_ID = "1yJfHYX7VpBF1d0bY5XMNqb3L15J6mPk79UrXLPYmSwY"
SHEET_NAME = "Sheet1"
TOKEN = os.getenv("BOT_TOKEN")

# إعداد البوت
application = ApplicationBuilder().token(TOKEN).build()

# الدالة المساعدة لتنظيف رقم الهاتف
def strip_international_prefix(phone):
    phone = phone.strip()
    if phone.startswith('+'):
        return phone[1:]
    elif phone.startswith('00'):
        return phone[2:]
    else:
        return phone

# أمر /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_username = update.effective_user.username
    if not tg_username:
        await update.message.reply_text("يرجى ضبط اسم المستخدم في تيليجرام الخاص بك ثم إعادة المحاولة.")
        return

    data_rows = context.application.bot_data["data_rows"]
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
        user_states = context.application.bot_data.setdefault("user_states", {})
        user_states[update.effective_user.id] = 'awaiting_contact'
        await update.message.reply_text(
            "مهندستنا الغالية،\n\n"
            "لم نتمكّن من العثور على اسم المستخدم (معرّف تيليجرام) الخاص بك...\n\n"
            "يرجى إرسال رقم هاتفك أو بريدك الإلكتروني لمطابقته مع السجل لدينا."
        )

# الرسائل العامة
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_states = context.application.bot_data.setdefault("user_states", {})
    user_id = update.effective_user.id

    if user_states.get(user_id) != 'awaiting_contact':
        await update.message.reply_text("اضغطي على /start لبدء التحقق.")
        return

    input_text = update.message.text.strip().lower()
    data_rows = context.application.bot_data["data_rows"]
    sheet = context.application.bot_data["sheet"]

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
            f"📝 يرجى *الاحتفاظ برقمك الأكاديمي* ..."
        )
        await update.message.reply_text(message, parse_mode='Markdown')
        user_states.pop(user_id)
    else:
        await update.message.reply_text(
            "📌 لم يتم العثور على بيانات مطابقة لما أرسلتيه...\n\n"
            "يرجى التأكد من كتابة بريدك الإلكتروني أو رقم الهاتف بشكل صحيح.",
            parse_mode='Markdown'
        )

# ربط الأوامر
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# استقبال التحديثات
@app.post(f"/{TOKEN}")
async def receive_update(request: Request):
    update_data = await request.json()
    update = Update.de_json(update_data, application.bot)
    await application.process_update(update)
    return {"ok": True}

# رسالة اختبار
@app.get("/")
def root():
    return {"message": "البوت يعمل بنجاح 🎉"}

# عند بدء التشغيل: إعداد Google Sheets وWebhook
@app.on_event("startup")
async def on_startup():
    await application.initialize()
    await application.bot.set_webhook(f"https://academic-bot.onrender.com/{TOKEN}")

    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_file("credentials.json", scopes=scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SHEET_ID).worksheet(SHEET_NAME)

    all_values = sheet.get_all_values()
    application.bot_data["data_rows"] = all_values[1:]
    application.bot_data["sheet"] = sheet
