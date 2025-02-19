import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, CallbackContext, ConversationHandler
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Valid Serial Codes
VALID_SERIAL_CODES = [
    "sixsixsix23$$&@",
    "zuzushuga@gmail,com",
    "sweetsixteen0616@gmail.com",
    "suniemimaxhimum@gmail.com",
    "winwininnovation@gmail.com"
]

# SMTP Configuration from .env
SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

# Conversation States
START, VALIDATE_SERIAL, FROM_NAME, FROM_EMAIL, REPLY_TO, SUBJECT, BODY_HTML, SEND_TO = range(8)

# User Session Data
user_sessions = {}

async def start(update: Update, context: CallbackContext) -> int:
    await update.message.reply_text("Welcome to the Email Marketing Bot! Please enter your serial code to proceed.")
    return VALIDATE_SERIAL

async def validate_serial(update: Update, context: CallbackContext) -> int:
    user_input = update.message.text
    if user_input in VALID_SERIAL_CODES:
        await update.message.reply_text("Serial code validated! Let's set up your email. What is the 'From Name'?")
        return FROM_NAME
    else:
        await update.message.reply_text("Invalid serial code. Please try again.")
        return VALIDATE_SERIAL

async def from_name(update: Update, context: CallbackContext) -> int:
    user_sessions[update.message.chat_id] = {"from_name": update.message.text}
    await update.message.reply_text("Got it! What is the 'From Email'?")
    return FROM_EMAIL

async def from_email(update: Update, context: CallbackContext) -> int:
    user_input = update.message.text
    if "@" in user_input and "." in user_input:  # Basic email validation
        user_sessions[update.message.chat_id]["from_email"] = user_input
        await update.message.reply_text("Great! What is the 'Reply To' email?")
        return REPLY_TO
    else:
        await update.message.reply_text("Invalid email format. Please try again.")
        return FROM_EMAIL

async def reply_to(update: Update, context: CallbackContext) -> int:
    user_input = update.message.text
    if "@" in user_input and "." in user_input:  # Basic email validation
        user_sessions[update.message.chat_id]["reply_to"] = user_input
        await update.message.reply_text("Awesome! What is the email subject?")
        return SUBJECT
    else:
        await update.message.reply_text("Invalid email format. Please try again.")
        return REPLY_TO

async def subject(update: Update, context: CallbackContext) -> int:
    user_sessions[update.message.chat_id]["subject"] = update.message.text
    await update.message.reply_text("Got it! Please provide the HTML body of the email.")
    return BODY_HTML

async def body_html(update: Update, context: CallbackContext) -> int:
    user_sessions[update.message.chat_id]["body_html"] = update.message.text
    await update.message.reply_text("Almost done! Please provide the recipient emails (comma-separated, 1-1000 emails).")
    return SEND_TO

async def send_to(update: Update, context: CallbackContext) -> int:
    user_input = update.message.text.strip()
    if not user_input:
        await update.message.reply_text("Recipient emails cannot be empty. Please provide the recipient emails (comma-separated, 1-1000 emails).")
        return SEND_TO

    emails = [email.strip() for email in user_input.split(",")]
    if len(emails) < 1 or len(emails) > 1000:
        await update.message.reply_text("Please provide between 1 and 1000 recipient emails.")
        return SEND_TO

    user_sessions[update.message.chat_id]["send_to"] = emails

    # Send Email
    try:
        session = user_sessions[update.message.chat_id]
        for recipient in session["send_to"]:
            msg = MIMEMultipart()
            msg["From"] = f"{session['from_name']} <{session['from_email']}>"
            msg["Reply-To"] = session["reply_to"]
            msg["To"] = recipient
            msg["Subject"] = session["subject"]
            msg.attach(MIMEText(session["body_html"], "html"))

            with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
                server.starttls()
                server.login(SMTP_USERNAME, SMTP_PASSWORD)
                server.sendmail(session["from_email"], recipient, msg.as_string())

        await update.message.reply_text(f"Email sent successfully to {len(emails)} recipients!")
    except Exception as e:
        logger.error(f"Error sending email: {e}")
        await update.message.reply_text(f"Error sending email: {e}")

    # Reset Session
    user_sessions.pop(update.message.chat_id, None)
    return ConversationHandler.END

async def cancel(update: Update, context: CallbackContext) -> int:
    await update.message.reply_text("Operation canceled.")
    user_sessions.pop(update.message.chat_id, None)
    return ConversationHandler.END

def main() -> None:
    # Load Telegram Bot Token from .env
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN not found in .env file.")

    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            VALIDATE_SERIAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, validate_serial)],
            FROM_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, from_name)],
            FROM_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, from_email)],
            REPLY_TO: [MessageHandler(filters.TEXT & ~filters.COMMAND, reply_to)],
            SUBJECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, subject)],
            BODY_HTML: [MessageHandler(filters.TEXT & ~filters.COMMAND, body_html)],
            SEND_TO: [MessageHandler(filters.TEXT & ~filters.COMMAND, send_to)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(conv_handler)
    application.run_polling()

if __name__ == "__main__":
    main()
