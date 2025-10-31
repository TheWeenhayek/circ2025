import os
import requests
from dotenv import load_dotenv
from typing_extensions import TypedDict, Literal, Annotated
from pydantic import BaseModel, Field

from langchain.chat_models import init_chat_model
from langgraph.types import Command
from langgraph.graph import StateGraph, add_messages, START, END

# === Configuración básica ===
load_dotenv()
llm = init_chat_model("openai:gpt-4o-mini")

# === Estado del agente ===
class State(TypedDict):
    user_input: dict
    messages: Annotated[list, add_messages]

# === Modelo de salida estructurada del router ===
class Router(BaseModel):
    reasoning: str = Field(description="Explicación del razonamiento detrás de la clasificación.")
    classification: Literal["btc_price", "about", "ignore"] = Field(
        description="Tipo de consulta: precio BTC, descripción del bot o ignorar."
    )

llm_router = llm.with_structured_output(Router)

# === TRIAGE NODE ===
def triage_router(state: State, config, store=None) -> Command[
    Literal["handle_btc_price", "handle_about", "handle_ignore"]
]:
    """Clasifica el mensaje del usuario en una de tres categorías."""
    message = state["user_input"]["message"]

    # Prompt para el modelo (puede ser más elaborado)
    system_prompt = (
        "Eres un asistente que clasifica mensajes de Telegram.\n"
        "- Si el usuario pregunta por el precio del Bitcoin o BTC/USDT → 'btc_price'\n"
        "- Si pregunta qué haces o quién eres → 'about'\n"
        "- De lo contrario → 'ignore'"
    )
    result = llm_router.invoke([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": message},
    ])

    print(f"🧠 Reasoning: {result.reasoning}")
    print(f"📦 Clasificado como: {result.classification}")

    return Command(
        goto=f"handle_{result.classification}",
        update={"messages": [{"role": "user", "content": message}]},
    )

# === HANDLERS ===
def handle_btc_price(state: State, config):
    """Consulta el precio actual de BTC/USDT usando la API pública de Binance."""
    try:
        resp = requests.get("https://api.coinpaprika.com/v1/tickers/btc-bitcoin", timeout=10)
        resp.raise_for_status()
        data = resp.json()
        price = data.get("quotes", {}).get("USD", {}).get("price")
        if price:
            content = f"💰 El precio actual de *Bitcoin (BTC/USDT)* es **{price} USDT**."
        else:
            content = "⚠️ No pude obtener el precio en este momento."
    except Exception as e:
        content = f"❌ Error al consultar Binance: {e}"
    return {"messages": [{"role": "assistant", "content": content}]}

def handle_about(state: State, config):
    """Describe brevemente qué hace el bot."""
    content = (
        "👋 Soy un agente construido con **LangGraph** y **LangChain**.\n"
        "Puedo consultar datos reales, como el precio del Bitcoin, y responderte en lenguaje natural.\n"
        "Pregúntame: '¿Cuál es el precio del BTC/USDT?'"
    )
    return {"messages": [{"role": "assistant", "content": content}]}

def handle_ignore(state: State, config):
    """Responde cuando el mensaje no es relevante."""
    content = (
        "🤖 No entiendo tu solicitud. Puedes preguntarme cosas como:\n"
        "• Precio del BTC/USDT\n"
        "• Qué hace este bot"
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
