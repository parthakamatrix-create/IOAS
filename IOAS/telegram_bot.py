import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from app import app
from models import Opportunity, User, db

load_dotenv()

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# Initialize Gemini if key exists
gemini_client = None
if GEMINI_API_KEY:
    try:
        from google import genai
        gemini_client = genai.Client(api_key=GEMINI_API_KEY)
    except ImportError:
        pass

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    welcome_msg = (
        "👋 Welcome to the IOAS Smart Bot!\n\n"
        "You can chat with me naturally! Ask things like:\n"
        "👉 'What AI hackathons are coming up?'\n"
        "👉 'Are there any Scopus conferences next month?'\n\n"
        "To update your automatic alerts, use: \n"
        "`/subscribe AI, Web3`"
    )
    await update.message.reply_text(welcome_msg, parse_mode='Markdown')

async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text.replace('/subscribe', '').strip()
    user_id = str(update.message.chat_id)
    
    if not text:
        await update.message.reply_text("Please provide your interests! Example: `/subscribe AI, Machine Learning`", parse_mode='Markdown')
        return
        
    with app.app_context():
        user = User.query.filter_by(phone_number=user_id).first()
        if user:
            user.interests = text
            reply = f"✅ Your interests have been updated to: {text}"
        else:
            first_name = update.message.from_user.first_name or "Telegram User"
            user = User(name=first_name, phone_number=user_id, interests=text, whatsapp_enabled=True)
            db.session.add(user)
            reply = f"✅ You are now subscribed for alerts with interests: {text}"
        db.session.commit()
    await update.message.reply_text(reply)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_message = update.message.text
    user_id = str(update.message.chat_id)
    first_name = update.message.from_user.first_name or "User"
    
    if not gemini_client:
        await update.message.reply_text("I'm currently running in 'Basic Mode'.")
        return

    # Trigger scraper on demand if requested
    if any(word in user_message.lower() for word in ['reload', 'refresh', 'scan', 'latest', 'new']):
        await update.message.reply_text("🔄 Give me a second, scanning the web for the absolute latest opportunities...")
        from scraper import run_scraper_pipeline
        with app.app_context():
            run_scraper_pipeline()
            
    # 1. Fetch DB Context
    with app.app_context():
        # Get active opportunities (only future deadlines)
        from datetime import datetime
        now = datetime.utcnow()
        opps = Opportunity.query.filter(Opportunity.registration_deadline >= now).limit(30).all()
        db_context = "AVAILABLE UPCOMING OPPORTUNITIES IN DATABASE:\n"
        for o in opps:
            reg = o.registration_deadline.strftime('%Y-%m-%d') if o.registration_deadline else 'N/A'
            scopus = "Yes" if o.is_scopus_indexed else "No"
            db_context += f"- Title: {o.title} | Type: {o.type} | Category: {o.category} | Reg Deadline: {reg} | Scopus: {scopus} | Link: {o.url}\n"
            
    # 2. Call Gemini with fallback models for 503 errors
    system_prompt = f"""You are the IOAS (Intelligent Opportunity Aggregation System) virtual assistant.
You are talking to a user named {first_name} on Telegram.
Be friendly, concise, and helpful (like a human assistant). Use emojis naturally.
Use the following database records to answer their query. Do not invent opportunities that aren't in this list.
If they ask for something not in the list, politely tell them it's not currently available.
If they want to sign up for automated background alerts, tell them to use the command `/subscribe <their interests>`.

{db_context}
"""
    
    models_to_try = ['gemini-3.5-flash-lite', 'gemini-3.1-flash-lite', 'gemini-3.8-flash']
    for model_name in models_to_try:
        try:
            response = gemini_client.models.generate_content(
                model=model_name,
                contents=system_prompt + f"\nUser Message: {user_message}"
            )
            await update.message.reply_text(response.text)
            return
        except Exception as e:
            print(f"Failed with {model_name}: {e}")
            
    await update.message.reply_text("Oops! My AI brain is currently experiencing high demand. Please try asking again in a few seconds!")

def main() -> None:
    if not TOKEN:
        print("TELEGRAM_BOT_TOKEN is not set in .env")
        return

    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("subscribe", subscribe))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Telegram Smart AI Bot is running...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
