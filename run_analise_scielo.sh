#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$SCRIPT_DIR"
PYTHON_BIN="${PYTHON_BIN:-python3}"
RUN_EXPANDED_MODELS="${RUN_EXPANDED_MODELS:-0}"

SCIELO_DIR="$ROOT_DIR/analise_complementar_scielo"
SCIELO_LIST="$SCIELO_DIR/scielo_lista_oficial.csv"
EXPANDED_LATINDEX="$SCIELO_DIR/latindex_journals_brasileiros_scielo_ampliada.csv"
EXPANDED_OUT="$SCIELO_DIR/cenario_latindex_ampliado"
EXPANDED_SCIELO_OUT="$EXPANDED_OUT/analise_scielo"

require_file() {
  [[ -f "$1" ]] || { echo "Arquivo não encontrado: $1" >&2; exit 1; }
}

require_file "$ROOT_DIR/data/openalex_BR_2000_2024_tratado.csv"
require_file "$ROOT_DIR/data/latindex-journals-brasileiros.csv"
require_file "$ROOT_DIR/outputs/05_resultados/base_analitica_periodicos.csv"

require_file "$SCIELO_LIST"
"$PYTHON_BIN" "$SCIELO_DIR/01_integrar_scielo.py" \
  --base "$ROOT_DIR/outputs/05_resultados/base_analitica_periodicos.csv" \
  --scielo-csv "$SCIELO_LIST" \
  --outdir "$SCIELO_DIR"

"$PYTHON_BIN" "$SCIELO_DIR/02_analisar_scielo.py" \
  --base "$ROOT_DIR/outputs/05_resultados/base_analitica_periodicos.csv" \
  --matches "$SCIELO_DIR/scielo_matches.csv" \
  --scielo-list "$SCIELO_LIST" \
  --outdir "$SCIELO_DIR"

"$PYTHON_BIN" "$SCIELO_DIR/03_ampliar_latindex_com_scielo.py" \
  --latindex "$ROOT_DIR/data/latindex-journals-brasileiros.csv" \
  --scielo "$SCIELO_LIST" \
  --output "$EXPANDED_LATINDEX" \
  --audit "$SCIELO_DIR/registros_scielo_adicionados.csv"

if [[ "$RUN_EXPANDED_MODELS" == "1" ]]; then
  PYTHON_BIN="$PYTHON_BIN" \
  LATINDEX_INPUT="$EXPANDED_LATINDEX" \
  OUTPUT_DIR="$EXPANDED_OUT" \
    bash "$ROOT_DIR/run_pipeline.sh"
else
  mkdir -p "$EXPANDED_OUT/01_crossmatch" "$EXPANDED_OUT/02_classificacao" \
    "$EXPANDED_OUT/03_doi" "$EXPANDED_OUT/04_bradford" "$EXPANDED_OUT/05_resultados"

  "$PYTHON_BIN" "$ROOT_DIR/scripts/01_comparar_issn_latindex_openalex.py" \
    --openalex "$ROOT_DIR/data/openalex_BR_2000_2024_tratado.csv" \
    --latindex "$EXPANDED_LATINDEX" \
    --outdir "$EXPANDED_OUT/01_crossmatch"
  "$PYTHON_BIN" "$ROOT_DIR/scripts/02_classificar_periodicos_openalex_por_periodico.py" \
    --input "$EXPANDED_OUT/01_crossmatch/latindex_issn_encontrado_no_openalex.csv" \
    --outdir "$EXPANDED_OUT/02_classificacao"
  "$PYTHON_BIN" "$ROOT_DIR/scripts/03_calcular_proporcao_doi_v2.py" \
    --input "$EXPANDED_OUT/01_crossmatch/latindex_issn_encontrado_no_openalex.csv" \
    --outdir "$EXPANDED_OUT/03_doi"
  "$PYTHON_BIN" "$ROOT_DIR/scripts/04_criar_periodicos_bradford.py" \
    --input "$EXPANDED_OUT/02_classificacao/periodico_resumo_classificacao.csv" \
    --outdir "$EXPANDED_OUT/04_bradford"
  "$PYTHON_BIN" "$ROOT_DIR/scripts/05_gerar_tabelas_resultados.py" \
    --resumo "$EXPANDED_OUT/02_classificacao/periodico_resumo_classificacao.csv" \
    --doi "$EXPANDED_OUT/03_doi/doi_por_periodico.csv" \
    --bradford "$EXPANDED_OUT/04_bradford/periodicos_bradford.csv" \
    --outdir "$EXPANDED_OUT/05_resultados"
fi

mkdir -p "$EXPANDED_SCIELO_OUT"
"$PYTHON_BIN" "$SCIELO_DIR/01_integrar_scielo.py" \
  --base "$EXPANDED_OUT/05_resultados/base_analitica_periodicos.csv" \
  --scielo-csv "$SCIELO_LIST" \
  --outdir "$EXPANDED_SCIELO_OUT"
"$PYTHON_BIN" "$SCIELO_DIR/02_analisar_scielo.py" \
  --base "$EXPANDED_OUT/05_resultados/base_analitica_periodicos.csv" \
  --matches "$EXPANDED_SCIELO_OUT/scielo_matches.csv" \
  --scielo-list "$EXPANDED_SCIELO_OUT/scielo_lista_oficial.csv" \
  --outdir "$EXPANDED_SCIELO_OUT"
"$PYTHON_BIN" "$SCIELO_DIR/04_comparar_cenarios.py"
VALIDATION_ARGS=()
if [[ "$RUN_EXPANDED_MODELS" == "1" ]]; then
  VALIDATION_ARGS+=("--require-expanded-models")
fi
"$PYTHON_BIN" "$SCIELO_DIR/05_validar_reprodutibilidade.py" "${VALIDATION_ARGS[@]}"

echo "Análise SciELO reproduzida em: $SCIELO_DIR"
