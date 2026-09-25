#!/usr/bin/env python3
"""Cria uma copia do Latindex acrescida dos titulos SciELO ausentes por ISSN."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd


LATINDEX_COLUMNS = [
    "folio_u", "tit_propio", "nombre_edi", "es_enlinea", "catalogada",
    "id_catalogo", "nombre_largo", "issn_e", "issn_l", "issn_imp", "subtemas",
]


def normalize_issn(value: object) -> str | None:
    if pd.isna(value):
        return None
    s = re.sub(r"[^0-9X]", "", str(value).strip().upper())
    return f"{s[:4]}-{s[4:]}" if len(s) == 8 else None


def split_issns(value: object) -> set[str]:
    if pd.isna(value):
        return set()
    return {x for part in re.split(r"[;,|]", str(value)) if (x := normalize_issn(part))}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Amplia uma copia do Latindex com registros SciELO ausentes.")
    p.add_argument("--latindex", default="data/latindex-journals-brasileiros.csv")
    p.add_argument("--scielo", default="analise_complementar_scielo/scielo_lista_oficial.csv")
    p.add_argument("--output", default="analise_complementar_scielo/latindex_journals_brasileiros_scielo_ampliada.csv")
    p.add_argument("--audit", default="analise_complementar_scielo/registros_scielo_adicionados.csv")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    latindex = pd.read_csv(args.latindex, sep=";", dtype=str, keep_default_na=False)
    scielo = pd.read_csv(args.scielo, dtype=str, keep_default_na=False)
    missing = set(LATINDEX_COLUMNS) - set(latindex.columns)
    if missing:
        raise ValueError(f"Colunas ausentes no Latindex: {sorted(missing)}")
    required_scielo = {"scielo_acronimo", "titulo_scielo", "issns_scielo", "issn_e_scielo", "issn_imp_scielo", "editora_scielo", "area_scielo", "registro_tecnico_invalido"}
    missing = required_scielo - set(scielo.columns)
    if missing:
        raise ValueError(f"Metadados SciELO precisam ser recoletados; colunas ausentes: {sorted(missing)}")

    existing_issns: set[str] = set()
    for col in ["issn_e", "issn_l", "issn_imp"]:
        existing_issns.update(x for value in latindex[col] for x in split_issns(value))

    candidates = scielo[
        (pd.to_numeric(scielo["registro_tecnico_invalido"], errors="coerce").fillna(0) == 0)
        & ~scielo["issns_scielo"].apply(lambda value: bool(split_issns(value) & existing_issns))
    ].copy()
    if candidates["scielo_acronimo"].duplicated().any():
        raise ValueError("Acronimos duplicados entre os registros bibliograficos a adicionar.")

    additions = []
    audit = []
    for row in candidates.itertuples():
        all_issns = sorted(split_issns(row.issns_scielo))
        electronic = normalize_issn(row.issn_e_scielo) or ""
        printed = normalize_issn(row.issn_imp_scielo) or ""
        untyped = [x for x in all_issns if x not in {electronic, printed}]
        linking = untyped[0] if len(untyped) == 1 else ""
        folio = f"SCIELO-{row.scielo_acronimo}"
        additions.append({
            "folio_u": folio,
            "tit_propio": row.titulo_scielo,
            "nombre_edi": row.editora_scielo,
            "es_enlinea": "1",
            "catalogada": "",
            "id_catalogo": "",
            "nombre_largo": "Brasil",
            "issn_e": electronic,
            "issn_l": linking,
            "issn_imp": printed,
            "subtemas": row.area_scielo,
        })
        audit.append({
            "folio_u_sintetico": folio,
            "titulo_scielo": row.titulo_scielo,
            "status_scielo": row.status_scielo,
            "issns_scielo": row.issns_scielo,
            "issn_e_adicionado": electronic,
            "issn_imp_adicionado": printed,
            "issn_l_adicionado": linking,
            "fonte": row.url_scielo,
            "decisao": "adicionado_por_ausencia_de_todos_os_issns_no_csv_latindex_local",
        })

    additions_df = pd.DataFrame(additions, columns=LATINDEX_COLUMNS)
    expanded = pd.concat([latindex[LATINDEX_COLUMNS], additions_df], ignore_index=True)
    if expanded["folio_u"].duplicated().any():
        raise ValueError("A ampliacao produziu folio_u duplicado.")
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    expanded.to_csv(output, sep=";", index=False, encoding="utf-8-sig")
    pd.DataFrame(audit).to_csv(args.audit, index=False, encoding="utf-8-sig")
    print(f"Latindex original: {len(latindex)}; adicionados: {len(additions_df)}; ampliado: {len(expanded)}.")


if __name__ == "__main__":
    main()
