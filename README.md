# Otimizador de Corte para Rebobinadeira

Ferramenta em Python que calcula **a melhor forma de cortar bobinas-mãe de papel** numa rebobinadeira de facas, atendendo os pedidos dos clientes e gerando **a menor apara (perda) possível**.

## O problema

Na rebobinadeira, a bobina-mãe chega com uma largura que **varia de 500 a 1100 mm** e é cortada por **17 facas** em bobinas-filhas nas larguras que os clientes pedem. As bordas levam um **refile**, cujo tamanho depende do ajuste das facas.

Se o cliente pede **75 mm** e uma bobina de 500 mm é cortada só nessa largura:

```
6 × 75 mm = 450 mm   →   50 mm de apara em TODA bobina (10% de perda)
```

Quando chegam vários pedidos (70, 75, 90, 110 mm...), dá para **combinar larguras diferentes na mesma bobina** e aproveitar essa sobra. Só que o número de combinações é enorme: numa bobina de 1100 mm, com 6 larguras e até 16 tiras, são mais de 4.500 combinações possíveis. Escolher na mão quais usar, e quantas vezes cada uma, é inviável. Esse é o clássico **Problema de Corte Unidimensional** (*Cutting Stock Problem*).

## O método

1. **Geração de padrões** ([padroes.py](otimizador_corte/padroes.py)): para cada largura de bobina-mãe disponível, listamos todas as formas viáveis de posicionar as facas, respeitando:
   - soma das larguras ≤ largura da bobina − 2 × refile mínimo;
   - nº de tiras ≤ nº de facas − 1 (com 17 facas, até 16 tiras).
2. **Otimização** ([otimizador.py](otimizador_corte/otimizador.py)): um modelo de **Programação Linear Inteira** decide quantas bobinas-mãe cortar com cada padrão:

   ```
   minimizar    Σ W_p · x_p  +  custo_troca · W_max · Σ y_p
   sujeito a    Σ_p a_ip · x_p ≥ demanda_i      (todo pedido é atendido)
                x_p ≤ M · y_p                     (y_p = padrão p foi usado)
                x_p inteiro ≥ 0,  y_p ∈ {0,1}
   ```

   - `x_p`: quantas bobinas cortar com o padrão `p`
   - `W_p`: largura da bobina-mãe do padrão (minimizar `Σ W_p·x_p` = gastar menos papel)
   - `a_ip`: quantas tiras da largura `i` o padrão `p` gera
   - `custo_troca` (opcional): penaliza cada padrão diferente, porque trocar as facas toma tempo de máquina. É medido em "bobinas da maior largura".

   O modelo é resolvido com o solver **HiGHS**, que já vem no SciPy (`scipy.optimize.milp`). Com custo de troca, o problema fica bem mais pesado. Por isso ele é resolvido em duas etapas: primeiro só o papel, depois as trocas, considerando só os ~400 padrões mais promissores (escolhidos pelo *custo reduzido* da relaxação linear).
3. **Comparação** com o *corte simples* (uma largura por bobina), para medir o ganho.

O resultado traz, para cada padrão, **a largura da bobina-mãe e a posição de cada faca em mm**, prontas para o operador.

## Resultados (dados fictícios)

Pedidos: 25 × 140 mm, 45 × 110 mm, 80 × 90 mm, 150 × 75 mm, 90 × 70 mm e 60 × 60 mm.

| Cenário | Corte simples | Otimizado | Trocas de faca |
|---|---|---|---:|
| Bobina 500 mm, refile 5 mm | 83 bobinas, perda 9,11% | **76 bobinas, perda 2,51%** | 13 |
| Bobina 1100 mm, refile 8 mm | 37 bobinas, perda 6,34% | **35 bobinas, perda 1,82%** | 7 |
| Bobina 1100 mm, refile 8 mm, `custo_troca = 1` | 37 bobinas | **35 bobinas, perda 1,82%** | **2** |
| Bobinas de 500, 800 e 1100 mm, refile 8 mm | 39.800 mm de papel, perda 5,88% | **37.600 mm de papel, perda 1,89%** | 17 |

Com a bobina de 1100 mm, o pedido inteiro sai com **apenas 2 ajustes de faca**:

