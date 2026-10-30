import os
import logging
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from google import genai
from google.genai import types

# Hata loglarını takip etmek için kurulum
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Render'a eklediğiniz şifreleri sistemden çekiyoruz
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Yapay zeka istemcisini başlatıyoruz
ai_client = genai.Client(api_key=GEMINI_API_KEY)

# Konuşmaları her kullanıcı için ayrı ayrı akılda tutacak hafıza sözlüğü
bot_memories = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/start komutu verildiğinde botun vereceği ilk hafıza talimatı"""
    user_id = update.effective_user.id
    # Her kullanıcı için temiz ve yönlendirmeli bir hafıza geçmişi başlatıyoruz
    bot_memories[user_id] = [
        types.Content(role="user", parts=[types.Part.from_text("Sen arkadaş canlısı, yardımsever ve konuşulanları asla unutmayan akıllı bir Telegram botusun. Türkçe konuşacaksın. Cevapların çok uzun olmasın.")]),
        types.Content(role="model", parts=[types.Part.from_text("Harika! Hazırım. Konuştuklarımızı aklımda tutacağım, bana istediğini sorabilirsin.")])
    ]
    await update.message.reply_text("Merhaba! Ben hafızası olan akıllı bir yapay zekayım. Konuştuklarımızı unutmam. Bana istediğini yazabilirsin!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kullanıcı bota normal mesaj attığında çalışan kısım"""
    user_id = update.effective_user.id
    user_message = update.message.text

    # Eğer kullanıcı botu /start demeden başlattıysa hafıza kaydı aç
    if user_id not in bot_memories:
        bot_memories[user_id] = []

    # Kullanıcının yeni gelen mesajını hafıza geçmişine ekle
    bot_memories[user_id].append(
        types.Content(role="user", parts=[types.Part.from_text(user_message)])
    )

    try:
        # Tüm konuşma geçmişini yapay zekaya gönderip cevap istiyoruz
        response = ai_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=bot_memories[user_id]
        )
        bot_response = response.text

        # Yapay zekanın verdiği cevabı da hafızaya ekle (böylece ne dediğini de unutmaz)
        bot_memories[user_id].append(
            types.Content(role="model", parts=[types.Part.from_text(bot_response)])
        )

        # Cevabı Telegram'dan kullanıcıya gönder
        await update.message.reply_text(bot_response)

    except Exception as e:
        logging.error(f"Hata oluştu: {e}")
        await update.message.reply_text("Ufak bir bağlantı sorunu yaşadım, lütfen tekrar dener misin?")

def main():
    """Botu çalıştıran ana motor"""
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logging.info("Bot Render üzerinde başarıyla çalıştırıldı...")
    app.run_polling()

if __name__ == '__main__':
    main()
