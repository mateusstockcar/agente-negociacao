"""Política de negociação: as REGRAS DO NEGÓCIO ficam no código, não no prompt.

Lição central deste projeto: o modelo de IA conversa, mas quem CALCULA valores e
DECIDE o que é permitido é código determinístico. Assim o agente não consegue
"inventar" um desconto, mesmo se o cliente insistir ou tentar enganá-lo.
"""

MAX_PARCELAS = 12
PARCELA_MINIMA = 50.00


def desconto_maximo(dias_atraso: int, parcelas: int) -> float:
    """Desconto máximo (em %) por faixa de atraso. Parcelado ganha metade do desconto."""
    if dias_atraso < 90:
        base = 10.0
    elif dias_atraso <= 365:
        base = 30.0
    else:
        base = 50.0
    return base if parcelas == 1 else base / 2


def simular(saldo: float, dias_atraso: int, parcelas: int, desconto_percentual: float) -> dict:
    """Valida a proposta contra a política e calcula os valores. Lança ValueError se violar."""
    if not 1 <= parcelas <= MAX_PARCELAS:
        raise ValueError(f"Número de parcelas deve ser entre 1 e {MAX_PARCELAS}.")
    maximo = desconto_maximo(dias_atraso, parcelas)
    if not 0 <= desconto_percentual <= maximo:
        raise ValueError(f"Desconto de {desconto_percentual}% não permitido. "
                         f"O máximo para esta dívida em {parcelas}x é {maximo}%.")
    total = round(saldo * (1 - desconto_percentual / 100), 2)
    parcela = round(total / parcelas, 2)
    if parcela < PARCELA_MINIMA:
        raise ValueError(f"Parcela de R$ {parcela:.2f} abaixo do mínimo de R$ {PARCELA_MINIMA:.2f}. "
                         "Ofereça menos parcelas.")
    return {"saldo_atual": saldo, "desconto_percentual": desconto_percentual,
            "valor_total": total, "parcelas": parcelas, "valor_parcela": parcela,
            "economia": round(saldo - total, 2)}