```
 Padrão 1: cortar 20 bobina(s) de 1100 mm
   Tiras:  4 x 90 + 6 x 75 + 3 x 70 + 1 x 60  (14 tiras)
   Apara:  20 mm por bobina (refile + sobra)
   Facas (15) em mm: [8, 98, 188, 278, 368, 443, 518, 593, 668, 743, 818, 888, 958, 1028, 1088]
   |░| 90| 90| 90| 90|75|75|75|75|75|75|70|70|70|60|░|

 Padrão 2: cortar 15 bobina(s) de 1100 mm
   Tiras:  2 x 140 + 3 x 110 + 2 x 75 + 2 x 70 + 3 x 60  (12 tiras)
   Apara:  20 mm por bobina (refile + sobra)
   Facas (13) em mm: [8, 148, 288, 398, 508, 618, 693, 768, 838, 908, 968, 1028, 1088]
   |░| 140 | 140 |110 |110 |110 |75|75|70|70|60|60|60|░|
```

### Cenário hipotético: um mês de produção

Simulando 4 semanas de pedidos fictícios numa bobina de 1100 mm, o otimizador economizaria **18 bobinas-mãe no mês (≈ 9.500 kg de papel, ≈ R$ 57 mil)**, reduzindo a perda de 6–9% para cerca de 2%, com 3 ou 4 ajustes de faca por semana. Detalhes e premissas em [docs/cenario_hipotetico.md](docs/cenario_hipotetico.md).

## Como usar

```bash
pip install -r requirements.txt

# uma largura de bobina-mãe
python main.py dados/pedidos_exemplo.csv --largura 1100 --refile 8

# várias larguras disponíveis: o programa escolhe a melhor para cada padrão
python main.py dados/pedidos_exemplo.csv --largura 500 800 1100 --refile 8

# preferindo menos trocas de faca
python main.py dados/pedidos_exemplo.csv --largura 1100 --refile 8 --custo-troca 1
```

Opções:

| Opção | Significado | Padrão |
|---|---|---|
| `--largura` | largura(s) da bobina-mãe em mm (uma ou várias) | 500 |
| `--facas` | número de facas da máquina | 17 |
| `--refile` | refile **mínimo** em cada borda (mm); se sobrar mais, vira apara | 0 |
| `--custo-troca` | penalidade por padrão diferente, em bobinas | 0 |
| `--excedente-max` | excedente máximo por item (0.1 = 10%) | sem limite |

O CSV de pedidos tem as colunas `cliente,largura_mm,quantidade` (ver [dados/pedidos_exemplo.csv](dados/pedidos_exemplo.csv)).

Também dá para usar direto no Python:

```python
from otimizador_corte import Configuracao, Pedido, otimizar, formatar_resultado

cfg = Configuracao(largura_bobina_mm=[500, 800, 1100], facas=17, refile_mm=8)
res = otimizar([Pedido(75, 120), Pedido(70, 90), Pedido(110, 45)], cfg)
print(formatar_resultado(res, cfg))
```

## Demonstração

O notebook [notebooks/demonstracao.ipynb](notebooks/demonstracao.ipynb) mostra o passo a passo, com gráfico dos padrões de corte, o caso com várias larguras de bobina-mãe e o efeito do custo de troca de facas.

## Estrutura

```
├── otimizador_corte/
│   ├── padroes.py       # geração dos padrões de corte
│   ├── otimizador.py    # modelo de otimização e comparação
│   └── relatorio.py     # leitura do CSV e relatório para o operador
├── dados/
│   └── pedidos_exemplo.csv   # pedidos fictícios
├── docs/
│   └── cenario_hipotetico.md # um mês de produção simulado
├── exemplos/
│   └── cenario_hipotetico.py # script que gera o cenário
├── notebooks/
│   └── demonstracao.ipynb
├── tests/
│   └── test_otimizador.py
├── main.py              # linha de comando
└── requirements.txt
```

Para rodar os testes: `python -m pytest`

## Limitações e próximos passos

- Considera só a **largura**; não trata comprimento/diâmetro das bobinas-filhas nem emendas.
- Não limita quantas bobinas-mãe de cada largura existem em estoque.
- Em casos grandes (várias larguras de bobina-mãe, custo de troca), o solver para no tempo limite (30 s por padrão) e informa **quão longe do ótimo** a solução pode estar. O próximo passo seria usar **geração de colunas** (Gilmore-Gomory).
- Possíveis extensões: prioridade e prazo por cliente, estoque de bobinas-mãe, interface web.

## Aviso

Todos os dados deste repositório são **fictícios** e servem apenas para demonstração.

## Licença

[MIT](LICENSE)
