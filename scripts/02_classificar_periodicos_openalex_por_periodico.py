#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Gera indicadores periódico-ano e classificação de continuidade indexadora
a partir de latindex_issn_encontrado_no_openalex.csv, usando o PERIÓDICO
como unidade analítica (folio_u), e não cada ISSN separadamente.

Entrada esperada:
- latindex_issn_encontrado_no_openalex.csv

Saídas:
- periodico_ano_indicadores.csv
- periodico_resumo_classificacao.csv
- categoria_resumo.csv
- classificacao_estatisticas.txt

Uso:
    python3 classificar_periodicos_openalex_por_periodico.py \
        --input latindex_issn_encontrado_no_openalex.csv \
        --outdir saida_classificacao

Observações metodológicas:
- A unidade de análise é o periódico (folio_u).
- ISSNs impresso, eletrônico e linking são tratados como atributos do mesmo periódico.
- O script deduplica artigos por periódico-ano com base em um artigo_id sintético.
- Como a base de entrada já é o subconjunto que bateu com OpenAlex, a variável
  cobertura_openalex_br é cobertura interna do recorte cruzado, não cobertura
  real frente ao universo completo de artigos do periódico.
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
    "journal_title",
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
        description="Gera base periódico-ano e classificação de continuidade indexadora por periódico."
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Arquivo latindex_issn_encontrado_no_openalex.csv",
    )
    parser.add_argument(
        "--outdir",
        default="saida_classificacao",
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
        "--continuante-min-anos",
        type=int,
        default=8,
        help="Mínimo de anos com indexação para classificar como continuante.",
    )
    parser.add_argument(
        "--continuante-ano-recente",
        type=int,
        default=2023,
        help="Ano mínimo do último ano indexado para classificar como continuante.",
    )
    parser.add_argument(
        "--retirante-ano-max",
        type=int,
        default=2018,
        help="Último ano indexado máximo para classificar como retirante.",
    )
    parser.add_argument(
        "--entrante-ano-min",
        type=int,
        default=2020,
        help="Primeiro ano indexado mínimo para classificar como entrante.",
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

    for col in [
        "folio_u",
        "Revista",
        "Instituicao_editora",
        "issn_norm",
        "tipo_issn",
        "titulo",
        "journal_title",
    ]:
        df[col] = df[col].apply(normalize_text)

    df["ano"] = pd.to_numeric(df["ano"], errors="coerce")
    df = df[df["ano"].notna()].copy()
    df["ano"] = df["ano"].astype(int)

    df["tem_doi"] = df["doi_norm"].notna() & (df["doi_norm"].astype(str).str.strip() != "")

    # ID sintético para deduplicar artigos repetidos por múltiplos ISSNs do mesmo periódico.
    # Inclui doi quando disponível e cai para combinação de título+ano.
    df["artigo_id_base"] = (
        df["doi_norm"].fillna("").astype(str).str.strip() + "||" +
        df["titulo"].fillna("").astype(str).str.strip() + "||" +
        df["ano"].astype(str)
    )

    return df


def build_periodico_ano(df: pd.DataFrame) -> pd.DataFrame:
    """
    Base periódico-ano no nível folio_u + ano.
    ISSNs múltiplos do mesmo periódico são colapsados.
    """
    grouped = (
        df.groupby(
            ["folio_u", "Revista", "Instituicao_editora", "ano"],
            dropna=False,
        )
        .agg(
            total_artigos=("artigo_id_base", "nunique"),
            artigos_com_doi=("tem_doi", "sum"),
            artigos_presentes_openalex_br=("artigo_id_base", "nunique"),
            issns_do_periodico=("issn_norm", lambda x: "; ".join(sorted(set(v for v in x.dropna() if v)))),
            tipos_issn_presentes=("tipo_issn", lambda x: "; ".join(sorted(set(v for v in x.dropna() if v)))),
            titulos_openalex=("journal_title", lambda x: "; ".join(sorted(set(v for v in x.dropna() if v)))),
        )
        .reset_index()
    )

    grouped["taxa_doi"] = (
        grouped["artigos_com_doi"] / grouped["total_artigos"]
    ).round(4)

    grouped["cobertura_openalex_br"] = (
        grouped["artigos_presentes_openalex_br"] / grouped["total_artigos"]
    ).round(4)

    return grouped


def max_gap(years: list[int]) -> int:
    years = sorted(set(years))
    if len(years) <= 1:
        return 0

    gaps = []
    for prev, curr in zip(years[:-1], years[1:]):
        gaps.append(curr - prev - 1)

    return max(gaps) if gaps else 0


def classify_periodico(
    primeiro_ano: int,
    ultimo_ano: int,
    anos_com_indexacao: int,
    retirante_ano_max: int,
    entrante_ano_min: int,
    continuante_min_anos: int,
    continuante_ano_recente: int,
) -> str:
    if anos_com_indexacao == 1:
        return "one-timer"

    if ultimo_ano <= retirante_ano_max:
        return "retirante"

    if primeiro_ano >= entrante_ano_min:
        return "entrante"

    if anos_com_indexacao >= continuante_min_anos and ultimo_ano >= continuante_ano_recente:
        return "continuante"

    return "transiente"


def build_periodico_resumo(periodico_ano: pd.DataFrame, df_original: pd.DataFrame, args: argparse.Namespace) -> pd.DataFrame:
    resumo = (
        periodico_ano.groupby(
            ["folio_u", "Revista", "Instituicao_editora"],
            dropna=False,
        )
        .agg(
            primeiro_ano_indexado=("ano", "min"),
            ultimo_ano_indexado=("ano", "max"),
            anos_com_indexacao=("ano", "nunique"),
            total_artigos=("total_artigos", "sum"),
            artigos_com_doi=("artigos_com_doi", "sum"),
            cobertura_media_openalex=("cobertura_openalex_br", "mean"),
            taxa_media_doi=("taxa_doi", "mean"),
        )
        .reset_index()
    )

    years_per_periodico = (
        periodico_ano.groupby(
            ["folio_u", "Revista", "Instituicao_editora"],
            dropna=False,
        )["ano"]
        .apply(lambda x: sorted(set(int(v) for v in x.dropna())))
        .reset_index(name="anos_indexados_lista")
    )

    issn_attr = (
        df_original.groupby(
            ["folio_u", "Revista", "Instituicao_editora"],
            dropna=False,
        )
        .agg(
            issns=("issn_norm", lambda x: "; ".join(sorted(set(v for v in x.dropna() if v)))),
            tipos_issn=("tipo_issn", lambda x: "; ".join(sorted(set(v for v in x.dropna() if v)))),
            titulos_openalex=("journal_title", lambda x: "; ".join(sorted(set(v for v in x.dropna() if v)))),
        )
        .reset_index()
    )

    resumo = resumo.merge(
        years_per_periodico,
        on=["folio_u", "Revista", "Instituicao_editora"],
        how="left",
    ).merge(
        issn_attr,
        on=["folio_u", "Revista", "Instituicao_editora"],
        how="left",
    )

    resumo["lacuna_maxima"] = resumo["anos_indexados_lista"].apply(max_gap)
    resumo["taxa_media_doi"] = resumo["taxa_media_doi"].round(4)
    resumo["cobertura_media_openalex"] = resumo["cobertura_media_openalex"].round(4)
    resumo["densidade_doi_global"] = (
        resumo["artigos_com_doi"] / resumo["total_artigos"]
    ).round(4)

    resumo["categoria_continuidade"] = resumo.apply(
        lambda row: classify_periodico(
            primeiro_ano=int(row["primeiro_ano_indexado"]),
            ultimo_ano=int(row["ultimo_ano_indexado"]),
            anos_com_indexacao=int(row["anos_com_indexacao"]),
            retirante_ano_max=args.retirante_ano_max,
            entrante_ano_min=args.entrante_ano_min,
            continuante_min_anos=args.continuante_min_anos,
            continuante_ano_recente=args.continuante_ano_recente,
        ),
        axis=1,
    )

    resumo["anos_indexados"] = resumo["anos_indexados_lista"].apply(
        lambda years: "; ".join(str(y) for y in years) if isinstance(years, list) else ""
    )
    resumo = resumo.drop(columns=["anos_indexados_lista"])

    ordered_cols = [
        "folio_u",
        "Revista",
        "Instituicao_editora",
        "issns",
        "tipos_issn",
        "titulos_openalex",
        "primeiro_ano_indexado",
        "ultimo_ano_indexado",
        "anos_com_indexacao",
        "anos_indexados",
        "lacuna_maxima",
        "total_artigos",
        "artigos_com_doi",
        "taxa_media_doi",
        "densidade_doi_global",
        "cobertura_media_openalex",
        "categoria_continuidade",
    ]
    resumo = resumo[ordered_cols]

    return resumo.sort_values(
        ["categoria_continuidade", "anos_com_indexacao", "total_artigos"],
        ascending=[True, False, False]
    )


def build_categoria_resumo(periodico_resumo: pd.DataFrame) -> pd.DataFrame:
    categoria_resumo = (
        periodico_resumo.groupby("categoria_continuidade", dropna=False)
        .agg(
            periodicos=("folio_u", "nunique"),
            total_artigos=("total_artigos", "sum"),
            media_taxa_doi=("taxa_media_doi", "mean"),
            media_densidade_doi_global=("densidade_doi_global", "mean"),
            media_cobertura_openalex=("cobertura_media_openalex", "mean"),
            media_lacuna_maxima=("lacuna_maxima", "mean"),
            media_anos_com_indexacao=("anos_com_indexacao", "mean"),
        )
        .reset_index()
    )

    for col in [
        "media_taxa_doi",
        "media_densidade_doi_global",
        "media_cobertura_openalex",
        "media_lacuna_maxima",
        "media_anos_com_indexacao",
    ]:
        categoria_resumo[col] = categoria_resumo[col].round(4)

    return categoria_resumo.sort_values("periodicos", ascending=False)

def build_stats_text(
    periodico_ano: pd.DataFrame,
    periodico_resumo: pd.DataFrame,
    categoria_resumo: pd.DataFrame,
    args: argparse.Namespace,
) -> str:
    total_periodicos = periodico_resumo["folio_u"].nunique()
    total_periodico_ano = len(periodico_ano)
    total_artigos = int(periodico_resumo["total_artigos"].sum())

    counts = {
        row["categoria_continuidade"]: int(row["periodicos"])
        for _, row in categoria_resumo.iterrows()
    }

    n_cont = counts.get("continuante", 0)
    n_trans = counts.get("transiente", 0)
    n_ent = counts.get("entrante", 0)
    n_ret = counts.get("retirante", 0)
    n_one = counts.get("one-timer", 0)

    lines = [
        "=== ESTATÍSTICAS DA CLASSIFICAÇÃO ===",
        "",
        f"Total de registros periódico-ano: {total_periodico_ano}",
        f"Total de periódicos analisados: {total_periodicos}",
        f"Total de artigos agregados no recorte: {total_artigos}",
        "",
        "Parâmetros de classificação:",
        "- unidade analítica: periódico (folio_u)",
        "- ISSNs múltiplos foram agregados no nível do periódico",
        "- one-timer: anos_com_indexacao = 1",
        "- retirante: ultimo_ano_indexado <= 2018",
        "- entrante: primeiro_ano_indexado >= 2020",
        "- continuante: anos_com_indexacao >= 8 e ultimo_ano_indexado >= 2023",
        "- transiente: demais casos",
        "",
        "Distribuição por categoria:",
        f"- continuante: {n_cont}",
        f"- transiente: {n_trans}",
        f"- entrante: {n_ent}",
        f"- retirante: {n_ret}",
        f"- one-timer: {n_one}",
        "",
        "Interpretação:",
        "- A classificação descreve padrões de continuidade da presença de periódicos no conjunto de artigos com afiliação brasileira presentes no OpenAlex.",
        "- A ausência ou descontinuidade observada refere-se ao recorte analisado e não implica necessariamente interrupção da atividade editorial do periódico.",
        "- Os resultados devem ser interpretados como indicadores de continuidade observada no sistema de indexação considerado.",
    ]
    return "\n".join(lines)


def write_outputs(
    outdir: Path,
    periodico_ano: pd.DataFrame,
    periodico_resumo: pd.DataFrame,
    categoria_resumo: pd.DataFrame,
    stats_text: str,
) -> None:
    outdir.mkdir(parents=True, exist_ok=True)

    files = {
        "periodico_ano_indicadores.csv": periodico_ano,
        "periodico_resumo_classificacao.csv": periodico_resumo,
        "categoria_resumo.csv": categoria_resumo,
    }

    for filename, df in files.items():
        path = outdir / filename
        df.to_csv(path, index=False, encoding="utf-8-sig")
        logging.info("Arquivo gerado: %s", path)

    stats_path = outdir / "classificacao_estatisticas.txt"
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

        logging.info("Construindo base periódico-ano...")
        periodico_ano = build_periodico_ano(df)

        logging.info("Agregando resumo por periódico...")
        periodico_resumo = build_periodico_resumo(periodico_ano, df, args)

        logging.info("Agregando resumo por categoria...")
        categoria_resumo = build_categoria_resumo(periodico_resumo)

        logging.info("Gerando estatísticas finais...")
        stats_text = build_stats_text(periodico_ano, periodico_resumo, categoria_resumo, args)

        write_outputs(Path(args.outdir), periodico_ano, periodico_resumo, categoria_resumo, stats_text)

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
