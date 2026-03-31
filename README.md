# Reprodutibilidade do pipeline analítico

Este repositório contém o pipeline para análise de estabilidade de indexação, densidade de DOI e posição estrutural de periódicos brasileiros de acesso aberto no período de 2000–2024.

## Objetivo

Construir uma base analítica por periódico e testar a associação entre:

- posição estrutural no sistema (Bradford)
- densidade de DOI
- continuidade de indexação

## Unidade de análise

A unidade analítica é o **periódico**, identificado por `folio_u`.

ISSNs impresso, eletrônico e linking são tratados como atributos do mesmo periódico e colapsados no nível do periódico.

## Arquivos de entrada

Coloque os arquivos abaixo na pasta `data_raw/`:

- `openalex_BR_2000_2024_tratado.csv`
- `latindex-journals-brasileiros.csv`

## Estrutura esperada do projeto

```text
enancib-2026-paper-indexacao/
├── data_raw/
│   ├── openalex_BR_2000_2024_tratado.csv
│   └── latindex-journals-brasileiros.csv
├── data_processed/
├── outputs/
├── scripts/
│   ├── 01_comparar_issn_latindex_openalex.py
│   ├── 02_classificar_periodicos_openalex_por_periodico.py
│   ├── 03_calcular_proporcao_doi_v2.py
│   ├── 04_criar_periodicos_bradford.py
│   ├── 05_gerar_tabelas_resultados.py
│   └── 06_analise_modelo_continuidade.py
├── requirements.txt
├── run_pipeline.sh
└── README.md
