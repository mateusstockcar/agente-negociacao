"""Testes das regras de negócio e das ferramentas — sem chamar a IA (rápidos e grátis)."""

import json

import pytest

from negociacao import politica
from negociacao.ferramentas import consultar_dividas, fechar_acordo, simular_acordo

ANA = {"configurable": {"cpf": "11111111111"}}
BRUNO = {"configurable": {"cpf": "22222222222"}}


def test_desconto_por_faixa_de_atraso():
    assert politica.desconto_maximo(45, 1) == 10
    assert politica.desconto_maximo(210, 1) == 30
    assert politica.desconto_maximo(400, 1) == 50
    assert politica.desconto_maximo(400, 6) == 25  # parcelado: metade


def test_simulacao_calcula_valores():
    r = politica.simular(1000.0, 210, 1, 30)
    assert r["valor_total"] == 700.0 and r["economia"] == 300.0


@pytest.mark.parametrize("parcelas,desconto", [(1, 31), (6, 30), (13, 0), (0, 0)])
def test_politica_bloqueia_propostas_invalidas(parcelas, desconto):
    with pytest.raises(ValueError):
        politica.simular(1000.0, 210, parcelas, desconto)


def test_parcela_minima():
    with pytest.raises(ValueError):
        politica.simular(300.0, 45, 12, 0)  # 12x de R$ 25


def test_ferramenta_nao_acessa_divida_de_outro_cliente():
    r = json.loads(simular_acordo.invoke({"divida_id": "D3", "parcelas": 1, "desconto_percentual": 0}, config=ANA))
    assert "erro" in r


def test_fechar_acordo_recheca_politica():
    r = json.loads(fechar_acordo.invoke({"divida_id": "D1", "parcelas": 1, "desconto_percentual": 90}, config=ANA))
    assert "erro" in r


def test_fluxo_feliz():
    dividas = json.loads(consultar_dividas.invoke({}, config=BRUNO))
    assert dividas["nome"] == "Bruno Lima" and dividas["dividas_abertas"][0]["id"] == "D3"
    simulacao = json.loads(simular_acordo.invoke({"divida_id": "d3", "parcelas": 1, "desconto_percentual": 50}, config=BRUNO))
    assert simulacao["valor_total"] == 4450.0


def test_divida_em_acordo_sai_da_lista_e_nao_aceita_novo_acordo():
    from negociacao.dados import ACORDOS
    ACORDOS.append({"divida_id": "D2", "protocolo": "AC-TESTE"})
    try:
        r = json.loads(consultar_dividas.invoke({}, config=ANA))
        assert [d["id"] for d in r["dividas_abertas"]] == ["D1"]
        assert r["dividas_em_acordo"][0]["protocolo"] == "AC-TESTE"
        r = json.loads(simular_acordo.invoke({"divida_id": "D2", "parcelas": 1, "desconto_percentual": 0}, config=ANA))
        assert "já tem acordo" in r["erro"]
    finally:
        ACORDOS.clear()
