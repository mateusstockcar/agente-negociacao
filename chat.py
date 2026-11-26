"""Chat no terminal simulando o WhatsApp.

    uv run chat.py                    # cliente Ana (2 dívidas)
    uv run chat.py --cpf 22222222222  # cliente Bruno (1 dívida antiga, desconto maior)
    uv run chat.py --cpf 33333333333  # cliente Carla (sem dívidas)
    uv run chat.py --grafo            # desenho do grafo (cole em mermaid.live)
"""

import argparse
import json
import os
import time
import uuid

from dotenv import load_dotenv

load_dotenv(override=True)

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage  # noqa: E402
from langgraph.types import Command  # noqa: E402

from negociacao.agente import construir_grafo  # noqa: E402
from negociacao.dados import CLIENTES  # noqa: E402


def texto(msg) -> str:
    c = msg.content
    if isinstance(c, str):
        return c
    return "".join(b.get("text", "") if isinstance(b, dict) else str(b) for b in c)


def main() -> None:
    args = argparse.ArgumentParser()
    args.add_argument("--cpf", default="11111111111")
    args.add_argument("--grafo", action="store_true")
    a = args.parse_args()

    grafo = construir_grafo()
    if a.grafo:
        print(grafo.get_graph().draw_mermaid())
        return

    callbacks = []
    if os.getenv("LANGFUSE_PUBLIC_KEY"):
        from langfuse.langchain import CallbackHandler
        callbacks.append(CallbackHandler())

    config = {"configurable": {"cpf": a.cpf, "thread_id": str(uuid.uuid4())},
              "callbacks": callbacks, "recursion_limit": 20}
    nome = CLIENTES.get(a.cpf, {}).get("nome", "cliente desconhecido")
    print(f"📱 Simulando WhatsApp de {nome} (CPF {a.cpf}). Digite 'sair' para encerrar.\n")

    while True:
        entrada = input("Você: ").strip()
        if entrada.lower() in {"sair", "exit", "quit"}:
            break
        if not entrada:
            continue
        antes = len(grafo.get_state(config).values.get("messages", []))
        inicio = time.perf_counter()
        resultado = grafo.invoke({"messages": [HumanMessage(entrada)]}, config=config)

        # o grafo pausou pedindo confirmação? quem pergunta é o SISTEMA, não a IA
        while resultado.get("__interrupt__"):
            pedido = resultado["__interrupt__"][0].value
            print(f"\n   🔒 CONFIRMAÇÃO DO SISTEMA: {pedido['resumo']}")
            pausa = time.perf_counter()
            confirmacao = input("   Confirma o acordo? (sim/não): ").strip()
            inicio += time.perf_counter() - pausa  # não conta o tempo que você levou para digitar
            resultado = grafo.invoke(Command(resume=confirmacao), config=config)
        segundos = time.perf_counter() - inicio

        novas = resultado["messages"][antes + 1:]
        for m in novas:  # mostra os bastidores: quais ferramentas o agente usou
            if isinstance(m, AIMessage) and m.tool_calls:
                for t in m.tool_calls:
                    print(f"   🔧 {t['name']}({json.dumps(t['args'], ensure_ascii=False)})")
            elif isinstance(m, ToolMessage):
                print(f"   ↳ {texto(m)[:300]}")
        chamadas = sum(1 for m in novas if isinstance(m, AIMessage))
        print(f"\nLia: {texto(resultado['messages'][-1])}\n")
        print(f"   ⏱️  {segundos:.1f}s | {chamadas} chamada(s) ao modelo\n")


if __name__ == "__main__":
    main()
