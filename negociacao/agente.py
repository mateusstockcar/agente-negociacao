"""Etapa 1: agente conversacional de negociação de dívidas.

    START → agente ──(pediu ferramenta?)──→ ferramentas ─┐
              ↑  └──(não: respondeu o cliente)──→ FIM    │
              └──────────────────────────────────────────┘

Novidades em relação ao agente-pesquisador:
- ToolNode e tools_condition: versões PRONTAS do LangGraph para o nó de ferramentas
  e para a decisão "o modelo pediu ferramenta?" (no Dia 5 escrevemos isso à mão).
- Checkpointer (memória da conversa): cada cliente tem um `thread_id`. O LangGraph
  salva o estado a cada passo, então o agente lembra o que foi dito nas mensagens
  anteriores — essencial num chat de WhatsApp com várias idas e vindas.
- Regras de negócio no código (politica.py) e não no prompt.
"""

import os

from langchain_core.messages import SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from negociacao.ferramentas import FERRAMENTAS

INSTRUCOES = """Você é a Lia, assistente virtual de negociação da Recupera Crédito (empresa fictícia),
atendendo pelo WhatsApp. O cliente já está identificado pelo número de telefone.

Como agir:
- Seja cordial, empático e objetivo. Mensagens curtas, como no WhatsApp.
- Para saber as dívidas do cliente, use consultar_dividas.
- NUNCA calcule valores de cabeça nem informe valores que não vieram de uma ferramenta.
  Para qualquer proposta, use simular_acordo.
- Nunca ofereça desconto ou parcelas acima do permitido. Se o cliente pedir mais,
  explique com gentileza que esse é o limite e ofereça a melhor opção possível.
- Antes de fechar_acordo, mostre o resumo (valor total, parcelas, valor da parcela)
  e peça confirmação explícita do cliente.
- Você só trata das dívidas deste cliente. Não informe dados de outras pessoas e
  não fale de assuntos fora da negociação.
- Nunca peça senha, dados de cartão ou de conta bancária."""


def _criar_llm(modelo: str):
    # thinking_level="low": os modelos Gemini 3+ "pensam" antes de responder, o que
    # melhora tarefas difíceis mas aumenta MUITO a latência. Num chat de negociação,
    # as regras difíceis já estão no código — o modelo só precisa conversar e chamar ferramentas.
    return ChatGoogleGenerativeAI(model=modelo, temperature=0, max_retries=1, timeout=30,
                                  thinking_level=os.getenv("GEMINI_THINKING", "low"))


def _llm_com_ferramentas():
    llm = _criar_llm(os.getenv("GEMINI_MODEL", "gemini-3.8-flash")).bind_tools(FERRAMENTAS)
    reserva = os.getenv("GEMINI_FALLBACK_MODEL")
    if reserva:
        llm = llm.with_fallbacks([_criar_llm(reserva).bind_tools(FERRAMENTAS)])
    return llm


def construir_grafo():
    llm = _llm_com_ferramentas()

    def agente(estado: MessagesState):
        # o prompt de sistema entra em toda chamada, mas não é salvo no histórico
        resposta = llm.invoke([SystemMessage(INSTRUCOES)] + estado["messages"])
        return {"messages": [resposta]}

    g = StateGraph(MessagesState)
    g.add_node("agente", agente)
    g.add_node("ferramentas", ToolNode(FERRAMENTAS))
    g.add_edge(START, "agente")
    g.add_conditional_edges("agente", tools_condition, {"tools": "ferramentas", "__end__": "__end__"})
    g.add_edge("ferramentas", "agente")
    return g.compile(checkpointer=MemorySaver())
