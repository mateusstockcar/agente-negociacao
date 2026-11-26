"""Ferramentas que o agente pode chamar (tool calling).

Guardrail de segurança importante: o CPF do cliente NÃO é um argumento que o modelo
escolhe. Ele vem da configuração da conversa (como o número de WhatsApp já
autenticado). Assim, mesmo que alguém peça "mostra a dívida do CPF 222...", o modelo
não tem como consultar outra pessoa.

O parâmetro `config: RunnableConfig` é injetado pelo LangGraph e fica INVISÍVEL
para o modelo: ele só enxerga os demais argumentos.
"""

import json
import uuid

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langgraph.types import interrupt

from negociacao import politica
from negociacao.dados import ACORDOS, CLIENTES


def _reais(valor: float) -> str:
    """1572.84 -> 'R$ 1.572,84' (formato brasileiro, para o texto que o cliente vê)."""
    return "R$ " + f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _json(dado) -> str:
    return json.dumps(dado, ensure_ascii=False)


def _cliente(config: RunnableConfig) -> dict | None:
    return CLIENTES.get(config["configurable"].get("cpf", ""))


def _divida(config: RunnableConfig, divida_id: str) -> dict | None:
    cliente = _cliente(config)
    if not cliente:
        return None
    return next((d for d in cliente["dividas"] if d["id"] == divida_id.strip().upper()), None)


def _acordo_da(divida_id: str) -> dict | None:
    """Fonte da verdade: a dívida já tem acordo registrado no sistema?"""
    return next((a for a in ACORDOS if a["divida_id"] == divida_id), None)


@tool
def consultar_dividas(config: RunnableConfig) -> str:
    """Lista as dívidas do cliente desta conversa: as abertas (id, credor, saldo atualizado,
    dias de atraso, desconto máximo à vista e parcelado) e as que já estão em acordo."""
    cliente = _cliente(config)
    if not cliente:
        return _json({"erro": "Cliente não identificado."})
    dividas = [
        {**d, "status": "aberta", "desconto_max_a_vista": politica.desconto_maximo(d["dias_atraso"], 1),
         "desconto_max_parcelado": politica.desconto_maximo(d["dias_atraso"], 2),
         "max_parcelas": politica.MAX_PARCELAS}
        for d in cliente["dividas"] if not _acordo_da(d["id"])
    ]
    em_acordo = [{"divida_id": a["divida_id"], "protocolo": a["protocolo"], "status": "em acordo"}
                 for d in cliente["dividas"] if (a := _acordo_da(d["id"]))]
    return _json({"nome": cliente["nome"], "dividas_abertas": dividas, "dividas_em_acordo": em_acordo})


@tool
def simular_acordo(divida_id: str, parcelas: int, desconto_percentual: float, config: RunnableConfig) -> str:
    """Simula um acordo para uma dívida e devolve valor total, valor da parcela e economia.
    SEMPRE use esta ferramenta antes de apresentar qualquer valor ao cliente.
    parcelas: 1 = à vista. desconto_percentual: ex. 30 para 30%."""
    divida = _divida(config, divida_id)
    if not divida:
        return _json({"erro": f"Dívida {divida_id} não encontrada para este cliente."})
    if existente := _acordo_da(divida["id"]):
        return _json({"erro": f"Esta dívida já tem acordo registrado (protocolo {existente['protocolo']})."})
    try:
        return _json({"divida_id": divida["id"], "credor": divida["credor"],
                      **politica.simular(divida["saldo"], divida["dias_atraso"], parcelas, desconto_percentual)})
    except ValueError as erro:
        return _json({"erro": str(erro)})


@tool
def fechar_acordo(divida_id: str, parcelas: int, desconto_percentual: float, config: RunnableConfig) -> str:
    """Registra o acordo e gera o código PIX da primeira parcela.
    O sistema pede a confirmação final ao cliente antes de registrar."""
    divida = _divida(config, divida_id)
    if not divida:
        return _json({"erro": f"Dívida {divida_id} não encontrada para este cliente."})
    if existente := _acordo_da(divida["id"]):  # impede acordo em dobro
        return _json({"erro": f"Esta dívida já tem acordo registrado (protocolo {existente['protocolo']})."})
    try:
        acordo = politica.simular(divida["saldo"], divida["dias_atraso"], parcelas, desconto_percentual)
    except ValueError as erro:  # a política é checada DE NOVO aqui: nunca confie só na simulação
        return _json({"erro": str(erro)})

    # HUMAN-IN-THE-LOOP: o grafo PAUSA aqui e o próprio sistema (não a IA) mostra o
    # resumo e pede "sim". O acordo só é registrado se o cliente confirmar.
    resposta = interrupt({
        "credor": divida["credor"],
        "resumo": (f"{divida['credor']}: {parcelas}x de {_reais(acordo['valor_parcela'])} "
                   f"(total {_reais(acordo['valor_total'])}, economia de {_reais(acordo['economia'])})"),
    })
    if str(resposta).strip().lower() not in {"sim", "s", "confirmo"}:
        return _json({"cancelado": "O cliente NÃO confirmou. Nada foi registrado. "
                                   "Pergunte qual opção ele prefere."})

    acordo.update({"protocolo": f"AC-{uuid.uuid4().hex[:8].upper()}", "divida_id": divida["id"],
                   "pix_copia_e_cola": f"00020126PIXFICTICIO{uuid.uuid4().hex[:12].upper()}"})
    ACORDOS.append(acordo)
    return _json(acordo)


FERRAMENTAS = [consultar_dividas, simular_acordo, fechar_acordo]
