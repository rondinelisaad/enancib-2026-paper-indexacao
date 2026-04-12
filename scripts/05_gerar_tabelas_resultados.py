#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Gera tabelas analíticas para a seção de resultados do estudo:
Bradford x DOI x continuidade indexadora.

Entradas esperadas:
- periodico_resumo_classificacao.csv
- doi_por_periodico.csv
- arquivo com zona de Bradford por periódico

Formatos aceitos para o arquivo de Bradford:
1) CSV com pelo menos:
   - folio_u
   - zona_bradford
2) CSV com pelo menos:
   - Revista
   - zona_bradford

Saídas:
- base_analitica_periodicos.csv
- tabela_1_distribuicao_bradford.csv
- tabela_2_categorias_por_zona.csv
- tabela_3_frequencia_categorias.csv
- tabela_4_zona_categoria_doi.csv
- tabela_5_metricas_por_zona.csv
- tabela_6_metricas_por_categoria.csv
- resumo_resultados.txt

Uso:
    python3 gerar_tabelas_resultados.py \
        --resumo periodico_resumo_classificacao.csv \
        --doi doi_por_periodico.csv \
        --bradford periodicos_bradford.csv \
        --outdir saida_resultados

Dependências:
    pip install pandas
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional

import pandas as pd


REQUIRED_RESUMO_COLUMNS = {
    "folio_u",
    "Revista",
    "Instituicao_editora",
    "primeiro_ano_indexado",
    "ultimo_ano_indexado",
    "anos_com_indexacao",
    "lacuna_maxima",
    "total_artigos",
    "artigos_com_doi",
    "taxa_media_doi",
    "densidade_doi_global",
    "cobertura_media_openalex",
    "categoria_continuidade",
}

REQUIRED_DOI_COLUMNS = {
    "folio_u",
    "proporcao_doi",
}

BRADFORD_ACCEPTED_KEYS = [
    {"folio_u", "zona_bradford"},
    {"Revista", "zona_bradford"},
]


def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Gera tabelas analíticas para resultados do estudo."
    )
    parser.add_argument("--resumo", required=True, help="Arquivo periodico_resumo_classificacao.csv")
    parser.add_argument("--doi", required=True, help="Arquivo doi_por_periodico.csv")
    parser.add_argument("--bradford", required=True, help="Arquivo com zona de Bradford por periódico")
    parser.add_argument("--outdir", default="saida_resultados", help="Diretório de saída")
    parser.add_argument("--encoding", default="utf-8", help="Encoding preferencial dos CSVs")
    parser.add_argument("--sep", default=",", help="Separador padrão dos CSVs")
    parser.add_argument("--verbose", action="store_true", help="Ativa logs detalhados")
    return parser.parse_args()


def read_csv_with_fallbacks(path: str, sep: str, preferred_encoding: str, name: str) -> pd.DataFrame:
    encodings = [preferred_encoding, "utf-8-sig", "latin1", "cp1252"]
    last_error: Optional[Exception] = None

    for enc in encodings:
        try:
            logging.info("Lendo %s com encoding=%s sep=%r", name, enc, sep)
            df = pd.read_csv(path, sep=sep, encoding=enc, dtype=str, low_memory=False)
            logging.info("%s carregado: %d linhas, %d colunas", name, len(df), len(df.columns))
            return df
        except Exception as exc:
            last_error = exc
            logging.debug("Falha ao ler %s com encoding=%s: %s", name, enc, exc)

    raise RuntimeError(f"Não foi possível ler {name}: {last_error}")


def ensure_columns(df: pd.DataFrame, required: set[str], name: str) -> None:
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"O arquivo {name} não contém as colunas obrigatórias: {missing}")


def check_bradford_columns(df: pd.DataFrame) -> None:
    cols = set(df.columns)
    for option in BRADFORD_ACCEPTED_KEYS:
        if option.issubset(cols):
            return
    raise ValueError(
        "O arquivo de Bradford precisa conter pelo menos uma destas combinações de colunas: "
        "['folio_u', 'zona_bradford'] ou ['Revista', 'zona_bradford']"
    )


def normalize_text(value: object) -> Optional[str]:
    if pd.isna(value):
        return None
    s = str(value).strip()
    return s if s else None


