#!/usr/bin/env python3
"""Valida entradas congeladas e invariantes dos cenarios original e ampliado."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent.parent
SCIELO = ROOT / "analise_complementar_scielo"
EXPANDED = SCIELO / "cenario_latindex_ampliado"

EXPECTED_HASHES = {
    "data/openalex_BR_2000_2024_tratado.csv": "fb8ec4bfa1d8de9e1505d09a5161b4f544d39b11a6f1c511477249ff638b5dbb",
    "data/latindex-journals-brasileiros.csv": "1f78ced0d5b67226c53c72fe5791e58bf8d5a2c7f4fb38fb188679ad8dbaa0ec",
    "analise_complementar_scielo/scielo_lista_oficial.csv": "9c12e4aceb3a594c791d92f289938721e5dfcfbc6fa702b3dcd82b139a38c589",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Valida a reprodução da análise SciELO.")
    parser.add_argument("--skip-hashes", action="store_true", help="Não verifica os três arquivos de entrada congelados.")
    parser.add_argument("--require-expanded-models", action="store_true", help="Exige o relatório de modelos do cenário ampliado.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.skip_hashes:
        for relative, expected in EXPECTED_HASHES.items():
            path = ROOT / relative
            require(path.is_file(), f"Entrada ausente: {relative}")
            require(sha256(path) == expected, f"Checksum divergente: {relative}")

    source = pd.read_csv(SCIELO / "scielo_lista_oficial.csv")
    original = pd.read_csv(ROOT / "outputs/05_resultados/base_analitica_periodicos.csv", dtype={"folio_u": str})
    original_matches = pd.read_csv(SCIELO / "scielo_matches.csv", dtype={"folio_u": str})
    additions = pd.read_csv(SCIELO / "registros_scielo_adicionados.csv", dtype=str)
    augmented_input = pd.read_csv(SCIELO / "latindex_journals_brasileiros_scielo_ampliada.csv", sep=";", dtype=str)
    expanded = pd.read_csv(EXPANDED / "05_resultados/base_analitica_periodicos.csv", dtype={"folio_u": str})
    expanded_matches = pd.read_csv(EXPANDED / "analise_scielo/scielo_matches.csv", dtype={"folio_u": str})
    zones = pd.read_csv(EXPANDED / "analise_scielo/tabela_scielo_bradford.csv")
    migrations = pd.read_csv(EXPANDED / "migracao_zonas_periodicos_originais.csv", dtype={"folio_u": str})

    require(len(source) == 432, "A lista congelada deve conter 432 registros.")
    require(int(source["registro_tecnico_invalido"].sum()) == 3, "Devem existir três registros técnicos inválidos.")
    valid = source[source["registro_tecnico_invalido"] == 0]
    require(len(valid) == 429, "Devem existir 429 registros bibliográficos válidos.")
    require(valid["issns_scielo"].fillna("").str.len().gt(0).all(), "Todo registro SciELO válido deve possuir ISSN.")
    require(len(original) == original["folio_u"].nunique() == 2861, "O corpus original deve conter 2.861 periódicos únicos.")
    require(int(original_matches["scielo"].sum()) == 251, "O corpus original deve conter 251 matches SciELO.")
    require(len(additions) == additions["folio_u_sintetico"].nunique() == 177, "Devem ser adicionados 177 registros únicos.")
    require(additions["folio_u_sintetico"].str.startswith("SCIELO-").all(), "Todo folio sintético deve usar o prefixo SCIELO-.")
    require(len(augmented_input) == augmented_input["folio_u"].nunique() == 3986, "A entrada ampliada deve conter 3.986 registros únicos.")
    require(len(expanded) == expanded["folio_u"].nunique() == 3031, "O cenário ampliado deve conter 3.031 periódicos únicos.")
    observed_added = set(additions["folio_u_sintetico"]) & set(expanded["folio_u"])
    require(len(observed_added) == 170, "Devem existir 170 registros adicionados com presença observada.")
    require(int(expanded_matches["scielo"].sum()) == 421, "O cenário ampliado deve conter 421 matches SciELO.")
    expected_zones = {"núcleo": 142, "zona 2": 531, "periferia": 2358}
    actual_zones = expanded["zona_bradford"].value_counts().to_dict()
    require(actual_zones == expected_zones, f"Distribuição Bradford divergente: {actual_zones}")
    require(int(zones.loc[zones["zona_bradford"] == "núcleo", "SciELO"].iloc[0]) == 102, "O núcleo ampliado deve conter 102 SciELO.")
    require(int(migrations["mudou_zona"].sum()) == 104, "Devem existir 104 mudanças de zona entre periódicos originais.")
    require(original["proporcao_doi"].notna().all() and expanded["proporcao_doi"].notna().all(), "proporcao_doi não pode conter valores ausentes.")
    require(original["proporcao_doi"].between(0, 1).all() and expanded["proporcao_doi"].between(0, 1).all(), "proporcao_doi deve estar entre zero e um.")
    if args.require_expanded_models:
        require((EXPANDED / "06_modelos/modelos_continuidade.txt").is_file(), "Modelos ampliados não foram gerados.")
    print("VALIDAÇÃO OK: entradas congeladas e invariantes dos cenários foram confirmadas.")


if __name__ == "__main__":
    main()
