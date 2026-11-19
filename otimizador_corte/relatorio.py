"""Leitura de pedidos (CSV) e impressão do plano de corte."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import List

from .otimizador import Configuracao, Pedido, Resultado


def ler_pedidos_csv(caminho: str | Path) -> List[Pedido]:
    """Lê um CSV com as colunas: cliente, largura_mm, quantidade."""
    pedidos: List[Pedido] = []
    with open(caminho, newline="", encoding="utf-8") as f:
        for linha in csv.DictReader(f):
            pedidos.append(
                Pedido(
                    largura_mm=int(linha["largura_mm"]),
                    quantidade=int(linha["quantidade"]),
                    cliente=linha.get("cliente", ""),
                )
            )
    return pedidos


def desenhar_padrao(padrao: dict, largura_bobina: int, cfg: Configuracao) -> str:
    """Desenho em texto de uma bobina cortada (cerca de 55 caracteres de largura)."""
    escala_mm = max(10, largura_bobina // 50)  # mm por caractere
    partes = []
    if cfg.refile_mm:
        partes.append("░" * max(1, cfg.refile_mm // escala_mm))
    for w, k in sorted(padrao.items(), reverse=True):
        for _ in range(k):
            miolo = str(w).center(max(len(str(w)), w // escala_mm - 1))
            partes.append(miolo)
    usado = sum(w * k for w, k in padrao.items()) + cfg.refile_mm
    sobra = largura_bobina - usado
    if sobra > 0:
        partes.append("░" * max(1, sobra // escala_mm))
    return "|" + "|".join(partes) + "|"


def formatar_resultado(res: Resultado, cfg: Configuracao) -> str:
    """Texto pronto para o operador / planejamento."""
    L = []
    L.append("=" * 64)
    L.append(" PLANO DE CORTE — REBOBINADEIRA")
    L.append("=" * 64)
    disponiveis = ", ".join(f"{w}" for w in cfg.larguras_bobina)
    L.append(
        f" Bobinas-mãe disponíveis: {disponiveis} mm | Facas: {cfg.facas} "
        f"(máx. {cfg.max_tiras} tiras)"
    )
    L.append(f" Refile mínimo: {cfg.refile_mm} mm/borda | Status do solver: {res.status}")
    L.append("")

    for i, p in enumerate(res.planos, 1):
        composicao = " + ".join(f"{k} x {w}" for w, k in sorted(p.padrao.items(), reverse=True))
        L.append(f" Padrão {i}: cortar {p.repeticoes} bobina(s) de {p.largura_bobina_mm} mm")
        L.append(f"   Tiras:  {composicao}  ({p.tiras_por_bobina} tiras)")
        L.append(f"   Apara:  {p.apara_mm} mm por bobina (refile + sobra)")
        L.append(f"   Facas ({len(p.posicoes_facas)}) em mm: {p.posicoes_facas}")
        L.append(f"   {desenhar_padrao(p.padrao, p.largura_bobina_mm, cfg)}")
        L.append("")

    L.append("-" * 64)
    L.append(f" {'Largura':>8} {'Pedido':>8} {'Produzido':>10} {'Excedente':>10}")
    for w in res.produzido:
        pedido = res.produzido[w] - res.excedente[w]
        L.append(f" {w:>6}mm {pedido:>8} {res.produzido[w]:>10} {res.excedente[w]:>10}")
    L.append("-" * 64)

    c = res.comparacao
    por_largura = ", ".join(f"{n} x {w} mm" for w, n in sorted(res.bobinas_por_largura.items()))
    L.append(f" Bobinas-mãe usadas:  {res.bobinas_mae}  ({por_largura})")
    L.append(f" Trocas de faca:      {res.trocas_de_faca}")
    L.append(f" Apara total:         {res.apara_total_mm} mm ({res.perda_percentual:.2f}%)")
    if c:
        L.append("")
        L.append(" Comparação com corte simples (uma largura por bobina):")
        L.append(
            f"   Simples:    {c['simples_bobinas']:>4} bobinas | "
            f"{c['simples_material_mm']:>7} mm de papel | perda {c['simples_perda_pct']:.2f}%"
        )
        L.append(
            f"   Otimizado:  {c['otimizado_bobinas']:>4} bobinas | "
            f"{c['otimizado_material_mm']:>7} mm de papel | perda {c['otimizado_perda_pct']:.2f}%"
        )
        L.append(
            f"   Economia:   {c['material_economizado_mm']} mm de papel ({c['economia_pct']:.1f}%)"
        )
    L.append("=" * 64)
    return "\n".join(L)
