"""
Uso pela linha de comando:

    python main.py dados/pedidos_exemplo.csv --largura 500 --facas 17 --refile 5
    python main.py dados/pedidos_exemplo.csv --largura 500 800 1100 --refile 8

Veja `python main.py --help` para todas as opções.
"""

import argparse
import sys

from otimizador_corte import (
    Configuracao,
    formatar_resultado,
    ler_pedidos_csv,
    otimizar,
    salvar_plano_csv,
)


def main() -> int:
    ap = argparse.ArgumentParser(description="Otimizador de corte para rebobinadeira.")
    ap.add_argument("csv", help="arquivo CSV com colunas cliente,largura_mm,quantidade")
    ap.add_argument(
        "--largura",
        type=int,
        nargs="+",
        default=[500],
        help="largura(s) da bobina-mãe em mm; várias = o programa escolhe (ex.: 500 800 1100)",
    )
    ap.add_argument("--facas", type=int, default=17, help="número de facas da máquina")
    ap.add_argument(
        "--refile",
        type=int,
        default=0,
        help="refile mínimo por borda (mm); depende do ajuste das facas",
    )
    ap.add_argument(
        "--custo-troca",
        type=float,
        default=0.0,
        help="penalidade por padrão diferente, em bobinas (ex.: 0.5)",
    )
    ap.add_argument(
        "--excedente-max",
        type=float,
        default=None,
        help="excedente máximo por item, fração (ex.: 0.1 = 10%%)",
    )
    ap.add_argument(
        "--tempo-limite",
        type=float,
        default=30.0,
        help="tempo máximo do solver em segundos (com --custo-troca, use 120 para chegar ao ótimo)",
    )
    ap.add_argument(
        "--csv-saida",
        default=None,
        help="salva o plano de corte em CSV (abre direto no Excel)",
    )
    args = ap.parse_args()

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # acentos no terminal do Windows

    cfg = Configuracao(
        largura_bobina_mm=args.largura,
        facas=args.facas,
        refile_mm=args.refile,
        custo_troca=args.custo_troca,
        excedente_max=args.excedente_max,
        tempo_limite_s=args.tempo_limite,
    )
    try:
        pedidos = ler_pedidos_csv(args.csv)
        resultado = otimizar(pedidos, cfg)
    except (ValueError, RuntimeError, FileNotFoundError) as erro:
        # Mensagem curta para o usuário, sem o "traceback" do Python.
        print(f"Erro: {erro}", file=sys.stderr)
        return 1

    print(formatar_resultado(resultado, cfg))
    if args.csv_saida:
        salvar_plano_csv(resultado, args.csv_saida)
        print(f"\nPlano salvo em {args.csv_saida}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
