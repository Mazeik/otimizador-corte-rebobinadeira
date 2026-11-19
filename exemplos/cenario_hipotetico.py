"""
Cenário hipotético: um mês de produção numa rebobinadeira fictícia.

Gera 4 semanas de pedidos aleatórios (mas reproduzíveis, semente fixa),
otimiza cada semana e estima quanto papel e dinheiro seriam economizados
em relação ao corte simples (uma largura por bobina).

TODOS os números (pedidos, gramatura, comprimento, preço) são inventados.

Uso:
    python exemplos/cenario_hipotetico.py
"""

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from otimizador_corte import Configuracao, Pedido, otimizar  # noqa: E402

# ---------------- Premissas do cenário (fictícias) ---------------- #
SEMENTE = 42
SEMANAS = 4
LARGURAS_POSSIVEIS = [60, 70, 75, 80, 90, 100, 110, 120, 140]
LARGURA_BOBINA_MAE = 1100  # mm
REFILE = 8  # mm por borda
COMPRIMENTO_BOBINA_M = 6000  # metros de papel em cada bobina-mãe
GRAMATURA_G_M2 = 80  # g/m²
PRECO_KG = 6.00  # R$/kg

# Massa de papel por mm de largura numa bobina-mãe:
#   comprimento (m) x 0,001 m x gramatura (g/m²) / 1000 = kg por mm
KG_POR_MM = COMPRIMENTO_BOBINA_M * 0.001 * GRAMATURA_G_M2 / 1000


def gerar_semana(rng: random.Random) -> list[Pedido]:
    """Sorteia de 5 a 7 itens de pedido, com larguras e quantidades variadas."""
    larguras = rng.sample(LARGURAS_POSSIVEIS, rng.randint(5, 7))
    return [Pedido(w, rng.randint(20, 150), f"Cliente {i + 1} (fictício)") for i, w in enumerate(larguras)]


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    rng = random.Random(SEMENTE)
    cfg = Configuracao(largura_bobina_mm=LARGURA_BOBINA_MAE, refile_mm=REFILE, custo_troca=1)

    print(f"| Semana | Itens | Bobinas (simples) | Bobinas (otimizado) | Perda simples | Perda otimizada | Trocas de faca |")
    print(f"|---|---:|---:|---:|---:|---:|---:|")
    tot_simples = tot_otim = 0
    for s in range(1, SEMANAS + 1):
        pedidos = gerar_semana(rng)
        res = otimizar(pedidos, cfg)
        c = res.comparacao
        tot_simples += c["simples_material_mm"]
        tot_otim += c["otimizado_material_mm"]
        print(
            f"| {s} | {len(pedidos)} | {c['simples_bobinas']} | {c['otimizado_bobinas']} | "
            f"{c['simples_perda_pct']:.1f}% | {c['otimizado_perda_pct']:.1f}% | {res.trocas_de_faca} |"
        )

    economia_mm = tot_simples - tot_otim
    economia_kg = economia_mm * KG_POR_MM
    print()
    print(f"Bobinas-mãe economizadas no mês: {economia_mm / LARGURA_BOBINA_MAE:.0f}")
    print(f"Papel economizado no mês: {economia_kg:,.0f} kg".replace(",", "."))
    print(f"Valor estimado: R$ {economia_kg * PRECO_KG:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))


if __name__ == "__main__":
    main()
