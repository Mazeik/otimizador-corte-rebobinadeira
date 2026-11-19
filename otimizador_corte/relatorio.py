"""Leitura de pedidos (CSV) e impressão do plano de corte."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import List

from .otimizador import Configuracao, Pedido, Resultado


COLUNAS_OBRIGATORIAS = ("largura_mm", "quantidade")


def ler_pedidos_csv(caminho: str | Path) -> List[Pedido]:
    """Lê um CSV com as colunas: cliente, largura_mm, quantidade.

    Aceita os dois formatos comuns:
      * vírgula como separador (padrão internacional);
      * ponto e vírgula, que é como o Excel em português salva CSV.
    Linhas com valores inválidos geram um erro que diz qual linha corrigir.
    """
    # utf-8-sig ignora o "BOM" que o Excel coloca no início do arquivo.
    with open(caminho, newline="", encoding="utf-8-sig") as f:
        texto = f.read()

    primeira_linha = texto.splitlines()[0] if texto.strip() else ""
    separador = ";" if primeira_linha.count(";") > primeira_linha.count(",") else ","
    leitor = csv.DictReader(texto.splitlines(), delimiter=separador)

    # Normaliza os nomes das colunas (tira espaços e deixa minúsculo).
    colunas = [c.strip().lower() for c in (leitor.fieldnames or [])]
    faltando = [c for c in COLUNAS_OBRIGATORIAS if c not in colunas]
    if faltando:
        raise ValueError(f"Coluna(s) obrigatória(s) ausente(s) no CSV: {', '.join(faltando)}.")

    pedidos: List[Pedido] = []
    for n_linha, bruta in enumerate(leitor, start=2):  # linha 1 = cabeçalho
        linha = {k.strip().lower(): (v or "").strip() for k, v in bruta.items() if k}
        if not linha.get("largura_mm") and not linha.get("quantidade"):
            continue  # linha em branco
        try:
            largura = int(linha["largura_mm"])
            quantidade = int(linha["quantidade"])
        except ValueError:
            raise ValueError(
                f"Linha {n_linha}: largura e quantidade precisam ser números inteiros "
                f"(lido: largura='{linha['largura_mm']}', quantidade='{linha['quantidade']}')."
            ) from None
        if largura <= 0 or quantidade < 0:
            raise ValueError(f"Linha {n_linha}: largura deve ser > 0 e quantidade >= 0.")
        pedidos.append(Pedido(largura, quantidade, linha.get("cliente", "")))
    return pedidos


def salvar_plano_csv(res: Resultado, caminho: str | Path) -> None:
    """Salva o plano de corte em CSV (separador ';' para abrir direto no Excel BR).

    Uma linha por padrão: largura da bobina-mãe, quantas cortar, composição
    das tiras, apara por bobina e posição das facas.
    """
    with open(caminho, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(
            ["padrao", "largura_bobina_mae_mm", "bobinas_a_cortar", "tiras",
             "n_tiras", "apara_mm_por_bobina", "posicao_facas_mm"]
        )
        for i, p in enumerate(res.planos, 1):
            composicao = " + ".join(f"{k}x{w_}" for w_, k in sorted(p.padrao.items(), reverse=True))
            facas = " ".join(str(x) for x in p.posicoes_facas)
            w.writerow([i, p.largura_bobina_mm, p.repeticoes, composicao,
                        p.tiras_por_bobina, p.apara_mm, facas])


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
