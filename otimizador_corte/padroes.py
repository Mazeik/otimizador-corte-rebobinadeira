"""
Geração de padrões de corte.

Um *padrão* é uma forma de posicionar as facas na rebobinadeira: quantas
tiras de cada largura saem de UMA bobina-mãe.

Exemplo (bobina de 500 mm, pedidos de 75 mm e 120 mm):
    (4, 1)  ->  4 x 75 + 1 x 120 = 420 mm usados, 80 mm de apara

Restrições físicas consideradas:
    * soma das larguras  <=  largura útil (largura da bobina - refiles)
    * número de tiras    <=  número de facas - 1
      (cada tira precisa de uma faca de cada lado; facas vizinhas são
      compartilhadas, então N tiras usam N + 1 facas)
"""

from __future__ import annotations

from typing import List, Sequence, Tuple

Padrao = Tuple[int, ...]  # quantidade de tiras de cada largura, na ordem das larguras


def gerar_padroes(
    larguras: Sequence[int],
    largura_util: int,
    max_tiras: int,
    somente_maximais: bool = True,
) -> List[Padrao]:
    """Enumera todos os padrões de corte viáveis.

    Parâmetros
    ----------
    larguras : larguras (mm) pedidas pelos clientes, uma por item.
    largura_util : largura disponível para as tiras (mm), já sem refile.
    max_tiras : máximo de tiras por bobina (facas - 1).
    somente_maximais : se True, descarta padrões "incompletos", isto é,
        aqueles em que ainda caberia mais uma tira de alguma largura.
        Isso reduz muito o número de padrões sem piorar o resultado,
        porque um padrão incompleto só joga material fora como apara.

    Retorna
    -------
    Lista de tuplas; a posição i da tupla é quantas tiras da larguras[i].
    """
    if largura_util <= 0:
        raise ValueError("A largura útil precisa ser positiva (verifique o refile).")
    if max_tiras < 1:
        raise ValueError("É preciso pelo menos 2 facas (1 tira).")

    n = len(larguras)
    menor_largura = min(larguras)
    padroes: List[Padrao] = []
    atual = [0] * n

    # Busca em profundidade: para cada largura, tenta de "o máximo que cabe" até 0.
    def explorar(i: int, sobra: int, tiras_restantes: int) -> None:
        if i == n:
            if sum(atual) == 0:
                return  # padrão vazio não serve
            if somente_maximais and _cabe_mais(sobra, tiras_restantes, larguras, menor_largura):
                return
            padroes.append(tuple(atual))
            return

        maximo = min(sobra // larguras[i], tiras_restantes)
        for k in range(maximo, -1, -1):
            atual[i] = k
            explorar(i + 1, sobra - k * larguras[i], tiras_restantes - k)
        atual[i] = 0

    explorar(0, largura_util, max_tiras)
    return padroes


def _cabe_mais(sobra: int, tiras_restantes: int, larguras: Sequence[int], menor: int) -> bool:
    """True se ainda cabe pelo menos mais uma tira no padrão."""
    return tiras_restantes > 0 and sobra >= menor


def largura_usada(padrao: Padrao, larguras: Sequence[int]) -> int:
    """Soma das larguras das tiras de um padrão (mm)."""
    return sum(q * w for q, w in zip(padrao, larguras))


def posicoes_das_facas(padrao: Padrao, larguras: Sequence[int], refile: int) -> List[int]:
    """Calcula onde cada faca deve ser posicionada (mm a partir da borda esquerda).

    As tiras são colocadas da maior para a menor, começando após o refile.
    Retorna a lista de posições; o tamanho da lista é o número de facas usadas.
    """
    tiras = sorted(
        (w for q, w in zip(padrao, larguras) for _ in range(q)),
        reverse=True,
    )
    posicoes = [refile]
    for w in tiras:
        posicoes.append(posicoes[-1] + w)
    return posicoes
