"""Base FICTÍCIA de clientes e dívidas — simula a API interna de uma empresa de crédito.

Num projeto real, isto seriam chamadas HTTP para os sistemas de dívidas e pagamentos.
Aqui fica em memória para podermos focar no agente. Nenhum dado é real.
"""

CLIENTES = {
    "11111111111": {
        "nome": "Ana Souza",
        "dividas": [
            {"id": "D1", "credor": "Cartão Loja Bela", "saldo": 1850.40, "dias_atraso": 210},
            {"id": "D2", "credor": "Empréstimo Pessoal", "saldo": 3420.00, "dias_atraso": 45},
        ],
    },
    "22222222222": {
        "nome": "Bruno Lima",
        "dividas": [
            {"id": "D3", "credor": "Financiamento Moto", "saldo": 8900.00, "dias_atraso": 400},
        ],
    },
    "33333333333": {"nome": "Carla Dias", "dividas": []},
}

ACORDOS: list[dict] = []  # acordos fechados nesta execução
