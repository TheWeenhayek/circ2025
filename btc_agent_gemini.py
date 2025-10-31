import os
import requests
import google.generativeai as genai
from dotenv import load_dotenv
from typing_extensions import TypedDict, Literal, Annotated
from pydantic import BaseModel, Field

from langgraph.types import Command
from langgraph.graph import StateGraph, add_messages, START, END

# === Configuración ===
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

# === Wrapper de Gemini ===
def call_gemini(prompt: str) -> str:
    """Envía un prompt al modelo Gemini y devuelve el texto de salida."""
    model = genai.GenerativeModel("gemini-1.5-flash")  # puedes usar "gemini-pro" también
    response = model.generate_content(prompt)
    return response.text.strip()

# === Estado del agente ===
class State(TypedDict):
    user_input: dict
    messages: Annotated[list, add_messages]

# === Router estructurado ===
class Router(BaseModel):
    reasoning: str = Field(description="Razonamiento detrás de la clasificación.")
    classification: Literal["btc_price", "about", "ignore"]

# === TRIAGE NODE ===
def triage_router(state: State, config, store=None) -> Command[
    Literal["handle_btc_price", "handle_about", "handle_ignore"]
]:
    message = state["user_input"]["message"]

    system_prompt = (
        "Eres un asistente que clasifica mensajes de Telegram.\n"
        "Categorías posibles:\n"
        "- 'btc_price' → si el usuario pregunta por el precio del Bitcoin o BTC/USDT\n"
        "- 'about' → si pregunta qué haces o quién eres\n"
        "- 'ignore' → para cualquier otro mensaje\n\n"
        f"Mensaje: {message}"
    )

    result_text = call_gemini(system_prompt)

    # Heurística simple para extraer clasificación
    reasoning = result_text
    classification = "ignore"
    if "btc" in result_text.lower():
        classification = "btc_price"
    elif "about" in result_text.lower() or "quién eres" in message.lower():
        classification = "about"

    print(f"🧠 Reasoning: {reasoning}")
    print(f"📦 Clasificado como: {classification}")

    return Command(
        goto=f"handle_{classification}",
        update={"messages": [{"role": "user", "content": message}]},
    )

# === HANDLERS ===
def handle_btc_price(state: State, config):
    """Consulta el precio actual de BTC/USDT en Binance."""
    try:
        resp = requests.get("https://api.coinpaprika.com/v1/tickers/btc-bitcoin", timeout=10)
        resp.raise_for_status()
        data = resp.json()
        price = data.get("quotes", {}).get("USD", {}).get("price")
        content = f"💰 El precio actual de Bitcoin (BTC/USDT) es **{price} USDT**." if price else "⚠️ No se pudo obtener el precio."
    except Exception as e:
        content = f"❌ Error al consultar Binance: {e}"
    return {"messages": [{"role": "assistant", "content": content}]}

def handle_about(state: State, config):
    content = (
        "👋 Soy un agente construido con *LangGraph* y *Gemini (Google AI)*.\n"
        "Puedo consultar datos reales, como el precio del Bitcoin, y responderte en lenguaje natural."
    )
    return {"messages": [{"role": "assistant", "content": content}]}

def handle_ignore(state: State, config):
    content = (
        "🤖 No entiendo tu solicitud. Prueba con:\n"
        "• '¿Cuál es el precio del BTC/USDT?'\n"
        "• '¿Qué hace este bot?'"
    )
    return {"messages": [{"role": "assistant", "content": content}]}

# === GRAPH ===
agent_graph = StateGraph(State)
agent_graph.add_node("triage_router", triage_router)
agent_graph.add_node("handle_btc_price", handle_btc_price)
agent_graph.add_node("handle_about", handle_about)
agent_graph.add_node("handle_ignore", handle_ignore)

agent_graph.add_edge(START, "triage_router")
agent_graph.add_edge("handle_btc_price", END)
agent_graph.add_edge("handle_about", END)
agent_graph.add_edge("handle_ignore", END)

agent = agent_graph.compile()
