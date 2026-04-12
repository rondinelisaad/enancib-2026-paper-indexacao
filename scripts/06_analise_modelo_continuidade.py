#!/usr/bin/env python3
import argparse
from pathlib import Path

import pandas as pd
import statsmodels.formula.api as smf


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Executa correlações e modelos de continuidade a partir da base analítica."
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Caminho para o arquivo base_analitica_periodicos.csv",
    )
    parser.add_argument(
        "--output",
        required=False,
        help="Caminho opcional para salvar o relatório textual dos modelos",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.is_file():
        raise FileNotFoundError(f"Arquivo de entrada não encontrado: {input_path}")

    df = pd.read_csv(input_path)

    required_cols = [
        "proporcao_doi",
        "anos_com_indexacao",
        "lacuna_maxima",
        "zona_bradford",
        "categoria_continuidade",
    ]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Colunas obrigatórias ausentes: {missing}")

    # Garantir tipos
    df["proporcao_doi"] = pd.to_numeric(df["proporcao_doi"], errors="coerce")
    df["anos_com_indexacao"] = pd.to_numeric(df["anos_com_indexacao"], errors="coerce")
    df["lacuna_maxima"] = pd.to_numeric(df["lacuna_maxima"], errors="coerce")

    # Remover NAs críticos
    df = df.dropna(
        subset=[
            "proporcao_doi",
            "anos_com_indexacao",
            "lacuna_maxima",
            "zona_bradford",
            "categoria_continuidade",
        ]
    ).copy()

    if df.empty:
        raise ValueError("Nenhuma observação válida restou após remoção de valores ausentes.")

    # Correlações
    corr_anos = df["proporcao_doi"].corr(df["anos_com_indexacao"])
    corr_lacuna = df["proporcao_doi"].corr(df["lacuna_maxima"])

    report_parts = []

    report_parts.append("=== CORRELAÇÕES ===")
    report_parts.append(f"DOI × anos_com_indexacao: {corr_anos:.4f}")
    report_parts.append(f"DOI × lacuna_maxima: {corr_lacuna:.4f}")
    report_parts.append("")

    # Modelo 1
    report_parts.append("=== MODELO 1: anos_com_indexacao ~ DOI + Bradford ===")
    modelo1 = smf.ols(
        "anos_com_indexacao ~ proporcao_doi + C(zona_bradford)",
        data=df,
    ).fit()
    report_parts.append(str(modelo1.summary()))
    report_parts.append("")

    # Modelo 2
    report_parts.append("=== MODELO 2: lacuna_maxima ~ DOI + Bradford ===")
    modelo2 = smf.ols(
        "lacuna_maxima ~ proporcao_doi + C(zona_bradford)",
        data=df,
    ).fit()
    report_parts.append(str(modelo2.summary()))
    report_parts.append("")

    # Modelo 3
    report_parts.append("=== MODELO 3: probabilidade de ser CONTINUANTE ===")
    df["is_continuante"] = (df["categoria_continuidade"] == "continuante").astype(int)

    modelo3 = smf.logit(
        "is_continuante ~ proporcao_doi + C(zona_bradford)",
        data=df,
    ).fit()
    report_parts.append(str(modelo3.summary()))
    report_parts.append("")

    report = "\n".join(report_parts)

    print(report)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(report, encoding="utf-8")
        print(f"\nRelatório salvo em: {output_path}")


if __name__ == "__main__":
    main()
