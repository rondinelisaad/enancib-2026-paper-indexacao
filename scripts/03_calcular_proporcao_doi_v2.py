#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Gera indicadores de proporção de DOI por ISSN e por periódico, a partir de
latindex_issn_encontrado_no_openalex.csv.

Entradas esperadas:
- latindex_issn_encontrado_no_openalex.csv

Saídas:
- doi_por_issn.csv
- doi_por_issn_ano.csv
- doi_por_periodico.csv
- doi_por_periodico_ano.csv
- doi_indicadores_estatisticas.txt

Uso:
    python3 calcular_proporcao_doi_v2.py \
        --input latindex_issn_encontrado_no_openalex.csv \
        --outdir saida_doi

Observações metodológicas:
- "por ISSN" mede a manifestação editorial.
- "por periódico" colapsa múltiplos ISSNs do mesmo periódico via folio_u.
- A deduplicação de artigos usa uma chave sintética baseada em DOI + título + ano.
- O numerador e o denominador são deduplicados com a MESMA chave por agrupamento.
- Como a base de entrada já é um subconjunto com match no OpenAlex, os indicadores
  refletem o recorte observado, não necessariamente o universo completo de artigos
  do periódico.
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
    "issn_norm",
    "tipo_issn",
    "ano",
    "doi_norm",
    "titulo",
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
        description="Calcula proporção de DOI por ISSN e por periódico."
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Arquivo latindex_issn_encontrado_no_openalex.csv",
    )
    parser.add_argument(
        "--outdir",
        default="saida_doi",
        help="Diretório de saída.",
    )
    parser.add_argument(
        "--encoding",
        default="utf-8",
        help="Encoding do CSV de entrada.",
    )
    parser.add_argument(
        "--sep",
        default=",",
        help="Separador do CSV de entrada.",
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
            logging.info("Lendo arquivo %s com encoding=%s sep=%r", path, enc, sep)
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


def prepare_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    for col in ["folio_u", "Revista", "Instituicao_editora", "issn_norm", "tipo_issn", "titulo"]:
        df[col] = df[col].apply(normalize_text)

    df["ano"] = pd.to_numeric(df["ano"], errors="coerce")
    df = df[df["ano"].notna()].copy()
    df["ano"] = df["ano"].astype(int)

    df["doi_clean"] = df["doi_norm"].fillna("").astype(str).str.strip()
    df["titulo_clean"] = df["titulo"].fillna("").astype(str).str.strip()

    # Flag no nível da linha
    df["tem_doi_linha"] = df["doi_clean"] != ""

    # Chave sintética do artigo no nível mais granular do ISSN
    df["artigo_id_issn"] = (
        df["doi_clean"] + "||" +
        df["titulo_clean"] + "||" +
        df["ano"].astype(str) + "||" +
        df["issn_norm"].fillna("").astype(str).str.strip()
    )

    # Chave sintética do artigo no nível periódico, para colapsar múltiplos ISSNs
    df["artigo_id_periodico"] = (
        df["doi_clean"] + "||" +
        df["titulo_clean"] + "||" +
        df["ano"].astype(str) + "||" +
        df["folio_u"].fillna("").astype(str).str.strip()
    )

    return df


def count_unique_with_doi(group: pd.DataFrame, article_id_col: str) -> int:
    """
    Conta artigos únicos com DOI dentro do agrupamento.
    O artigo é considerado 'com DOI' se qualquer linha daquele article_id tiver DOI.
    """
    by_article = group.groupby(article_id_col, dropna=False)["tem_doi_linha"].max()
    return int(by_article.sum())


def build_doi_por_issn(df: pd.DataFrame) -> pd.DataFrame:
    base = (
        df.groupby(["issn_norm", "tipo_issn"], dropna=False)
        .apply(
            lambda g: pd.Series({
                "total_artigos": g["artigo_id_issn"].nunique(),
                "artigos_com_doi": count_unique_with_doi(g, "artigo_id_issn"),
                "periodicos": g["folio_u"].nunique(),
                "revistas": "; ".join(sorted(set(v for v in g["Revista"].dropna() if v))),
            })
        )
        .reset_index()
    )

    base["proporcao_doi"] = (base["artigos_com_doi"] / base["total_artigos"]).round(4)
    return base.sort_values(["proporcao_doi", "total_artigos"], ascending=[False, False])


def build_doi_por_issn_ano(df: pd.DataFrame) -> pd.DataFrame:
    base = (
        df.groupby(["issn_norm", "tipo_issn", "ano"], dropna=False)
        .apply(
            lambda g: pd.Series({
                "total_artigos": g["artigo_id_issn"].nunique(),
                "artigos_com_doi": count_unique_with_doi(g, "artigo_id_issn"),
                "periodicos": g["folio_u"].nunique(),
                "revistas": "; ".join(sorted(set(v for v in g["Revista"].dropna() if v))),
            })
        )
        .reset_index()
    )

    base["proporcao_doi"] = (base["artigos_com_doi"] / base["total_artigos"]).round(4)
    return base.sort_values(["issn_norm", "ano"])


def build_doi_por_periodico(df: pd.DataFrame) -> pd.DataFrame:
    base = (
        df.groupby(["folio_u", "Revista", "Instituicao_editora"], dropna=False)
        .apply(
            lambda g: pd.Series({
                "total_artigos": g["artigo_id_periodico"].nunique(),
                "artigos_com_doi": count_unique_with_doi(g, "artigo_id_periodico"),
                "issns": "; ".join(sorted(set(v for v in g["issn_norm"].dropna() if v))),
                "tipos_issn": "; ".join(sorted(set(v for v in g["tipo_issn"].dropna() if v))),
            })
        )
        .reset_index()
    )

    base["proporcao_doi"] = (base["artigos_com_doi"] / base["total_artigos"]).round(4)
    return base.sort_values(["proporcao_doi", "total_artigos"], ascending=[False, False])


def build_doi_por_periodico_ano(df: pd.DataFrame) -> pd.DataFrame:
    base = (
        df.groupby(["folio_u", "Revista", "Instituicao_editora", "ano"], dropna=False)
        .apply(
            lambda g: pd.Series({
                "total_artigos": g["artigo_id_periodico"].nunique(),
                "artigos_com_doi": count_unique_with_doi(g, "artigo_id_periodico"),
                "issns": "; ".join(sorted(set(v for v in g["issn_norm"].dropna() if v))),
                "tipos_issn": "; ".join(sorted(set(v for v in g["tipo_issn"].dropna() if v))),
            })
        )
        .reset_index()
    )

    base["proporcao_doi"] = (base["artigos_com_doi"] / base["total_artigos"]).round(4)
    return base.sort_values(["folio_u", "ano"])


def build_stats_text(
    df: pd.DataFrame,
    doi_por_issn: pd.DataFrame,
    doi_por_issn_ano: pd.DataFrame,
    doi_por_periodico: pd.DataFrame,
    doi_por_periodico_ano: pd.DataFrame,
) -> str:
    total_linhas = len(df)
    total_issns = doi_por_issn["issn_norm"].nunique()
    total_periodicos = doi_por_periodico["folio_u"].nunique()
    total_artigos_issn = int(doi_por_issn["total_artigos"].sum())
    total_artigos_periodico = int(doi_por_periodico["total_artigos"].sum())

    media_issn = doi_por_issn["proporcao_doi"].mean().round(4) if not doi_por_issn.empty else 0
    media_periodico = doi_por_periodico["proporcao_doi"].mean().round(4) if not doi_por_periodico.empty else 0

    lines = [
        "=== ESTATÍSTICAS DOS INDICADORES DE DOI ===",
        "",
        f"Linhas lidas na base de entrada: {total_linhas}",
        f"ISSNs distintos analisados: {total_issns}",
        f"Periódicos distintos analisados: {total_periodicos}",
        "",
        f"Total agregado de artigos no nível ISSN: {total_artigos_issn}",
        f"Total agregado de artigos no nível periódico: {total_artigos_periodico}",
        "",
        f"Média da proporção DOI por ISSN: {media_issn}",
        f"Média da proporção DOI por periódico: {media_periodico}",
        "",
        f"Registros em doi_por_issn_ano.csv: {len(doi_por_issn_ano)}",
        f"Registros em doi_por_periodico_ano.csv: {len(doi_por_periodico_ano)}",
        "",
        "Cuidado analítico:",
        "- o numerador e o denominador agora são deduplicados com a mesma chave de artigo;",
        "- o indicador por ISSN mede a manifestação editorial;",
        "- o indicador por periódico colapsa ISSNs impresso, linking e eletrônico no mesmo título;",
        "- como a base de entrada já é um subconjunto com match no OpenAlex, a proporção DOI reflete esse recorte observado, não necessariamente o universo total de artigos da revista.",
    ]
    return "\n".join(lines)


def write_outputs(
    outdir: Path,
    doi_por_issn: pd.DataFrame,
    doi_por_issn_ano: pd.DataFrame,
    doi_por_periodico: pd.DataFrame,
    doi_por_periodico_ano: pd.DataFrame,
    stats_text: str,
) -> None:
    outdir.mkdir(parents=True, exist_ok=True)

    files = {
        "doi_por_issn.csv": doi_por_issn,
        "doi_por_issn_ano.csv": doi_por_issn_ano,
        "doi_por_periodico.csv": doi_por_periodico,
        "doi_por_periodico_ano.csv": doi_por_periodico_ano,
    }

    for filename, df_out in files.items():
        path = outdir / filename
        df_out.to_csv(path, index=False, encoding="utf-8-sig")
        logging.info("Arquivo gerado: %s", path)

    stats_path = outdir / "doi_indicadores_estatisticas.txt"
    stats_path.write_text(stats_text, encoding="utf-8")
    logging.info("Arquivo gerado: %s", stats_path)


def main() -> int:
    args = parse_args()
    setup_logging(args.verbose)

    try:
        df = read_csv_with_fallbacks(args.input, args.sep, args.encoding)
        ensure_columns(df, REQUIRED_COLUMNS)

        logging.info("Preparando dataframe...")
        df = prepare_dataframe(df)

        logging.info("Calculando DOI por ISSN...")
        doi_por_issn = build_doi_por_issn(df)

        logging.info("Calculando DOI por ISSN e ano...")
        doi_por_issn_ano = build_doi_por_issn_ano(df)

        logging.info("Calculando DOI por periódico...")
        doi_por_periodico = build_doi_por_periodico(df)

        logging.info("Calculando DOI por periódico e ano...")
        doi_por_periodico_ano = build_doi_por_periodico_ano(df)

        logging.info("Gerando estatísticas finais...")
        stats_text = build_stats_text(
            df,
            doi_por_issn,
            doi_por_issn_ano,
            doi_por_periodico,
            doi_por_periodico_ano,
        )

        write_outputs(
            Path(args.outdir),
            doi_por_issn,
            doi_por_issn_ano,
            doi_por_periodico,
            doi_por_periodico_ano,
            stats_text,
        )

        print(stats_text)
        print()
        print(f"Saídas gravadas em: {Path(args.outdir).resolve()}")
        return 0

    except Exception as exc:
        logging.exception("Erro durante a execução: %s", exc)
        print(f"ERRO: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
