#!/usr/bin/env bash
set -Eeuo pipefail

# =========================================
# run_pipeline.sh
# Pipeline reprodutível do estudo
# =========================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$SCRIPT_DIR"

PYTHON_BIN="${PYTHON_BIN:-python3}"

# Entradas padrão
OPENALEX_INPUT="${OPENALEX_INPUT:-$ROOT_DIR/data/openalex_BR_2000_2024_tratado.csv}"
LATINDEX_INPUT="${LATINDEX_INPUT:-$ROOT_DIR/data/latindex-journals-brasileiros.csv}"

# Saídas
OUTPUT_DIR="${OUTPUT_DIR:-$ROOT_DIR/outputs}"
STEP01_DIR="$OUTPUT_DIR/01_crossmatch"
STEP02_DIR="$OUTPUT_DIR/02_classificacao"
STEP03_DIR="$OUTPUT_DIR/03_doi"
STEP04_DIR="$OUTPUT_DIR/04_bradford"
STEP05_DIR="$OUTPUT_DIR/05_resultados"
STEP06_DIR="$OUTPUT_DIR/06_modelos"
LOG_DIR="$OUTPUT_DIR/logs"

# Scripts
SCRIPT01="$ROOT_DIR/scripts/01_comparar_issn_latindex_openalex.py"
SCRIPT02="$ROOT_DIR/scripts/02_classificar_periodicos_openalex_por_periodico.py"
SCRIPT03="$ROOT_DIR/scripts/03_calcular_proporcao_doi_v2.py"
SCRIPT04="$ROOT_DIR/scripts/04_criar_periodicos_bradford.py"
SCRIPT05="$ROOT_DIR/scripts/05_gerar_tabelas_resultados.py"
SCRIPT06="$ROOT_DIR/scripts/06_analise_modelo_continuidade.py"

TIMESTAMP="$(date '+%Y%m%d_%H%M%S')"
LOG_FILE="$LOG_DIR/pipeline_${TIMESTAMP}.log"

# -----------------------------------------
# Tratamento de erro
# -----------------------------------------
on_error() {
  local exit_code=$?
  local line_no="${1:-unknown}"
  echo "[ERRO] Falha na linha $line_no. Código de saída: $exit_code" | tee -a "$LOG_FILE" >&2
  exit "$exit_code"
}
trap 'on_error $LINENO' ERR

# -----------------------------------------
# Utilitários
# -----------------------------------------
log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

die() {
  echo "[FATAL] $*" | tee -a "$LOG_FILE" >&2
  exit 1
}

require_file() {
  local f="$1"
  [[ -f "$f" ]] || die "Arquivo não encontrado: $f"
}

require_cmd() {
  local c="$1"
  command -v "$c" >/dev/null 2>&1 || die "Comando não encontrado: $c"
}

require_python_module() {
  local module="$1"
  "$PYTHON_BIN" -c "import $module" >/dev/null 2>&1 || die "Módulo Python ausente: $module"
}

run_step() {
  local step_name="$1"
  shift
  log "Iniciando: $step_name"
  "$@" 2>&1 | tee -a "$LOG_FILE"
  log "Concluído: $step_name"
}

# -----------------------------------------
# Preparação
# -----------------------------------------
mkdir -p \
  "$OUTPUT_DIR" \
  "$STEP01_DIR" \
  "$STEP02_DIR" \
  "$STEP03_DIR" \
  "$STEP04_DIR" \
  "$STEP05_DIR" \
  "$STEP06_DIR" \
  "$LOG_DIR"

log "==== Início do pipeline ===="
log "ROOT_DIR=$ROOT_DIR"
log "PYTHON_BIN=$PYTHON_BIN"
log "OPENALEX_INPUT=$OPENALEX_INPUT"
log "LATINDEX_INPUT=$LATINDEX_INPUT"
log "OUTPUT_DIR=$OUTPUT_DIR"

require_cmd "$PYTHON_BIN"

# Dependências mínimas do pipeline
require_python_module pandas
require_python_module statsmodels

# Scripts obrigatórios
require_file "$SCRIPT01"
require_file "$SCRIPT02"
require_file "$SCRIPT03"
require_file "$SCRIPT04"
require_file "$SCRIPT05"
require_file "$SCRIPT06"

# Dados de entrada
require_file "$OPENALEX_INPUT"
require_file "$LATINDEX_INPUT"

