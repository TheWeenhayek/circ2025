import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

from btc_agent import agent  # importar el grafo

load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    greeting = "¡Hola! Soy tu bot de criptomonedas 🤖"
    info = (
        "Puedo decirte el precio actual de *Bitcoin (BTC/USDT)* o contarte cómo fui creado.\n"
        "Prueba escribiendo: '¿Cuál es el precio del Bitcoin?'"
    )
    await update.message.reply_markdown(f"{greeting}\n\n{info}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_text = update.message.text.strip()

    # Estado inicial
    state_input = {"user_input": {"message": user_text}}
    config = {"configurable": {"langgraph_user_id": f"telegram-{user_id}"}}

    # Ejecuta el agente LangGraph
    result = agent.invoke(state_input, config=config)
    response = "⚠️ Sin respuesta."

    for message in result["messages"]:
        if "content" in message:
            response = message["content"]

    await update.message.reply_markdown(response)

if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🤖 Bot de LangGraph corriendo...")
    app.run_polling()
