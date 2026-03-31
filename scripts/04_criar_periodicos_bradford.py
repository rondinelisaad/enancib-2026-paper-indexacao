#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Cria periodicos_bradford.csv a partir de periodico_resumo_classificacao.csv.

Lógica:
- ordena os periódicos por total_artigos (decrescente)
- calcula o acumulado de artigos
- divide o total acumulado em 3 partes aproximadamente iguais
- classifica os periódicos em:
  - núcleo
  - zona 2
  - periferia

Entrada esperada:
- periodico_resumo_classificacao.csv

Saídas:
- periodicos_bradford.csv
- bradford_resumo.txt

Uso:
    python3 criar_periodicos_bradford.py \
        --input periodico_resumo_classificacao.csv \
        --outdir saida_bradford
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional

import pandas as pd


REQUIRED_COLUMNS = {
    "folio_u",
    "Revista",
    "Instituicao_editora",
    "total_artigos",
}


def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Cria classificação de Bradford por periódico."
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Arquivo periodico_resumo_classificacao.csv",
    )
    parser.add_argument(
        "--outdir",
        default="saida_bradford",
        help="Diretório de saída.",
    )
    parser.add_argument(
        "--encoding",
        default="utf-8",
        help="Encoding preferencial.",
    )
    parser.add_argument(
        "--sep",
        default=",",
        help="Separador do CSV.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Ativa logs detalhados.",
    )
    return parser.parse_args()


def read_csv_with_fallbacks(path: str, sep: str, preferred_encoding: str) -> pd.DataFrame:
    encodings = [preferred_encoding, "utf-8-sig", "latin1", "cp1252"]
    last_error: Optional[Exception] = None

    for enc in encodings:
        try:
            logging.info("Lendo %s com encoding=%s sep=%r", path, enc, sep)
            df = pd.read_csv(path, sep=sep, encoding=enc, dtype=str, low_memory=False)
            logging.info("Arquivo carregado: %d linhas, %d colunas", len(df), len(df.columns))
            return df
        except Exception as exc:
            last_error = exc
            logging.debug("Falha ao ler com encoding=%s: %s", enc, exc)

    raise RuntimeError(f"Não foi possível ler o arquivo: {last_error}")


def ensure_columns(df: pd.DataFrame, required: set[str]) -> None:
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"Colunas obrigatórias ausentes: {missing}")


def normalize_text(value: object) -> Optional[str]:
    if pd.isna(value):
        return None
    s = str(value).strip()
    return s if s else None


def preparar_base(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    for col in ["folio_u", "Revista", "Instituicao_editora"]:
        df[col] = df[col].apply(normalize_text)

    df["total_artigos"] = pd.to_numeric(df["total_artigos"], errors="coerce")
    df = df[df["total_artigos"].notna()].copy()
    df["total_artigos"] = df["total_artigos"].astype(int)

    # Segurança: um periódico por folio_u
    df = (
        df.sort_values(["total_artigos", "Revista"], ascending=[False, True])
          .drop_duplicates(subset=["folio_u"], keep="first")
          .copy()
    )

    return df


def classificar_bradford(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values(["total_artigos", "folio_u"], ascending=[False, True]).reset_index(drop=True)

    total_artigos = df["total_artigos"].sum()
    if total_artigos == 0:
        raise ValueError("A soma de total_artigos é zero. Não é possível calcular as zonas de Bradford.")

    tercio = total_artigos / 3.0

    df["rank_bradford"] = range(1, len(df) + 1)
    df["artigos_acumulados"] = df["total_artigos"].cumsum()
    df["perc_acumulado_artigos"] = (df["artigos_acumulados"] / total_artigos * 100).round(4)

    def zona(acumulado: float) -> str:
        if acumulado <= tercio:
            return "núcleo"
        if acumulado <= 2 * tercio:
            return "zona 2"
        return "periferia"

    df["zona_bradford"] = df["artigos_acumulados"].apply(zona)

    return df


def gerar_resumo(bradford: pd.DataFrame) -> str:
    total_periodicos = bradford["folio_u"].nunique()
    total_artigos = int(bradford["total_artigos"].sum())

    resumo_zonas = (
        bradford.groupby("zona_bradford", dropna=False)
        .agg(
            periodicos=("folio_u", "nunique"),
            artigos=("total_artigos", "sum"),
        )
        .reset_index()
    )

    linhas = [
        "=== RESUMO DA CLASSIFICAÇÃO DE BRADFORD ===",
        "",
        f"Periódicos classificados: {total_periodicos}",
        f"Total de artigos considerados: {total_artigos}",
        "",
        "Distribuição por zona:",
    ]

    for _, row in resumo_zonas.iterrows():
        linhas.append(
            f"- {row['zona_bradford']}: {int(row['periodicos'])} periódicos, {int(row['artigos'])} artigos"
        )

    linhas.extend([
        "",
        "Critério utilizado:",
        "- periódicos ordenados por total_artigos em ordem decrescente;",
        "- acumulado de artigos dividido em três partes aproximadamente iguais;",
        "- classificação resultante: núcleo, zona 2 e periferia.",
        "",
        "Cuidado analítico:",
        "- esta implementação operacionaliza Bradford por terços do total acumulado de artigos;",
        "- dependendo do desenho do artigo, você pode querer testar sensibilidade dessa divisão.",
    ])

    return "\n".join(linhas)


def write_outputs(outdir: Path, bradford: pd.DataFrame, resumo: str) -> None:
    outdir.mkdir(parents=True, exist_ok=True)

    output_cols = [
        "folio_u",
        "Revista",
        "Instituicao_editora",
        "total_artigos",
        "rank_bradford",
        "artigos_acumulados",
        "perc_acumulado_artigos",
        "zona_bradford",
    ]

    csv_path = outdir / "periodicos_bradford.csv"
    bradford[output_cols].to_csv(csv_path, index=False, encoding="utf-8-sig")
    logging.info("Arquivo gerado: %s", csv_path)

    txt_path = outdir / "bradford_resumo.txt"
    txt_path.write_text(resumo, encoding="utf-8")
    logging.info("Arquivo gerado: %s", txt_path)


def main() -> int:
    args = parse_args()
    setup_logging(args.verbose)

    try:
        df = read_csv_with_fallbacks(args.input, args.sep, args.encoding)
        ensure_columns(df, REQUIRED_COLUMNS)

        logging.info("Preparando base...")
        df = preparar_base(df)

        logging.info("Classificando zonas de Bradford...")
        bradford = classificar_bradford(df)

        resumo = gerar_resumo(bradford)

        write_outputs(Path(args.outdir), bradford, resumo)

        print(resumo)
        print()
        print(f"Saídas gravadas em: {Path(args.outdir).resolve()}")
        return 0

    except Exception as exc:
        logging.exception("Erro durante a execução: %s", exc)
        print(f"ERRO: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