# Informações do ambiente
{
  echo "timestamp=$TIMESTAMP"
  echo "root_dir=$ROOT_DIR"
  echo "python_bin=$PYTHON_BIN"
  "$PYTHON_BIN" --version
  echo "openalex_input=$OPENALEX_INPUT"
  echo "latindex_input=$LATINDEX_INPUT"
  echo "output_dir=$OUTPUT_DIR"
} >> "$LOG_FILE"

# -----------------------------------------
# Etapa 1 - Cruzamento OpenAlex x Latindex
# -----------------------------------------
run_step "01 - Cruzamento OpenAlex x Latindex" \
  "$PYTHON_BIN" "$SCRIPT01" \
    --openalex "$OPENALEX_INPUT" \
    --latindex "$LATINDEX_INPUT" \
    --outdir "$STEP01_DIR"

require_file "$STEP01_DIR/latindex_issn_encontrado_no_openalex.csv"
require_file "$STEP01_DIR/latindex_issn_nao_encontrado_no_openalex.csv"
require_file "$STEP01_DIR/latindex_revistas_relacao_openalex.csv"
require_file "$STEP01_DIR/latindex_cobertura_por_revista.csv"
require_file "$STEP01_DIR/latindex_estatisticas.txt"

# -----------------------------------------
# Etapa 2 - Classificação por periódico
# -----------------------------------------
run_step "02 - Classificação por periódico" \
  "$PYTHON_BIN" "$SCRIPT02" \
    --input "$STEP01_DIR/latindex_issn_encontrado_no_openalex.csv" \
    --outdir "$STEP02_DIR"

require_file "$STEP02_DIR/periodico_ano_indicadores.csv"
require_file "$STEP02_DIR/periodico_resumo_classificacao.csv"
require_file "$STEP02_DIR/categoria_resumo.csv"
require_file "$STEP02_DIR/classificacao_estatisticas.txt"

# -----------------------------------------
# Etapa 3 - Cálculo da proporção de DOI
# -----------------------------------------
run_step "03 - Cálculo da proporção de DOI" \
  "$PYTHON_BIN" "$SCRIPT03" \
    --input "$STEP01_DIR/latindex_issn_encontrado_no_openalex.csv" \
    --outdir "$STEP03_DIR"

require_file "$STEP03_DIR/doi_por_issn.csv"
require_file "$STEP03_DIR/doi_por_issn_ano.csv"
require_file "$STEP03_DIR/doi_por_periodico.csv"
require_file "$STEP03_DIR/doi_por_periodico_ano.csv"
require_file "$STEP03_DIR/doi_indicadores_estatisticas.txt"

# -----------------------------------------
# Etapa 4 - Classificação Bradford
# -----------------------------------------
run_step "04 - Classificação Bradford" \
  "$PYTHON_BIN" "$SCRIPT04" \
    --input "$STEP02_DIR/periodico_resumo_classificacao.csv" \
    --outdir "$STEP04_DIR"

require_file "$STEP04_DIR/periodicos_bradford.csv"
require_file "$STEP04_DIR/bradford_resumo.txt"

# -----------------------------------------
# Etapa 5 - Geração das tabelas de resultados
# -----------------------------------------
run_step "05 - Geração das tabelas de resultados" \
  "$PYTHON_BIN" "$SCRIPT05" \
    --resumo "$STEP02_DIR/periodico_resumo_classificacao.csv" \
    --doi "$STEP03_DIR/doi_por_periodico.csv" \
    --bradford "$STEP04_DIR/periodicos_bradford.csv" \
    --outdir "$STEP05_DIR"

require_file "$STEP05_DIR/base_analitica_periodicos.csv"
require_file "$STEP05_DIR/tabela_1_distribuicao_bradford.csv"
require_file "$STEP05_DIR/tabela_2_categorias_por_zona.csv"
require_file "$STEP05_DIR/tabela_3_frequencia_categorias.csv"
require_file "$STEP05_DIR/tabela_4_zona_categoria_doi.csv"
require_file "$STEP05_DIR/tabela_5_metricas_por_zona.csv"
require_file "$STEP05_DIR/tabela_6_metricas_por_categoria.csv"
require_file "$STEP05_DIR/resumo_resultados.txt"

# -----------------------------------------
# Etapa 6 - Modelos analíticos
# -----------------------------------------
run_step "06 - Modelos analíticos" \
  "$PYTHON_BIN" "$SCRIPT06" \
    --input "$STEP05_DIR/base_analitica_periodicos.csv" \
    --output "$STEP06_DIR/modelos_continuidade.txt"

require_file "$STEP06_DIR/modelos_continuidade.txt"

log "==== Pipeline concluído com sucesso ===="
log "Saídas em: $OUTPUT_DIR"
log "Log completo em: $LOG_FILE"
