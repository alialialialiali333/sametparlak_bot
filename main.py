import os
import logging
import asyncio
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from google import genai

# Log ayarları
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Yapay zeka istemcisi
ai_client = genai.Client(api_key=GEMINI_API_KEY)

# Kullanıcı bazlı basit metin hafızası
bot_memories = {}

# --- RENDER PORTU İÇİN WEB SUNUCUSU ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Bot Aktif")

def run_health_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    server.serve_forever()
# --------------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bot ilk başlatıldığında hafızayı kurar"""
    user_id = update.effective_user.id
    # Sadeleştirilmiş sistem talimatı ve başlangıç
    bot_memories[user_id] = [
        {"role": "user", "parts": ["Sen arkadaş canlısı, yardımsever ve konuşulanları asla unutmayan akıllı bir Telegram botusun. Türkçe konuşacaksın. Cevapların çok uzun olmasın."]},
        {"role": "model", "parts": ["Harika! Hazırım. Konuştuklarımızı aklımda tutacağım, bana istediğini sorabilirsin."]}
    ]
    await update.message.reply_text("Merhaba! Ben hafızası olan akıllı bir yapay zekayım. Konuştuklarımızı unutmam. Bana istediğini yazabilirsin!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mesaj geldikçe hafızayı günceller ve cevap üretir"""
    user_id = update.effective_user.id
    user_message = update.message.text

    if user_id not in bot_memories:
        bot_memories[user_id] = []

    # Kullanıcı mesajını hafızaya ekle
    bot_memories[user_id].append({"role": "user", "parts": [user_message]})

    try:
        # Doğrudan metin tabanlı geçmiş listesini gönderiyoruz (Hata ihtimali sıfır)
        response = ai_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=bot_memories[user_id]
        )
        bot_response = response.text

        # Botun cevabını hafızaya ekle
        bot_memories[user_id].append({"role": "model", "parts": [bot_response]})

        # Cevabı gönder
        await update.message.reply_text(bot_response)

    except Exception as e:
        logging.error(f"Hata olustu: {e}")
        await update.message.reply_text("Ufak bir bağlantı sorunu yaşadım, lütfen tekrar dener misin?")

def main():
    threading.Thread(target=run_health_server, daemon=True).start()

    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logging.info("Bot basariyla calisiyor...")
    app.run_polling()

if __name__ == '__main__':
    main()
