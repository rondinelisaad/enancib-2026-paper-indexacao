#!/usr/bin/env python3
import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from statsmodels.stats.outliers_influence import variance_inflation_factor


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
        "total_artigos",
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
    df["total_artigos"] = pd.to_numeric(df["total_artigos"], errors="coerce")

    # Remover NAs críticos
    df = df.dropna(
        subset=[
            "proporcao_doi",
            "anos_com_indexacao",
            "lacuna_maxima",
            "total_artigos",
            "zona_bradford",
            "categoria_continuidade",
        ]
    ).copy()

    if df.empty:
        raise ValueError("Nenhuma observação válida restou após remoção de valores ausentes.")
    if (df["total_artigos"] <= 0).any():
        raise ValueError("total_artigos deve ser positivo para o ajuste por volume.")

    df["log_total_artigos"] = np.log1p(df["total_artigos"])

    # Correlações
    corr_anos = df["proporcao_doi"].corr(df["anos_com_indexacao"])
    corr_lacuna = df["proporcao_doi"].corr(df["lacuna_maxima"])

    report_parts = []

    report_parts.append("=== CORRELAÇÕES ===")
    report_parts.append(f"DOI × anos_com_indexacao: {corr_anos:.4f}")
    report_parts.append(f"DOI × lacuna_maxima: {corr_lacuna:.4f}")
    report_parts.append("")

    # Modelos comparáveis para avaliar o confundimento por volume
    zona = "C(zona_bradford, Treatment(reference='núcleo'))"
    report_parts.append("=== MODELO 1: anos_com_indexacao ~ DOI + Bradford ===")
    modelo1 = smf.ols(
        f"anos_com_indexacao ~ proporcao_doi + {zona}",
        data=df,
    ).fit()
    report_parts.append(str(modelo1.summary()))
    report_parts.append("")

    report_parts.append("=== MODELO 1A: anos_com_indexacao ~ DOI + log(volume) ===")
    modelo1a = smf.ols(
        "anos_com_indexacao ~ proporcao_doi + log_total_artigos",
        data=df,
    ).fit()
    report_parts.append(str(modelo1a.summary()))
    report_parts.append("")

    report_parts.append("=== MODELO 1B: anos_com_indexacao ~ DOI + Bradford + log(volume) ===")
    modelo1b = smf.ols(
        f"anos_com_indexacao ~ proporcao_doi + {zona} + log_total_artigos",
        data=df,
    ).fit()
    report_parts.append(str(modelo1b.summary()))
    report_parts.append("")

    zone_terms = [name for name in modelo1.params.index if name.startswith("C(zona_bradford")]
    comparison_rows = []
    for term in zone_terms:
        before = float(modelo1.params[term])
        after = float(modelo1b.params[term])
        attenuation = np.nan if before == 0 else 100 * (1 - abs(after) / abs(before))
        comparison_rows.append(
            {
                "termo": term,
                "coef_sem_volume": before,
                "p_sem_volume": float(modelo1.pvalues[term]),
                "coef_com_volume": after,
                "p_com_volume": float(modelo1b.pvalues[term]),
                "atenuacao_abs_pct": attenuation,
            }
        )
    comparison = pd.DataFrame(comparison_rows)
    report_parts.append("=== COMPARAÇÃO DOS COEFICIENTES DE BRADFORD: MODELO 1 × MODELO 1B ===")
    report_parts.append(comparison.to_string(index=False, float_format=lambda x: f"{x:.6f}"))
    report_parts.append("")

    vif_rows = []
    for index, name in enumerate(modelo1b.model.exog_names):
        if name == "Intercept":
            continue
        vif_rows.append(
            {
                "termo": name,
                "VIF": variance_inflation_factor(modelo1b.model.exog, index),
            }
        )
    vif = pd.DataFrame(vif_rows)
    report_parts.append("=== VIF DO MODELO 1B (INTERCEPTO OMITIDO) ===")
    report_parts.append(vif.to_string(index=False, float_format=lambda x: f"{x:.4f}"))
    report_parts.append("")

    f_volume, p_volume, df_volume = modelo1b.compare_f_test(modelo1)
    f_zone, p_zone, df_zone = modelo1b.compare_f_test(modelo1a)
    partial_r2_volume = (modelo1.ssr - modelo1b.ssr) / modelo1.ssr
    partial_r2_zone = (modelo1a.ssr - modelo1b.ssr) / modelo1a.ssr
    report_parts.append("=== TESTES DE CONTRIBUIÇÃO INCREMENTAL (MODELOS ANINHADOS) ===")
    report_parts.append(
        "log(volume) acrescentado ao modelo com Bradford: "
        f"F({int(df_volume)}, {int(modelo1b.df_resid)})={f_volume:.4f}; "
        f"p={p_volume:.6g}; R2 parcial={partial_r2_volume:.4f}"
    )
    report_parts.append(
        "Bradford acrescentado ao modelo com log(volume): "
        f"F({int(df_zone)}, {int(modelo1b.df_resid)})={f_zone:.4f}; "
        f"p={p_zone:.6g}; R2 parcial={partial_r2_zone:.4f}"
    )
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