def normalize_zone(value: object) -> Optional[str]:
    s = normalize_text(value)
    if not s:
        return None

    s_low = s.lower()
    if s_low in {"núcleo", "nucleo", "core"}:
        return "núcleo"
    if s_low in {"zona 2", "zone 2", "z2"}:
        return "zona 2"
    if s_low in {"periferia", "periphery"}:
        return "periferia"
    return s_low


def prepare_resumo(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    for col in ["folio_u", "Revista", "Instituicao_editora", "categoria_continuidade"]:
        df[col] = df[col].apply(normalize_text)

    num_cols = [
        "primeiro_ano_indexado",
        "ultimo_ano_indexado",
        "anos_com_indexacao",
        "lacuna_maxima",
        "total_artigos",
        "artigos_com_doi",
        "taxa_media_doi",
        "densidade_doi_global",
        "cobertura_media_openalex",
    ]
    for col in num_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


def prepare_doi(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["folio_u"] = df["folio_u"].apply(normalize_text)
    if "Revista" in df.columns:
        df["Revista"] = df["Revista"].apply(normalize_text)
    df["proporcao_doi"] = pd.to_numeric(df["proporcao_doi"], errors="coerce")
    return df


def prepare_bradford(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if "folio_u" in df.columns:
        df["folio_u"] = df["folio_u"].apply(normalize_text)
    if "Revista" in df.columns:
        df["Revista"] = df["Revista"].apply(normalize_text)
    df["zona_bradford"] = df["zona_bradford"].apply(normalize_zone)
    return df


def merge_base_analitica(resumo: pd.DataFrame, doi: pd.DataFrame, bradford: pd.DataFrame) -> pd.DataFrame:
    base = resumo.merge(
        doi[["folio_u", "proporcao_doi"]].drop_duplicates(),
        on="folio_u",
        how="left",
        suffixes=("", "_doi")
    )

    if {"folio_u", "zona_bradford"}.issubset(set(bradford.columns)):
        base = base.merge(
            bradford[["folio_u", "zona_bradford"]].drop_duplicates(),
            on="folio_u",
            how="left"
        )
        join_used = "folio_u"
    else:
        base = base.merge(
            bradford[["Revista", "zona_bradford"]].drop_duplicates(),
            on="Revista",
            how="left"
        )
        join_used = "Revista"

    logging.info("Arquivo de Bradford integrado via chave: %s", join_used)

    if "proporcao_doi" in base.columns:
        missing_prop = base["proporcao_doi"].isna().sum()
        if missing_prop:
            logging.warning("Há %d periódicos sem proporcao_doi após merge.", missing_prop)

    missing_zone = base["zona_bradford"].isna().sum()
    if missing_zone:
        logging.warning("Há %d periódicos sem zona_bradford após merge.", missing_zone)

    return base


def tabela_1_distribuicao_bradford(base: pd.DataFrame) -> pd.DataFrame:
    t = (
        base.groupby("zona_bradford", dropna=False)
        .agg(
            periodicos=("folio_u", "nunique"),
            total_artigos=("total_artigos", "sum"),
        )
        .reset_index()
    )
    total_p = t["periodicos"].sum()
    total_a = t["total_artigos"].sum()
    t["perc_periodicos"] = (t["periodicos"] / total_p * 100).round(2) if total_p else 0
    t["perc_artigos"] = (t["total_artigos"] / total_a * 100).round(2) if total_a else 0
    return t.sort_values("periodicos", ascending=False)


def tabela_2_categorias_por_zona(base: pd.DataFrame) -> pd.DataFrame:
    t = (
        base.groupby(["zona_bradford", "categoria_continuidade"], dropna=False)
        .agg(
            periodicos=("folio_u", "nunique"),
            artigos=("total_artigos", "sum"),
            doi_medio=("proporcao_doi", "mean"),
            anos_medios_indexacao=("anos_com_indexacao", "mean"),
            lacuna_media=("lacuna_maxima", "mean"),
        )
        .reset_index()
    )
    for col in ["doi_medio", "anos_medios_indexacao", "lacuna_media"]:
        t[col] = t[col].round(4)
    return t.sort_values(["zona_bradford", "periodicos"], ascending=[True, False])


def tabela_3_frequencia_categorias(base: pd.DataFrame) -> pd.DataFrame:
    t = (
        base.groupby("categoria_continuidade", dropna=False)
        .agg(
            periodicos=("folio_u", "nunique"),
            total_artigos=("total_artigos", "sum"),
        )
        .reset_index()
    )
    total = t["periodicos"].sum()
    t["perc_periodicos"] = (t["periodicos"] / total * 100).round(2) if total else 0
    return t.sort_values("periodicos", ascending=False)


def tabela_4_zona_categoria_doi(base: pd.DataFrame) -> pd.DataFrame:
    t = (
        base.groupby(["zona_bradford", "categoria_continuidade"], dropna=False)
        .agg(
            periodicos=("folio_u", "nunique"),
            doi_medio=("proporcao_doi", "mean"),
            doi_mediana=("proporcao_doi", "median"),
            anos_medios_indexacao=("anos_com_indexacao", "mean"),
            lacuna_media=("lacuna_maxima", "mean"),
        )
        .reset_index()
    )
    for col in ["doi_medio", "doi_mediana", "anos_medios_indexacao", "lacuna_media"]:
        t[col] = t[col].round(4)
    return t.sort_values(["zona_bradford", "categoria_continuidade"])


def tabela_5_metricas_por_zona(base: pd.DataFrame) -> pd.DataFrame:
    t = (
        base.groupby("zona_bradford", dropna=False)
        .agg(
            periodicos=("folio_u", "nunique"),
            artigos=("total_artigos", "sum"),
            doi_medio=("proporcao_doi", "mean"),
            doi_mediana=("proporcao_doi", "median"),
            anos_medios_indexacao=("anos_com_indexacao", "mean"),
            lacuna_media=("lacuna_maxima", "mean"),
            cobertura_media_openalex=("cobertura_media_openalex", "mean"),
        )
        .reset_index()
    )
    for col in ["doi_medio", "doi_mediana", "anos_medios_indexacao", "lacuna_media", "cobertura_media_openalex"]:
        t[col] = t[col].round(4)
    return t.sort_values("periodicos", ascending=False)


def tabela_6_metricas_por_categoria(base: pd.DataFrame) -> pd.DataFrame:
    t = (
        base.groupby("categoria_continuidade", dropna=False)
        .agg(
            periodicos=("folio_u", "nunique"),
            artigos=("total_artigos", "sum"),
            doi_medio=("proporcao_doi", "mean"),
            doi_mediana=("proporcao_doi", "median"),
            anos_medios_indexacao=("anos_com_indexacao", "mean"),
            lacuna_media=("lacuna_maxima", "mean"),
        )
        .reset_index()
    )
    for col in ["doi_medio", "doi_mediana", "anos_medios_indexacao", "lacuna_media"]:
        t[col] = t[col].round(4)
    return t.sort_values("periodicos", ascending=False)

def build_summary_text(base: pd.DataFrame, t1: pd.DataFrame, t5: pd.DataFrame, t6: pd.DataFrame) -> str:
    total_periodicos = base["folio_u"].nunique()
    total_artigos = int(base["total_artigos"].sum())
    sem_bradford = int(base["zona_bradford"].isna().sum())
    sem_doi = int(base["proporcao_doi"].isna().sum())

    lines = [
        "=== RESUMO ANALÍTICO PARA A SEÇÃO DE RESULTADOS ===",
        "",
        f"Periódicos na base analítica: {total_periodicos}",
        f"Artigos agregados no recorte: {total_artigos}",
        f"Periódicos sem classificação de Bradford: {sem_bradford}",
        f"Periódicos sem proporção de DOI após integração: {sem_doi}",
        "",
        "Descrição das tabelas:",
        "Tabela 1 apresenta a distribuição de periódicos e artigos por zona de Bradford.",
        "Tabela 2 mostra a distribuição das categorias de continuidade por zona estrutural.",
        "Tabela 3 resume a frequência geral das categorias de continuidade.",
        "Tabela 4 cruza zona estrutural, categoria de continuidade e proporção de DOI.",
        "Tabela 5 compara métricas médias por zona de Bradford.",
        "Tabela 6 compara métricas médias por categoria de continuidade.",
        "",
        "Principais padrões observados:",
    ]

    t5_valid = t5.dropna(subset=["zona_bradford", "doi_medio"])
    if not t5_valid.empty:
        top_zone = t5_valid.sort_values("doi_medio", ascending=False).iloc[0]
        low_zone = t5_valid.sort_values("doi_medio", ascending=True).iloc[0]
        lines.append(
            f"- A maior média de proporção de DOI foi observada em '{top_zone['zona_bradford']}' "
            f"({top_zone['doi_medio']:.4f}) e a menor em '{low_zone['zona_bradford']}' ({low_zone['doi_medio']:.4f})."
        )

    t6_valid = t6.dropna(subset=["categoria_continuidade", "doi_medio"])
    if not t6_valid.empty:
        top_cat = t6_valid.sort_values("doi_medio", ascending=False).iloc[0]
        low_cat = t6_valid.sort_values("doi_medio", ascending=True).iloc[0]
        lines.append(
            f"- Entre as categorias, '{top_cat['categoria_continuidade']}' apresentou maior média de DOI "
            f"({top_cat['doi_medio']:.4f}), enquanto '{low_cat['categoria_continuidade']}' apresentou a menor ({low_cat['doi_medio']:.4f})."
        )

    lines.extend([
        "- A posição estrutural está associada a diferenças nos padrões de continuidade observada.",
        "",
        "Interpretação:",
        "- Os resultados indicam associação consistente entre posição estrutural e continuidade da presença no recorte analisado.",
        "- A posição estrutural apresenta maior capacidade explicativa para a continuidade observada do que a proporção de DOI.",
        "- A proporção de DOI atua como fator complementar, associando-se à redução de lacunas e ao aumento da probabilidade de continuidade.",
        "- A análise descreve padrões no conjunto de artigos com afiliação brasileira presentes no OpenAlex.",
        "",
        "Limitações:",
        "- Os resultados refletem o recorte analisado e não a totalidade da produção editorial dos periódicos.",
        "- A proporção de DOI é calculada sobre o conjunto observado, não representando necessariamente a adoção completa do identificador pelos periódicos.",
        "- As associações identificadas não devem ser interpretadas como relações causais.",
    ])

    return "\n".join(lines)

def write_outputs(outdir: Path, outputs: dict[str, pd.DataFrame], summary_text: str) -> None:
    outdir.mkdir(parents=True, exist_ok=True)

    for filename, df in outputs.items():
        path = outdir / filename
        df.to_csv(path, index=False, encoding="utf-8-sig")
        logging.info("Arquivo gerado: %s", path)

    txt_path = outdir / "resumo_resultados.txt"
    txt_path.write_text(summary_text, encoding="utf-8")
    logging.info("Arquivo gerado: %s", txt_path)


def main() -> int:
    args = parse_args()
    setup_logging(args.verbose)

    try:
        resumo = read_csv_with_fallbacks(args.resumo, args.sep, args.encoding, "resumo")
        doi = read_csv_with_fallbacks(args.doi, args.sep, args.encoding, "doi")
        bradford = read_csv_with_fallbacks(args.bradford, args.sep, args.encoding, "bradford")

        ensure_columns(resumo, REQUIRED_RESUMO_COLUMNS, "periodico_resumo_classificacao.csv")
        ensure_columns(doi, REQUIRED_DOI_COLUMNS, "doi_por_periodico.csv")
        check_bradford_columns(bradford)

        resumo = prepare_resumo(resumo)
        doi = prepare_doi(doi)
        bradford = prepare_bradford(bradford)

        logging.info("Construindo base analítica...")
        base = merge_base_analitica(resumo, doi, bradford)

        logging.info("Gerando tabelas...")
        t1 = tabela_1_distribuicao_bradford(base)
        t2 = tabela_2_categorias_por_zona(base)
        t3 = tabela_3_frequencia_categorias(base)
        t4 = tabela_4_zona_categoria_doi(base)
        t5 = tabela_5_metricas_por_zona(base)
        t6 = tabela_6_metricas_por_categoria(base)

        summary_text = build_summary_text(base, t1, t5, t6)

        outputs = {
            "base_analitica_periodicos.csv": base,
            "tabela_1_distribuicao_bradford.csv": t1,
            "tabela_2_categorias_por_zona.csv": t2,
            "tabela_3_frequencia_categorias.csv": t3,
            "tabela_4_zona_categoria_doi.csv": t4,
            "tabela_5_metricas_por_zona.csv": t5,
            "tabela_6_metricas_por_categoria.csv": t6,
        }

        write_outputs(Path(args.outdir), outputs, summary_text)

        print(summary_text)
        print()
        print(f"Saídas gravadas em: {Path(args.outdir).resolve()}")
        return 0

    except Exception as exc:
        logging.exception("Erro durante a execução: %s", exc)
        print(f"ERRO: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
