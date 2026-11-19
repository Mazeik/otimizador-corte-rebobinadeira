"""Testes básicos: rode com `python -m pytest`."""

import pytest

from otimizador_corte import Configuracao, Pedido, corte_simples, gerar_padroes, otimizar
from otimizador_corte.padroes import largura_usada


def test_padroes_respeitam_largura_e_facas():
    larguras = [140, 90, 75, 60]
    padroes = gerar_padroes(larguras, largura_util=490, max_tiras=6)
    assert padroes
    for p in padroes:
        assert largura_usada(p, larguras) <= 490
        assert sum(p) <= 6


def test_exemplo_classico_75mm():
    # Bobina de 500 mm e pedido de 75 mm: 6 tiras por bobina, 50 mm de apara.
    cfg = Configuracao(largura_bobina_mm=500, facas=17)
    res = otimizar([Pedido(75, 60)], cfg)
    assert res.bobinas_mae == 10
    assert res.planos[0].apara_mm == 50


def test_limite_de_facas():
    # 20 mm caberia 25 vezes em 500 mm, mas 17 facas permitem só 16 tiras.
    cfg = Configuracao(largura_bobina_mm=500, facas=17)
    res = otimizar([Pedido(20, 32)], cfg)
    assert all(p.tiras_por_bobina <= 16 for p in res.planos)
    assert res.bobinas_mae == 2


def test_atende_todos_os_pedidos_e_nunca_pior_que_simples():
    pedidos = [Pedido(140, 25), Pedido(110, 45), Pedido(90, 80), Pedido(75, 150), Pedido(60, 60)]
    cfg = Configuracao(largura_bobina_mm=500, facas=17, refile_mm=5)
    res = otimizar(pedidos, cfg)
    for p in pedidos:
        assert res.produzido[p.largura_mm] >= p.quantidade
    simples = corte_simples({p.largura_mm: p.quantidade for p in pedidos}, cfg)
    assert res.bobinas_mae <= simples["bobinas_mae"]


def test_custo_de_troca_reduz_padroes():
    pedidos = [Pedido(140, 25), Pedido(110, 45), Pedido(90, 80), Pedido(75, 150), Pedido(60, 60)]
    sem = otimizar(pedidos, Configuracao(refile_mm=5))
    com = otimizar(pedidos, Configuracao(refile_mm=5, custo_troca=0.5, tempo_limite_s=6))
    assert com.trocas_de_faca <= sem.trocas_de_faca


def test_largura_maior_que_bobina_da_erro():
    with pytest.raises(ValueError):
        otimizar([Pedido(600, 1)], Configuracao(largura_bobina_mm=500))


def test_varias_larguras_de_bobina_mae():
    # Com 500, 800 e 1100 mm disponíveis, nunca gasta mais papel que só com 1100.
    pedidos = [Pedido(75, 60), Pedido(70, 40), Pedido(110, 20)]
    so_1100 = otimizar(pedidos, Configuracao(largura_bobina_mm=1100, refile_mm=8))
    varias = otimizar(
        pedidos, Configuracao(largura_bobina_mm=[500, 800, 1100], refile_mm=8, tempo_limite_s=10)
    )
    assert varias.material_mm <= so_1100.material_mm
    assert set(varias.bobinas_por_largura) <= {500, 800, 1100}
    for p in pedidos:
        assert varias.produzido[p.largura_mm] >= p.quantidade


def test_refile_maior_reduz_largura_util():
    # 1100 mm com refile de 25 mm por borda: sobram 1050 mm -> 15 tiras de 70 mm.
    res = otimizar([Pedido(70, 15)], Configuracao(largura_bobina_mm=1100, refile_mm=25))
    assert res.planos[0].tiras_por_bobina == 15
    assert res.planos[0].posicoes_facas[0] == 25
