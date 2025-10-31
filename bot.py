import os
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# --- Triage handler: decide si ignorar o procesar ---
async def triage_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text.strip().lower()

    if "btc" in user_text and ("usdt" in user_text or "usd" in user_text):
        # intención: cotización BTC/USDT
        await handle_btc_price(update, context)
    else:
        await update.message.reply_text(
            "Lo siento, no entendí tu solicitud. Puedes preguntar: “¿Cuál es el precio del BTC/USDT?”"
        )

# --- Response handler: realiza la consulta y responde ---
async def handle_btc_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        resp = requests.get("https://api.coinpaprika.com/v1/tickers/btc-bitcoin", timeout=10)
        resp.raise_for_status()
        data = resp.json()
        price = data.get("quotes", {}).get("USD", {}).get("price")
        if price:
            text = f"El precio actual de BTC/USDT es: *{price}* USDT"
            await update.message.reply_markdown(text)
        else:
            await update.message.reply_text("No pude obtener el precio en este momento. Por favor intenta más tarde.")
    except Exception:
        await update.message.reply_text("Ocurrió un error al consultar la API. Por favor intenta más tarde.")

# --- Comando /start ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    greeting = "¡Hola! 😊 Soy tu bot de cotización."
    instructions = "Puedes preguntarme: “¿Cuál es el precio del BTC/USDT?” y te lo responderé."
    await update.message.reply_markdown(f"{greeting}\n\n{instructions}")

# --- Main ---
if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, triage_handler))

    print("🤖 Bot de cotización de BTC está corriendo...")
    app.run_polling()
