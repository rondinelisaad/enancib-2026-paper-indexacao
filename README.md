# Continuidade da presença de periódicos de acesso aberto no sistema científico brasileiro

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.19355940.svg)](https://doi.org/10.5281/zenodo.19355940)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
![Reprodutibilidade](https://img.shields.io/badge/Reprodutível-Pipeline%20completo%20%2B%20Zenodo-blue)

Este repositório contém o pipeline analítico utilizado no estudo sobre continuidade da presença de periódicos brasileiros de acesso aberto, infraestrutura editorial (DOI) e posição estrutural no sistema científico (2000–2024).

---

## Objetivo

O objetivo do pipeline é:

- identificar periódicos brasileiros presentes no OpenAlex;
- construir indicadores de continuidade da presença observada;
- calcular proporção de DOI;
- classificar periódicos segundo zonas de Bradford;
- gerar tabelas analíticas;
- executar modelos estatísticos de associação.

---

## Definição do universo analítico

A base OpenAlex utilizada contém artigos com pelo menos um autor com afiliação brasileira.

Isso implica que:

- o dataset inclui artigos de periódicos brasileiros e internacionais;
- o pipeline identifica periódicos brasileiros presentes nesse recorte de produção científica;
- os resultados não representam a totalidade da produção editorial dos periódicos.

> Em termos analíticos, o estudo mede: **a presença de periódicos brasileiros no fluxo de produção científica com participação nacional.**

---

## Estrutura do repositório

```
enancib-2026-paper-indexacao/
├── README.md
├── requirements.txt
├── run_pipeline.sh
├── scripts/
│   ├── 01_comparar_issn_latindex_openalex.py
│   ├── 02_classificar_periodicos_openalex_por_periodico.py
│   ├── 03_calcular_proporcao_doi_v2.py
│   ├── 04_criar_periodicos_bradford.py
│   ├── 05_gerar_tabelas_resultados.py
│   └── 06_analise_modelo_continuidade.py
├── docs/
│   └── reproducibilidade.md
└── data_sample/
```

---

## Requisitos

- Python 3.10+
- pandas
- statsmodels

**Instalação:**

```bash
pip install -r requirements.txt
```

---

## Execução do pipeline

**Execução sequencial:**

```bash
bash run_pipeline.sh
```

**Ou manualmente:**

```bash
# 1. Cruzamento OpenAlex × Latindex
python3 scripts/01_comparar_issn_latindex_openalex.py \
  --openalex openalex.csv \
  --latindex latindex.csv \
  --outdir outputs/01_crossmatch

# 2. Construção da base periódico-ano
python3 scripts/02_classificar_periodicos_openalex_por_periodico.py \
  --input outputs/01_crossmatch/latindex_issn_encontrado_no_openalex.csv \
  --outdir outputs/02_classificacao

# 3. Cálculo da proporção de DOI
python3 scripts/03_calcular_proporcao_doi_v2.py \
  --input outputs/01_crossmatch/latindex_issn_encontrado_no_openalex.csv \
  --outdir outputs/03_doi

# 4. Classificação de Bradford
python3 scripts/04_criar_periodicos_bradford.py \
  --input outputs/02_classificacao/periodico_resumo_classificacao.csv \
  --outdir outputs/04_bradford

# 5. Geração das tabelas
python3 scripts/05_gerar_tabelas_resultados.py \
  --resumo outputs/02_classificacao/periodico_resumo_classificacao.csv \
  --doi outputs/03_doi/doi_por_periodico.csv \
  --bradford outputs/04_bradford/periodicos_bradford.csv \
  --outdir outputs/05_resultados

# 6. Modelos analíticos
python3 scripts/06_analise_modelo_continuidade.py
```

---

## Lógica do pipeline

### Script 01 — Cruzamento de bases

- Cruza OpenAlex e Latindex via ISSN
- Identifica periódicos brasileiros presentes no OpenAlex

### Script 02 — Base periódico-ano

- Define o periódico (`folio_u`) como unidade analítica
- Deduplica artigos (DOI + título + ano)
- Calcula indicadores de continuidade

### Script 03 — Proporção de DOI

- Calcula proporção de DOI por ISSN e por periódico
- Inclui granularidade temporal

### Script 04 — Bradford

- Ordena periódicos por volume de artigos
- Classifica em:
  - **núcleo**
  - **zona 2**
  - **periferia**

> A divisão é baseada em terços do acumulado de artigos (operacionalização, não prova da lei)

### Script 05 — Base analítica e tabelas
- integra continuidade observada, proporção de DOI e classificação estrutural
- gera a base analítica final
- produz tabelas descritivas da seção de resultados
- gera um resumo textual automatizado dos principais padrões observados

### Script 06 — Modelos analíticos
- executa correlações entre proporção de DOI e continuidade
- estima modelos OLS e logit
- grava relatório textual dos modelos
- análise associativa, não causal

> Análise associativa (não causal)

---

## Principais outputs

- `base_analitica_periodicos.csv`
- tabelas analíticas (1 a 6)
- classificação Bradford
- indicadores de DOI
- outputs de modelos
- outputs/05_resultados/resumo_resultados.txt
- outputs/06_modelos/modelos_continuidade.txt

---

## Limitações importantes

- OpenAlex é usado como proxy de presença observada no recorte analisado
- A base contém artigos com pelo menos um autor com afiliação brasileira
- A proporção de DOI é calculada sobre o conjunto observado
- A deduplicação usa chave sintética (DOI + título + ano)
- A classificação de Bradford é uma operacionalização baseada no acumulado de artigos
- Os resultados devem ser interpretados como associações, não como relações causais

---

## Dados

Os dados utilizados neste estudo não são versionados neste repositório.

Os dados completos e outputs analíticos estão disponíveis em:

> **Zenodo:** https://doi.org/10.5281/zenodo.19355939

O diretório `data/` é utilizado apenas como ponto de entrada para execução do pipeline.
---

## Reprodutibilidade

- Pipeline totalmente reproduzível via scripts sequenciais
- Regras detalhadas em `docs/reproducibilidade.md`
- Dados versionados com DOI (Zenodo)
- Código versionado (GitHub)

---

## Citação

Se utilizar este repositório, cite:

- o artigo
- o DOI do dataset no Zenodo
- a versão do código utilizada
