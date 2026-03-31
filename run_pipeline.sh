#!/usr/bin/env bash
set -euo pipefail

mkdir -p data_processed/01_crosswalk
mkdir -p data_processed/02_periodicos
mkdir -p data_processed/03_doi
mkdir -p data_processed/04_bradford
mkdir -p outputs/05_resultados

python3 scripts/01_comparar_issn_latindex_openalex.py   --openalex data_raw/openalex_BR_2000_2024_tratado.csv   --latindex data_raw/latindex-journals-brasileiros.csv   --outdir data_processed/01_crosswalk

python3 scripts/02_classificar_periodicos_openalex_por_periodico.py   --input data_processed/01_crosswalk/latindex_issn_encontrado_no_openalex.csv   --outdir data_processed/02_periodicos

python3 scripts/03_calcular_proporcao_doi_v2.py   --input data_processed/01_crosswalk/latindex_issn_encontrado_no_openalex.csv   --outdir data_processed/03_doi

python3 scripts/04_criar_periodicos_bradford.py   --input data_processed/02_periodicos/periodico_resumo_classificacao.csv   --outdir data_processed/04_bradford

python3 scripts/05_gerar_tabelas_resultados.py   --resumo data_processed/02_periodicos/periodico_resumo_classificacao.csv   --doi data_processed/03_doi/doi_por_periodico.csv   --bradford data_processed/04_bradford/periodicos_bradford.csv   --outdir outputs/05_resultados

python3 scripts/06_analise_modelo_continuidade.py
