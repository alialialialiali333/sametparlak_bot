import os
import logging
import asyncio
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Log ayarları
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Kullanıcı bazlı düz metin hafızası (Sürüm güncellemelerinden etkilenmez)
bot_memories = {}

# --- RENDER PORTU İÇİN WEB SUNUCUSU (KİLİTLENMEYEN SADE YAPI) ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Bot Aktif")

    def log_message(self, format, *args):
        return  # Log ekranını sahte web istekleriyle doldurmaması için logları kapatıyoruz

def run_health_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    server.serve_forever()
# ----------------------------------------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bot ilk başlatıldığında hafıza yapısını temiz kurar"""
    user_id = update.effective_user.id
    
    # Google API'sinin ham JSON formatına tam uyumlu düz metin geçmişi
    bot_memories[user_id] = [
        {"role": "user", "parts": [{"text": "Sen arkadaş canlısı, yardımsever ve konuşulanları asla unutmayan akıllı bir Telegram botusun. Türkçe konuşacaksın. Cevapların çok uzun olmasın."}]},
        {"role": "model", "parts": [{"text": "Harika! Hazırım. Konuştuklarımızı aklımda tutacağım, bana istediğini sorabilirsin."}]}
    ]
    await update.message.reply_text("Merhaba! Ben hafızası olan akıllı bir yapay zekayım. Konuştuklarımızı unutmam. Bana istediğini yazabilirsin!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gelen mesajı ham HTTP isteğiyle Gemini'ye sorar ve hafızayı korur"""
    user_id = update.effective_user.id
    user_message = update.message.text

    if user_id not in bot_memories:
        bot_memories[user_id] = []

    # Kullanıcı mesajını hafızaya ekle
    bot_memories[user_id].append({"role": "user", "parts": [{"text": user_message}]})

    try:
        # Google SDK sürüm hatalarını aşmak için doğrudan resmi API URL'sine istek atıyoruz
        url = f"https://googleapis.com{GEMINI_API_KEY}"
        payload = {"contents": bot_memories[user_id]}
        
        # İsteği gönderiyoruz
        response = requests.post(url, json=payload, timeout=15)
        response_data = response.json()
        
        # Yanıtı ayıklıyoruz
        bot_response = response_data['candidates'][0]['content']['parts'][0]['text']

        # Botun cevabını hafızaya ekle
        bot_memories[user_id].append({"role": "model", "parts": [{"text": bot_response}]})

        # Cevabı Telegram'a gönder
        await update.message.reply_text(bot_response)

    except Exception as e:
        logging.error(f"Sistem Hatası: {e}")
        await update.message.reply_text("Ufak bir bağlantı sorunu yaşadım, lütfen tekrar dener misin?")

def main():
    # Port kilitlenmesini önlemek için web sunucusunu arka planda başlatıyoruz
    threading.Thread(target=run_health_server, daemon=True).start()

    # Telegram bot motoru
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logging.info("Bot ana motoru başarıyla çalışıyor...")
    app.run_polling()

if __name__ == '__main__':
    main()
