#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Compara ISSNs entre:
1) openalex_BR_2000_2024_tratado.csv
2) latindex-journals-brasileiros.csv

Saídas:
- latindex_issn_encontrado_no_openalex.csv
- latindex_issn_nao_encontrado_no_openalex.csv
- latindex_revistas_relacao_openalex.csv
- latindex_cobertura_por_revista.csv
- latindex_estatisticas.txt

Uso:
    python3 comparar_issn_latindex_openalex.py \
        --openalex openalex_BR_2000_2024_tratado.csv \
        --latindex latindex-journals-brasileiros.csv \
        --outdir saida_comparacao

Dependências:
    pip install pandas
"""

from __future__ import annotations

import argparse
import ast
import logging
import re
import sys
from pathlib import Path
from typing import Optional

import pandas as pd


OPENALEX_REQUIRED_COLUMNS = {
    "titulo",
    "ano",
    "journal_title",
    "issn_l",
    "issn",
    "doi_norm",
}

LATINDEX_REQUIRED_COLUMNS = {
    "folio_u",
    "tit_propio",
    "nombre_edi",
    "issn_e",
    "issn_l",
    "issn_imp",
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
        description="Compara ISSNs da base Latindex com ISSNs presentes na base OpenAlex."
    )
    parser.add_argument("--openalex", required=True, help="Caminho do CSV do OpenAlex.")
    parser.add_argument("--latindex", required=True, help="Caminho do CSV do Latindex.")
    parser.add_argument(
        "--outdir",
        default="saida_comparacao_issn",
        help="Diretório de saída para os relatórios.",
    )
    parser.add_argument(
        "--encoding-openalex",
        default="utf-8",
        help="Encoding do CSV OpenAlex (default: utf-8).",
    )
    parser.add_argument(
        "--encoding-latindex",
        default="utf-8",
        help="Encoding do CSV Latindex (default: utf-8).",
    )
    parser.add_argument(
        "--sep-openalex",
        default=",",
        help="Separador do CSV OpenAlex (default: ,).",
    )
    parser.add_argument(
        "--sep-latindex",
        default=";",
        help="Separador do CSV Latindex (default: ;).",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Ativa logs em nível DEBUG.",
    )
    return parser.parse_args()


def normalize_issn(value: object) -> Optional[str]:
    """
    Normaliza ISSN para o formato ####-####.
    Remove caracteres não alfanuméricos, preservando X.
    Retorna None para vazio ou formato inválido.
    """
    if pd.isna(value):
        return None

    s = str(value).strip().upper()
    if not s or s in {"[]", "NAN", "NONE", "NULL"}:
        return None

    s = re.sub(r"[^0-9X]", "", s)
    if len(s) != 8:
        return None

    return f"{s[:4]}-{s[4:]}"


def parse_openalex_issn_list(value: object) -> list[str]:
    """
    Campo 'issn' do OpenAlex costuma vir como string serializada de lista.
    Ex.: '["1415-6555", "1982-7849"]'
    """
    if pd.isna(value):
        return []

    s = str(value).strip()
    if not s or s in {"[]", "nan", "None"}:
        return []

    try:
        parsed = ast.literal_eval(s)
    except (ValueError, SyntaxError):
        logging.debug("Falha ao converter lista de ISSNs do OpenAlex: %r", s)
        return []

    if not isinstance(parsed, list):
        return []

    normalized = []
    for item in parsed:
        issn = normalize_issn(item)
        if issn:
            normalized.append(issn)
    return normalized


def ensure_columns(df: pd.DataFrame, required: set[str], df_name: str) -> None:
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(
            f"O arquivo {df_name} não contém as colunas obrigatórias: {missing}"
        )


def read_csv_with_fallbacks(
    path: str,
    sep: str,
    preferred_encoding: str,
    name: str,
) -> pd.DataFrame:
    encodings_to_try = [preferred_encoding, "utf-8-sig", "latin1", "cp1252"]
    last_error: Optional[Exception] = None

    for enc in encodings_to_try:
        try:
            logging.info("Lendo %s com encoding=%s sep=%r", name, enc, sep)
            df = pd.read_csv(path, sep=sep, encoding=enc, dtype=str, low_memory=False)
            logging.info("%s carregado com %d linhas e %d colunas", name, len(df), len(df.columns))
            return df
        except Exception as exc:
            last_error = exc
            logging.debug("Falha ao ler %s com encoding=%s: %s", name, enc, exc)

    raise RuntimeError(f"Não foi possível ler {name}: {last_error}")


def build_openalex_issn_expanded(openalex: pd.DataFrame) -> pd.DataFrame:
    openalex = openalex.copy()

    openalex["issn_l_norm"] = openalex["issn_l"].apply(normalize_issn)
    openalex["issn_list_norm"] = openalex["issn"].apply(parse_openalex_issn_list)

    rows: list[dict[str, object]] = []

    for _, row in openalex.iterrows():
        issns = set()

        issn_l = row.get("issn_l_norm")
        if pd.notna(issn_l) and issn_l:
            issns.add(issn_l)

        issn_list = row.get("issn_list_norm", [])
        if isinstance(issn_list, list):
            for item in issn_list:
                if item:
                    issns.add(item)

        for issn in issns:
            rows.append(
                {
                    "issn_norm": issn,
                    "titulo": row.get("titulo"),
                    "ano": row.get("ano"),
                    "journal_title": row.get("journal_title"),
                    "doi_norm": row.get("doi_norm"),
                }
            )

    expanded = pd.DataFrame(rows).drop_duplicates()

    if expanded.empty:
        logging.warning("A expansão de ISSNs do OpenAlex resultou em DataFrame vazio.")
    else:
        logging.info(
            "OpenAlex expandido em %d relações artigo-ISSN (%d ISSNs únicos)",
            len(expanded),
            expanded["issn_norm"].nunique(),
        )

    return expanded


def build_latindex_issn_df(latindex: pd.DataFrame) -> pd.DataFrame:
    latindex = latindex.copy()

    latindex["issn_e_norm"] = latindex["issn_e"].apply(normalize_issn)
    latindex["issn_l_norm"] = latindex["issn_l"].apply(normalize_issn)
    latindex["issn_imp_norm"] = latindex["issn_imp"].apply(normalize_issn)

    rows: list[dict[str, object]] = []

    for _, row in latindex.iterrows():
        base = {
            "folio_u": row.get("folio_u"),
            "Revista": row.get("tit_propio"),
            "Instituicao_editora": row.get("nombre_edi"),
            "nome_largo": row.get("nombre_largo"),
            "es_enlinea": row.get("es_enlinea"),
            "catalogada": row.get("catalogada"),
            "id_catalogo": row.get("id_catalogo"),
            "subtemas": row.get("subtemas"),
        }

        for tipo, col in (
            ("eletronico", "issn_e_norm"),
            ("linking", "issn_l_norm"),
            ("impresso", "issn_imp_norm"),
        ):
            issn = row.get(col)
            if pd.notna(issn) and issn:
                rows.append(
                    {
                        **base,
                        "tipo_issn": tipo,
                        "issn_norm": issn,
                    }
                )

    latindex_issn = pd.DataFrame(rows).drop_duplicates()

    if latindex_issn.empty:
        logging.warning("A extração de ISSNs do Latindex resultou em DataFrame vazio.")
    else:
        logging.info(
            "Latindex expandido em %d relações revista-ISSN (%d ISSNs únicos)",
            len(latindex_issn),
            latindex_issn["issn_norm"].nunique(),
        )

    return latindex_issn


def build_outputs(
    openalex_issn_expanded: pd.DataFrame,
    latindex_issn_df: pd.DataFrame,
) -> dict[str, pd.DataFrame]:
    openalex_issn_set = set(openalex_issn_expanded["issn_norm"].dropna().unique())

    matched_issns = latindex_issn_df[
        latindex_issn_df["issn_norm"].isin(openalex_issn_set)
    ].copy()

    unmatched_issns = latindex_issn_df[
        ~latindex_issn_df["issn_norm"].isin(openalex_issn_set)
    ].copy()

    matched_issns_detail = matched_issns.merge(
        openalex_issn_expanded,
        on="issn_norm",
        how="left",
    )

    journal_summary = latindex_issn_df.copy()
    journal_summary["encontrado_no_openalex"] = journal_summary["issn_norm"].isin(openalex_issn_set)

    journal_summary = (
        journal_summary
        .groupby(
            ["folio_u", "Revista", "Instituicao_editora", "nome_largo"],
            dropna=False,
        )
        .agg(
            total_issns_latindex=("issn_norm", "nunique"),
            issns_encontrados=("encontrado_no_openalex", "sum"),
            issns_latindex=("issn_norm", lambda x: "; ".join(sorted(set(x.dropna())))),
        )
        .reset_index()
    )

    journal_summary["tem_relacao_com_openalex"] = journal_summary["issns_encontrados"] > 0
    journal_summary["percentual_cobertura_issn"] = (
        journal_summary["issns_encontrados"] / journal_summary["total_issns_latindex"] * 100
    ).round(2)

    cobertura_por_revista = (
        matched_issns_detail
        .groupby(
            ["folio_u", "Revista", "Instituicao_editora", "nome_largo", "issn_norm", "tipo_issn"],
            dropna=False,
        )
        .agg(
            artigos_openalex=("doi_norm", "count"),
            artigos_com_doi=("doi_norm", lambda x: x.notna().sum()),
            anos_distintos=("ano", lambda x: x.dropna().nunique()),
            ano_min=("ano", "min"),
            ano_max=("ano", "max"),
            titulos_periodicos_openalex=("journal_title", lambda x: "; ".join(sorted(set(v for v in x.dropna() if v)))),
        )
        .reset_index()
        .sort_values(["Revista", "artigos_openalex"], ascending=[True, False])
    )

    return {
        "matched_issns_detail": matched_issns_detail,
        "unmatched_issns": unmatched_issns,
        "journal_summary": journal_summary,
        "cobertura_por_revista": cobertura_por_revista,
    }


def build_statistics_text(
    openalex: pd.DataFrame,
    latindex: pd.DataFrame,
    openalex_issn_expanded: pd.DataFrame,
    latindex_issn_df: pd.DataFrame,
    outputs: dict[str, pd.DataFrame],
) -> str:
    matched = outputs["matched_issns_detail"]
    unmatched = outputs["unmatched_issns"]
    summary = outputs["journal_summary"]

    total_openalex_rows = len(openalex)
    total_latindex_rows = len(latindex)
    total_openalex_issn_unique = openalex_issn_expanded["issn_norm"].nunique()
    total_latindex_issn_unique = latindex_issn_df["issn_norm"].nunique()
    total_matched_issn_unique = matched["issn_norm"].nunique()
    total_unmatched_issn_unique = unmatched["issn_norm"].nunique()
    total_latindex_journals = summary["folio_u"].nunique() if "folio_u" in summary.columns else len(summary)
    total_latindex_journals_with_match = int(summary["tem_relacao_com_openalex"].sum())

    coverage_issn = (
        (total_matched_issn_unique / total_latindex_issn_unique) * 100
        if total_latindex_issn_unique else 0
    )
    coverage_journals = (
        (total_latindex_journals_with_match / total_latindex_journals) * 100
        if total_latindex_journals else 0
    )

    lines = [
        "=== ESTATÍSTICAS DA COMPARAÇÃO LATINDEX x OPENALEX ===",
        "",
        f"Linhas lidas no OpenAlex: {total_openalex_rows}",
        f"Linhas lidas no Latindex: {total_latindex_rows}",
        "",
        f"ISSNs únicos identificados no OpenAlex: {total_openalex_issn_unique}",
        f"ISSNs únicos identificados no Latindex: {total_latindex_issn_unique}",
        f"ISSNs únicos do Latindex encontrados no OpenAlex: {total_matched_issn_unique}",
        f"ISSNs únicos do Latindex NÃO encontrados no OpenAlex: {total_unmatched_issn_unique}",
        f"Cobertura de ISSNs do Latindex no OpenAlex: {coverage_issn:.2f}%",
        "",
        f"Revistas Latindex analisadas: {total_latindex_journals}",
        f"Revistas Latindex com pelo menos 1 ISSN encontrado no OpenAlex: {total_latindex_journals_with_match}",
        f"Cobertura de revistas do Latindex no OpenAlex: {coverage_journals:.2f}%",
        "",
        "Observação metodológica:",
        "- A base OpenAlex foi tratada no nível artigo-ISSN, não no nível revista.",
        "- A comparação usou issn_l + lista de issn da coluna 'issn' do OpenAlex.",
        "- A comparação no Latindex usou issn_e + issn_l + issn_imp.",
        "- O matching foi feito por ISSN normalizado, não por título da revista.",
    ]
    return "\n".join(lines)


def write_outputs(outdir: Path, outputs: dict[str, pd.DataFrame], stats_text: str) -> None:
    outdir.mkdir(parents=True, exist_ok=True)

    files = {
        "latindex_issn_encontrado_no_openalex.csv": outputs["matched_issns_detail"],
        "latindex_issn_nao_encontrado_no_openalex.csv": outputs["unmatched_issns"],
        "latindex_revistas_relacao_openalex.csv": outputs["journal_summary"],
        "latindex_cobertura_por_revista.csv": outputs["cobertura_por_revista"],
    }

    for filename, df in files.items():
        path = outdir / filename
        df.to_csv(path, index=False, encoding="utf-8-sig")
        logging.info("Arquivo gerado: %s", path)

    stats_path = outdir / "latindex_estatisticas.txt"
    stats_path.write_text(stats_text, encoding="utf-8")
    logging.info("Arquivo gerado: %s", stats_path)


def main() -> int:
    args = parse_args()
    setup_logging(args.verbose)

    try:
        openalex = read_csv_with_fallbacks(
            args.openalex, args.sep_openalex, args.encoding_openalex, "OpenAlex"
        )
        latindex = read_csv_with_fallbacks(
            args.latindex, args.sep_latindex, args.encoding_latindex, "Latindex"
        )

        ensure_columns(openalex, OPENALEX_REQUIRED_COLUMNS, "OpenAlex")
        ensure_columns(latindex, LATINDEX_REQUIRED_COLUMNS, "Latindex")

        logging.info("Validando e expandindo ISSNs do OpenAlex...")
        openalex_issn_expanded = build_openalex_issn_expanded(openalex)

        logging.info("Validando e expandindo ISSNs do Latindex...")
        latindex_issn_df = build_latindex_issn_df(latindex)

        logging.info("Gerando comparações...")
        outputs = build_outputs(openalex_issn_expanded, latindex_issn_df)

        logging.info("Gerando estatísticas finais...")
        stats_text = build_statistics_text(
            openalex, latindex, openalex_issn_expanded, latindex_issn_df, outputs
        )

        write_outputs(Path(args.outdir), outputs, stats_text)

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
