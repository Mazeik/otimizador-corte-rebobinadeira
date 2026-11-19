# Cenário hipotético: um mês de produção

> Tudo nesta página é **inventado**: a fábrica, os pedidos, a gramatura e o preço. O objetivo é mostrar a ordem de grandeza do ganho, não descrever uma empresa real.

## A situação

Uma rebobinadeira fictícia recebe bobinas-mãe de **1100 mm**, com **17 facas** e refile mínimo de **8 mm** por borda. Toda semana chegam de 5 a 7 itens de pedido, com larguras entre 60 e 140 mm e de 20 a 150 bobinas-filhas por item.

Hoje, cada bobina-mãe é cortada com **uma largura só** (corte simples). A proposta é usar o otimizador para **combinar larguras** na mesma bobina, preferindo poucos ajustes de faca (`custo_troca = 1`).

Premissas para converter em peso e dinheiro:

| Premissa | Valor (fictício) |
|---|---|
| Comprimento da bobina-mãe | 6.000 m |
| Gramatura | 80 g/m² |
| Preço do papel | R$ 6,00/kg |
| Papel por mm de largura de uma bobina-mãe | 0,48 kg |

## Resultado semana a semana

| Semana | Itens | Bobinas (simples) | Bobinas (otimizado) | Perda simples | Perda otimizada | Trocas de faca |
|---|---:|---:|---:|---:|---:|---:|
| 1 | 7 | 39 | 35 | 6,4% | 1,8% | 4 |
| 2 | 5 | 46 | 40 | 7,7% | 1,8% | 4 |
| 3 | 5 | 34 | 31 | 6,7% | 2,4% | 3 |
| 4 | 6 | 46 | 41 | 9,0% | 1,8% | 3 |

## No mês

| | |
|---|---:|
| Bobinas-mãe economizadas | **18** (de 165 para 147) |
| Papel economizado | **≈ 9.500 kg** |
| Valor estimado | **≈ R$ 57 mil/mês** |

A perda cai de **6 a 9%** para **cerca de 2%**, com apenas **3 ou 4 ajustes de faca por semana**.

## Como reproduzir

```bash
python exemplos/cenario_hipotetico.py
```

Os pedidos são sorteados com semente fixa (`SEMENTE = 42`), então o resultado é sempre o mesmo. Para testar outro cenário, mude as premissas no começo do arquivo [exemplos/cenario_hipotetico.py](../exemplos/cenario_hipotetico.py). Leva cerca de 1 minuto.

## Cuidados na interpretação

- O ganho real depende do mix de pedidos. Pedidos com uma largura só ou larguras que já "fecham" bem na bobina ganham pouco.
- Bobinas-filhas excedentes (quando o padrão produz um pouco além do pedido) foram tratadas como produto, não como perda. Na prática, elas precisam ter saída (estoque ou próximo pedido).
- O tempo de troca de facas não foi convertido em dinheiro. Ele entra só como penalidade no modelo.
