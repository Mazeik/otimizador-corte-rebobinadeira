"""
Gera as figuras usadas no README (pasta docs/img/).

    python exemplos/gerar_figuras.py

Leva cerca de 2 minutos: o caso com custo de troca usa 120 s de solver
para chegar ao plano ótimo (2 ajustes de faca).
"""

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # gera arquivos sem abrir janela
import matplotlib.pyplot as plt  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from otimizador_corte import Configuracao, ler_pedidos_csv, otimizar  # noqa: E402

SAIDA = RAIZ / "docs" / "img"

# Paleta categórica validada para daltonismo (ordem fixa: 1 cor por largura).
CORES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300"]
CINZA_APARA = "#d6d5d0"
CINZA_SIMPLES = "#9b9a95"
TEXTO = "#0b0b0b"
TEXTO_2 = "#52514e"
FUNDO = "#fcfcfb"

plt.rcParams.update(
    {
        "font.size": 10,
        "axes.edgecolor": "#c3c2b7",
        "axes.labelcolor": TEXTO_2,
        "xtick.color": TEXTO_2,
        "ytick.color": TEXTO,
        "figure.facecolor": FUNDO,
        "axes.facecolor": FUNDO,
    }
)


def figura_padroes(res, cfg, larguras_pedido, arquivo):
    """Desenha cada padrão como uma barra: tiras coloridas por largura, apara em cinza."""
    cor = {w: CORES[i % len(CORES)] for i, w in enumerate(sorted(larguras_pedido, reverse=True))}
    fig, ax = plt.subplots(figsize=(10, 1.1 * len(res.planos) + 1.2))
    for i, p in enumerate(res.planos):
        x = 0
        ax.barh(i, cfg.refile_mm, left=x, color=CINZA_APARA, height=0.6)
        x += cfg.refile_mm
        for w, k in sorted(p.padrao.items(), reverse=True):
            for _ in range(k):
                # edgecolor = cor do fundo: cria o espaço de 2 px entre as tiras
                ax.barh(i, w, left=x, color=cor[w], edgecolor=FUNDO, linewidth=2, height=0.6)
                ax.text(x + w / 2, i, str(w), ha="center", va="center", fontsize=8, color=TEXTO)
                x += w
        ax.barh(i, p.largura_bobina_mm - x, left=x, color=CINZA_APARA, height=0.6)
    ax.set_yticks(range(len(res.planos)))
    ax.set_yticklabels(
        [f"Padrão {i + 1}\n{p.repeticoes} bobinas" for i, p in enumerate(res.planos)]
    )
    ax.invert_yaxis()
    ax.set_xlim(0, max(cfg.larguras_bobina))
    ax.set_xlabel("posição na bobina-mãe (mm) — números = largura da tira; cinza = refile + apara")
    ax.set_title(
        f"Plano ótimo: {res.bobinas_mae} bobinas de {cfg.larguras_bobina[0]} mm, "
        f"perda {res.perda_percentual:.1f}%, {res.trocas_de_faca} ajustes de faca".replace(".", ","),
        loc="left", color=TEXTO,
    )
    for lado in ("top", "right", "left"):
        ax.spines[lado].set_visible(False)
    ax.tick_params(axis="y", length=0)
    fig.tight_layout()
    fig.savefig(arquivo, dpi=150)
    plt.close(fig)


def figura_comparacao(linhas, arquivo):
    """Barras horizontais agrupadas: perda do corte simples x otimizado em cada cenário."""
    fig, ax = plt.subplots(figsize=(9, 3.6))
    altura = 0.36
    for i, (nome, simples, otim) in enumerate(linhas):
        ax.barh(i - altura / 2, simples, height=altura, color=CINZA_SIMPLES, edgecolor=FUNDO, linewidth=2,
                label="Corte simples" if i == 0 else None)
        ax.barh(i + altura / 2, otim, height=altura, color=CORES[0], edgecolor=FUNDO, linewidth=2,
                label="Otimizado" if i == 0 else None)
        ax.text(simples + 0.15, i - altura / 2, f"{simples:.1f}%".replace(".", ","), va="center", color=TEXTO_2)
        ax.text(otim + 0.15, i + altura / 2, f"{otim:.1f}%".replace(".", ","), va="center", color=TEXTO)
    ax.set_yticks(range(len(linhas)))
    ax.set_yticklabels([n for n, _, _ in linhas])
    ax.invert_yaxis()
    ax.set_xlabel("perda (% da largura da bobina-mãe)")
    ax.set_title("Perda de papel: corte simples × otimizado (dados fictícios)", loc="left", color=TEXTO)
    ax.legend(frameon=False, loc="lower right")
    ax.xaxis.grid(True, color="#e8e7e3")
    ax.set_axisbelow(True)
    for lado in ("top", "right", "left"):
        ax.spines[lado].set_visible(False)
    ax.tick_params(axis="y", length=0)
    fig.tight_layout()
    fig.savefig(arquivo, dpi=150)
    plt.close(fig)


def main():
    SAIDA.mkdir(parents=True, exist_ok=True)
    pedidos = ler_pedidos_csv(RAIZ / "dados" / "pedidos_exemplo.csv")
    larguras = {p.largura_mm for p in pedidos}

    # Figura 1: plano com menos trocas de faca (bobina de 1100 mm).
    cfg = Configuracao(largura_bobina_mm=1100, refile_mm=8, custo_troca=1, tempo_limite_s=120)
    figura_padroes(otimizar(pedidos, cfg), cfg, larguras, SAIDA / "padroes_corte.png")

    # Figura 2: comparação nos cenários do README.
    cenarios = [
        ("Bobina 500 mm", Configuracao(largura_bobina_mm=500, refile_mm=5)),
        ("Bobina 1100 mm", Configuracao(largura_bobina_mm=1100, refile_mm=8)),
        ("Bobinas 500/800/1100 mm", Configuracao(largura_bobina_mm=[500, 800, 1100], refile_mm=8)),
    ]
    linhas = []
    for nome, c in cenarios:
        r = otimizar(pedidos, c)
        linhas.append((nome, r.comparacao["simples_perda_pct"], r.perda_percentual))
    figura_comparacao(linhas, SAIDA / "comparacao_perda.png")
    print(f"Figuras salvas em {SAIDA}")


if __name__ == "__main__":
    main()
