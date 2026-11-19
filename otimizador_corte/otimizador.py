"""
Otimização do corte na rebobinadeira (problema clássico de *Cutting Stock*).

Ideia em três passos:
    1. Gerar todos os padrões de corte possíveis (ver padroes.py), para cada
       largura de bobina-mãe disponível (ex.: 500, 800 e 1100 mm).
    2. Decidir QUANTAS bobinas-mãe cortar com cada padrão, de forma que:
         - todos os pedidos sejam atendidos;
         - a quantidade de papel consumida (e portanto a apara) seja mínima;
         - opcionalmente, use poucos padrões diferentes (menos trocas de faca).
    3. Comparar com o "corte simples" (uma largura por bobina), que é
       como muitas vezes se faz na prática.

O passo 2 é um problema de Programação Linear Inteira, resolvido com o
solver HiGHS que já vem no SciPy (scipy.optimize.milp) — sem dependência extra.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, linprog, milp

from .padroes import Padrao, gerar_padroes, largura_usada, posicoes_das_facas


# --------------------------------------------------------------------------- #
# Estruturas de dados
# --------------------------------------------------------------------------- #
@dataclass
class Pedido:
    """Um item pedido pelo cliente: N bobinas-filhas de uma certa largura."""

    largura_mm: int
    quantidade: int
    cliente: str = ""


@dataclass
class Configuracao:
    """Parâmetros da máquina e do processo.

    largura_bobina_mm aceita um número (ex.: 500) ou uma lista de larguras
    disponíveis (ex.: [500, 800, 1100]). Com uma lista, o otimizador escolhe
    qual largura usar em cada padrão.

    refile_mm é o refile MÍNIMO em cada borda. Se sobrar mais material, ele
    aparece como apara a mais naquele padrão (na prática, um refile maior).
    """

    largura_bobina_mm: int | Sequence[int] = 500
    facas: int = 17  # facas disponíveis na rebobinadeira
    refile_mm: int = 0  # refile mínimo em CADA borda
    custo_troca: float = 0.0  # penalidade por padrão diferente, em "bobinas"
    excedente_max: Optional[float] = None  # ex.: 0.10 = até 10% a mais por item
    tempo_limite_s: float = 30.0  # tempo máximo do solver (segundos)

    @property
    def max_tiras(self) -> int:
        return self.facas - 1

    @property
    def larguras_bobina(self) -> List[int]:
        """Larguras de bobina-mãe disponíveis, sempre como lista ordenada."""
        if isinstance(self.largura_bobina_mm, (int, np.integer)):
            return [int(self.largura_bobina_mm)]
        return sorted({int(w) for w in self.largura_bobina_mm})

    def largura_util(self, largura_bobina: int) -> int:
        return largura_bobina - 2 * self.refile_mm


@dataclass
class PlanoCorte:
    """Um padrão de corte e quantas bobinas-mãe serão cortadas com ele."""

    largura_bobina_mm: int  # largura da bobina-mãe deste padrão
    padrao: Dict[int, int]  # {largura_mm: tiras por bobina}
    repeticoes: int  # quantas bobinas-mãe cortar assim
    apara_mm: int  # perda por bobina (inclui refile)
    posicoes_facas: List[int]  # posição de cada faca, em mm

    @property
    def tiras_por_bobina(self) -> int:
        return sum(self.padrao.values())


@dataclass
class Resultado:
    planos: List[PlanoCorte]
    bobinas_mae: int
    bobinas_por_largura: Dict[int, int]  # {largura da bobina-mãe: quantidade}
    material_mm: int  # soma das larguras das bobinas-mãe usadas
    apara_total_mm: int
    perda_percentual: float
    produzido: Dict[int, int]  # {largura: tiras produzidas}
    excedente: Dict[int, int]  # {largura: tiras além do pedido}
    status: str
    comparacao: Dict[str, float] = field(default_factory=dict)

    @property
    def trocas_de_faca(self) -> int:
        """Número de padrões diferentes (= setups da máquina)."""
        return len(self.planos)


# --------------------------------------------------------------------------- #
# Funções principais
# --------------------------------------------------------------------------- #
def agrupar_pedidos(pedidos: Sequence[Pedido]) -> Dict[int, int]:
    """Soma quantidades de pedidos com a mesma largura (vários clientes)."""
    demanda: Dict[int, int] = {}
    for p in pedidos:
        if p.quantidade <= 0:
            continue
        demanda[p.largura_mm] = demanda.get(p.largura_mm, 0) + p.quantidade
    return dict(sorted(demanda.items(), reverse=True))


def _gerar_todos(larguras, cfg: Configuracao, somente_maximais: bool) -> List[Tuple[int, Padrao]]:
    """Padrões de todas as bobinas-mãe disponíveis: lista de (largura_bobina, padrão)."""
    todos: List[Tuple[int, Padrao]] = []
    for W in cfg.larguras_bobina:
        util = cfg.largura_util(W)
        cabem = [w for w in larguras if w <= util]
        if not cabem:
            continue
        # Gera só com as larguras que cabem e depois recoloca zeros nas demais.
        for p in gerar_padroes(cabem, util, cfg.max_tiras, somente_maximais):
            mapa = dict(zip(cabem, p))
            todos.append((W, tuple(mapa.get(w, 0) for w in larguras)))
    return todos


def otimizar(pedidos: Sequence[Pedido], cfg: Configuracao) -> Resultado:
    """Calcula o melhor plano de corte para um conjunto de pedidos."""
    demanda = agrupar_pedidos(pedidos)
    if not demanda:
        raise ValueError("Nenhum pedido com quantidade positiva.")

    larguras = list(demanda.keys())
    q = np.array([demanda[w] for w in larguras])

    maior_util = cfg.largura_util(max(cfg.larguras_bobina))
    for w in larguras:
        if w > maior_util:
            raise ValueError(f"Largura {w} mm não cabe na largura útil de {maior_util} mm.")

    # 1) Padrões "completos" bastam na maioria dos casos. Se houver limite de
    #    excedente, pode ser preciso usar padrões incompletos -> tenta de novo.
    tempo = cfg.tempo_limite_s / (2 if cfg.custo_troca > 0 else 1)
    padroes = _gerar_todos(larguras, cfg, somente_maximais=True)
    sol = _resolver(padroes, q, cfg, custo_troca=0, tempo=tempo)
    if sol is None and cfg.excedente_max is not None:
        padroes = _gerar_todos(larguras, cfg, somente_maximais=False)
        sol = _resolver(padroes, q, cfg, custo_troca=0, tempo=tempo)
    if sol is None:
        raise RuntimeError("O solver não encontrou solução. Revise os parâmetros.")
    x, status = sol

    # 2) Menos trocas de faca (opcional). O modelo com trocas é bem mais pesado,
    #    então ele é resolvido só com os padrões mais promissores: os da etapa 1
    #    mais os de menor "custo reduzido" na relaxação linear.
    if cfg.custo_troca > 0:
        idx = _selecionar_candidatos(padroes, q, x, cfg)
        sub = [padroes[i] for i in idx]
        sol2 = _resolver(sub, q, cfg, custo_troca=cfg.custo_troca, tempo=tempo)
        if sol2 is not None:
            x_etapa1 = np.zeros(len(sub), dtype=int)
            x_etapa1[: int((x > 0).sum())] = x[x > 0]  # padrões da etapa 1 vêm primeiro
            if _custo_total(sub, sol2[0], cfg) <= _custo_total(sub, x_etapa1, cfg):
                padroes, (x, status) = sub, sol2
            else:
                padroes, x = sub, x_etapa1

    resultado = _montar_resultado(padroes, x, larguras, q, cfg, status)
    resultado.comparacao = comparar_com_corte_simples(demanda, cfg, resultado)
    return resultado


MAX_CANDIDATOS = 400  # padrões considerados no modelo com custo de troca


def _custo_total(padroes, x, cfg: Configuracao) -> float:
    """Papel consumido + penalidade das trocas, na mesma unidade (mm)."""
    larg_max = max(cfg.larguras_bobina)
    papel = sum(W * xi for (W, _), xi in zip(padroes, x))
    return papel + cfg.custo_troca * larg_max * int((np.asarray(x) > 0).sum())


def _selecionar_candidatos(padroes, q, x, cfg: Configuracao) -> List[int]:
    """Escolhe os padrões mais promissores usando a relaxação linear.

    O "custo reduzido" de um padrão diz quanto ele é pior que a combinação
    ideal; padrões com custo reduzido perto de zero são os bons candidatos.
    Os padrões já usados na etapa 1 sempre entram (e vêm primeiro na lista).
    """
    usados = [i for i in range(len(padroes)) if x[i] > 0]
    if len(padroes) <= MAX_CANDIDATOS:
        return usados + [i for i in range(len(padroes)) if x[i] == 0]

    W = np.array([wb for wb, _ in padroes], dtype=float)
    A = np.array([p for _, p in padroes], dtype=float).T
    lp = linprog(W, A_ub=-A, b_ub=-q, bounds=(0, None), method="highs")
    duais = -lp.ineqlin.marginals  # valor de cada mm pedido, em mm de papel
    reduzido = W - A.T @ duais

    ordem = [i for i in np.argsort(reduzido) if x[i] == 0]
    return usados + ordem[: MAX_CANDIDATOS - len(usados)]


def _resolver(
    padroes: List[Tuple[int, Padrao]],
    q: np.ndarray,
    cfg: Configuracao,
    custo_troca: float,
    tempo: float,
):
    """Monta e resolve o modelo de Programação Linear Inteira.

    Variáveis:
        x_p  = nº de bobinas-mãe cortadas com o padrão p   (inteiro >= 0)
        y_p  = 1 se o padrão p é usado (só quando custo_troca > 0)

    Minimizar:   soma( W_p * x_p )  +  custo_troca * W_max * soma(y_p)
                 (W_p = largura da bobina-mãe do padrão, ou seja, o papel
                  consumido; custo_troca é medido em "bobinas da maior largura")
    Sujeito a:   para cada largura i:  soma_p( A[i,p] * x_p ) >= q_i
                 (e <= q_i * (1 + excedente_max), se informado)
                 x_p <= M_p * y_p
    """
    W = np.array([wb for wb, _ in padroes], dtype=float)
    A = np.array([p for _, p in padroes], dtype=float).T  # linhas = larguras, colunas = padrões
    n_lar, n_pad = A.shape
    # Custo de cada bobina-mãe proporcional à sua largura. Dividir pelo MDC deixa
    # os custos inteiros (ex.: 500, 800, 1100 -> 5, 8, 11), o que ajuda o solver
    # a provar a solução ótima bem mais rápido.
    mdc = int(np.gcd.reduce(W.astype(int)))
    peso = W / mdc

    # Limite superior de x_p: nunca vale a pena repetir um padrão além do
    # necessário para atender sozinho todos os itens que ele produz.
    M = np.where(A > 0, np.ceil(q[:, None] / np.where(A > 0, A, 1)), 0).max(axis=0)
    M = np.maximum(M, 1)

    if cfg.excedente_max is None:
        limite_sup = np.full(n_lar, np.inf)
    else:
        limite_sup = q + np.floor(q * cfg.excedente_max)

    if custo_troca > 0:
        c = np.concatenate([peso, np.full(n_pad, custo_troca * W.max() / mdc)])
        A_dem = np.hstack([A, np.zeros((n_lar, n_pad))])
        A_lig = np.hstack([np.eye(n_pad), -np.diag(M)])  # x_p - M_p*y_p <= 0
        restricoes = [
            LinearConstraint(A_dem, q, limite_sup),
            LinearConstraint(A_lig, -np.inf, 0),
        ]
        limites = Bounds(np.zeros(2 * n_pad), np.concatenate([M, np.ones(n_pad)]))
        inteiros = np.ones(2 * n_pad)
    else:
        c = peso
        restricoes = [LinearConstraint(A, q, limite_sup)]
        limites = Bounds(np.zeros(n_pad), M)
        inteiros = np.ones(n_pad)

    res = milp(
        c,
        constraints=restricoes,
        integrality=inteiros,
        bounds=limites,
        options={"time_limit": tempo, "disp": False},
    )
    if res.x is None:
        return None
    x = np.round(res.x[:n_pad]).astype(int)
    if res.status == 0:
        status = "ótimo"
    else:
        # Parou no tempo limite: o solver informa a distância máxima até o ótimo.
        gap = getattr(res, "mip_gap", None)
        extra = f", no máximo {100 * gap:.1f}% acima do ótimo" if gap is not None else ""
        status = f"melhor solução em {tempo:.0f}s{extra}"
    return x, status


def _montar_resultado(padroes, x, larguras, q, cfg: Configuracao, status: str) -> Resultado:
    planos: List[PlanoCorte] = []
    for (W, padrao), rep in zip(padroes, x):
        if rep <= 0:
            continue
        planos.append(
            PlanoCorte(
                largura_bobina_mm=W,
                padrao={w: k for w, k in zip(larguras, padrao) if k > 0},
                repeticoes=int(rep),
                apara_mm=W - largura_usada(padrao, larguras),
                posicoes_facas=posicoes_das_facas(padrao, larguras, cfg.refile_mm),
            )
        )
    # Agrupa por largura de bobina-mãe e, dentro dela, os mais usados primeiro.
    planos.sort(key=lambda p: (-p.largura_bobina_mm, -p.repeticoes))

    bobinas = sum(p.repeticoes for p in planos)
    por_largura: Dict[int, int] = {}
    for p in planos:
        por_largura[p.largura_bobina_mm] = por_largura.get(p.largura_bobina_mm, 0) + p.repeticoes
    material = sum(p.largura_bobina_mm * p.repeticoes for p in planos)
    apara_total = sum(p.apara_mm * p.repeticoes for p in planos)
    produzido = {w: sum(p.padrao.get(w, 0) * p.repeticoes for p in planos) for w in larguras}
    excedente = {w: produzido[w] - int(qi) for w, qi in zip(larguras, q)}

    return Resultado(
        planos=planos,
        bobinas_mae=bobinas,
        bobinas_por_largura=por_largura,
        material_mm=material,
        apara_total_mm=apara_total,
        perda_percentual=100 * apara_total / material,
        produzido=produzido,
        excedente=excedente,
        status=status,
    )


def corte_simples(demanda: Dict[int, int], cfg: Configuracao) -> Dict[str, float]:
    """Linha de base: cada bobina-mãe é cortada com UMA só largura.

    Ex.: bobina de 500 mm, pedido de 75 mm -> 6 tiras (450 mm) e 50 mm de apara.
    Havendo várias bobinas-mãe, usa para cada item a que dá menos apara.
    """
    bobinas = 0
    material = 0
    apara = 0
    for w, qtd in demanda.items():
        melhor = None
        for W in cfg.larguras_bobina:
            tiras = min(cfg.largura_util(W) // w, cfg.max_tiras)
            if tiras == 0:
                continue
            n = math.ceil(qtd / tiras)
            opcao = (n * W, n, n * (W - tiras * w))  # (material, bobinas, apara)
            if melhor is None or opcao < melhor:
                melhor = opcao
        material += melhor[0]
        bobinas += melhor[1]
        apara += melhor[2]
    return {
        "bobinas_mae": bobinas,
        "material_mm": material,
        "apara_total_mm": apara,
        "perda_percentual": 100 * apara / material,
    }


def comparar_com_corte_simples(demanda, cfg: Configuracao, res: Resultado) -> Dict[str, float]:
    base = corte_simples(demanda, cfg)
    return {
        "simples_bobinas": base["bobinas_mae"],
        "simples_material_mm": base["material_mm"],
        "simples_perda_pct": base["perda_percentual"],
        "otimizado_bobinas": res.bobinas_mae,
        "otimizado_material_mm": res.material_mm,
        "otimizado_perda_pct": res.perda_percentual,
        "material_economizado_mm": base["material_mm"] - res.material_mm,
        "economia_pct": 100 * (base["material_mm"] - res.material_mm) / base["material_mm"],
    }
