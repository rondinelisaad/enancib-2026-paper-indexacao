# Continuidade da presença de periódicos de acesso aberto no sistema científico brasileiro

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.19355940.svg)](https://doi.org/10.5281/zenodo.19355940)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
![Reprodutibilidade](https://img.shields.io/badge/Reprodutível-Pipeline%20%2B%20SciELO-blue)

Este repositório contém um pipeline determinístico para analisar a presença observada de periódicos brasileiros no OpenAlex entre 2000 e 2024. O estudo examina trajetórias de presença, proporção de DOI e zonas de Bradford. Uma análise complementar compara o corpus com a Coleção SciELO Brasil e avalia um cenário ampliado.

## Universos analíticos

### Corpus principal

O corpus principal combina o arquivo de periódicos brasileiros do Latindex utilizado no estudo com trabalhos do OpenAlex que possuem ao menos um autor afiliado a instituição brasileira. A unidade analítica é o periódico agregado, identificado por `folio_u`.

- 3.809 registros no arquivo Latindex de entrada;
- 2.861 periódicos com presença observada no OpenAlex;
- 1.000.587 artigos únicos agregados;
- 128 periódicos no núcleo, 513 na zona 2 e 2.220 na periferia.

Esses números representam o arquivo Latindex utilizado, não a totalidade dos registros disponíveis no portal Latindex.

### Análise complementar SciELO

A lista oficial da Coleção SciELO Brasil foi coletada em 6 de setembro de 2026 e congelada em `analise_complementar_scielo/scielo_lista_oficial.csv`. Ela contém 432 registros retornados pelo portal: 429 registros bibliográficos válidos e três registros técnicos inválidos. Foram incluídos títulos correntes e não correntes.

O matching usa interseção exata de ISSNs normalizados. Títulos semelhantes ou idênticos sem ISSN coincidente permanecem para validação manual e não são classificados automaticamente como SciELO.

- 251 periódicos SciELO identificados no corpus principal;
- 84 dos 128 periódicos do núcleo são SciELO;
- não houve match por ISSN ambíguo.

### Cenário Latindex ampliado com SciELO

Como análise de sensibilidade, uma cópia do arquivo Latindex recebeu 177 registros SciELO cujos ISSNs não estavam no CSV Latindex local. Essa base combinada não é uma atualização oficial do Latindex.

- 3.986 registros na entrada ampliada;
- 170 dos 177 registros adicionados têm presença observada no OpenAlex;
- 3.031 periódicos no corpus ampliado;
- 1.155.089 artigos únicos agregados;
- 421 periódicos SciELO identificados;
- 142 periódicos no núcleo, 531 na zona 2 e 2.358 na periferia.

As zonas de Bradford são recalculadas no cenário ampliado. Por isso, 104 periódicos do corpus original mudam de zona.

## Estrutura

```text
.
├── data/
├── scripts/                         # pipeline principal
├── outputs/                         # resultados principais
├── analise_complementar_scielo/
│   ├── 01_integrar_scielo.py
│   ├── 02_analisar_scielo.py
│   ├── 03_ampliar_latindex_com_scielo.py
│   ├── 04_comparar_cenarios.py
│   ├── 05_validar_reprodutibilidade.py
│   ├── scielo_lista_oficial.csv
│   ├── latindex_journals_brasileiros_scielo_ampliada.csv
│   └── cenario_latindex_ampliado/
├── run_pipeline.sh
├── run_analise_scielo.sh
├── CHECKSUMS.sha256
└── requirements.txt
```

## Ambiente

- Python 3.10 ou superior;
- dependências fixadas em `requirements.txt`;
- espaço livre recomendado superior a 3 GB.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Reprodução do corpus principal

```bash
PYTHON_BIN=.venv/bin/python bash run_pipeline.sh
```

Execução manual do modelo:

```bash
.venv/bin/python scripts/06_analise_modelo_continuidade.py \
  --input outputs/05_resultados/base_analitica_periodicos.csv \
  --output outputs/06_modelos/modelos_continuidade.txt
```

## Reprodução da análise SciELO

O comando canônico usa a lista SciELO congelada. Ele reproduz a análise complementar, cria a base combinada, executa as etapas descritivas 1–5 do cenário ampliado e valida as invariantes:

```bash
PYTHON_BIN=.venv/bin/python bash run_analise_scielo.sh
```

Para também estimar os modelos no cenário ampliado:

```bash
PYTHON_BIN=.venv/bin/python RUN_EXPANDED_MODELS=1 bash run_analise_scielo.sh
```

Os modelos ampliados não fazem parte do conjunto atual de resultados. Até que sejam estimados, os coeficientes existentes em `outputs/06_modelos/` referem-se exclusivamente ao corpus principal.

### Controle do volume de artigos

O modelo de duração foi submetido a uma análise de sensibilidade que acrescenta `log1p(total_artigos)` como covariável contínua. No corpus principal, o contraste periferia–núcleo diminuiu de −12,50 para −2,70 anos (atenuação absoluta de 78,4%), embora tenha permanecido significativo. O contraste zona 2–núcleo diminuiu de −3,64 para +0,30 e deixou de ser significativo (`p=0,454`). O modelo somente com volume apresentou `R²=0,609`, ante `R²=0,384` no modelo com Bradford sem volume; o modelo conjunto apresentou `R²=0,630`.

Os VIFs do modelo conjunto foram 5,71 para periferia, 4,33 para zona 2, 1,81 para `log1p(total_artigos)` e 1,02 para proporção de DOI. Esses valores indicam colinearidade moderada nas variáveis indicadoras de zona e recomendam cautela na interpretação de seus coeficientes. O relatório completo está em `outputs/06_modelos/modelos_continuidade.txt`.

## Atualização da lista SciELO

Uma atualização on-line pode produzir resultados diferentes e deve ser gravada em outro diretório:

```bash
.venv/bin/python analise_complementar_scielo/01_integrar_scielo.py \
  --base outputs/05_resultados/base_analitica_periodicos.csv \
  --outdir analise_complementar_scielo/coleta_atualizada
```

Não substitua a lista congelada sem registrar nova data, revisar os matches, atualizar os valores esperados e gerar novos checksums.

## Validação

```bash
.venv/bin/python analise_complementar_scielo/05_validar_reprodutibilidade.py
```

A validação confere checksums das entradas congeladas, unicidade de `folio_u`, quantidades, matches SciELO, distribuição Bradford, mudanças de zona e limites de `proporcao_doi`.

## Regras metodológicas

- ISSN: maiúsculas, remoção de caracteres diferentes de `0–9` e `X`, oito caracteres e formato `####-####`.
- Unidade analítica: periódico agregado por `folio_u`.
- Artigo único: chave sintética formada por DOI, título e ano no nível do periódico.
- DOI: utilizar exclusivamente `proporcao_doi`, proporção de artigos únicos com DOI.
- Bradford: periódicos ordenados por artigos observados e produção acumulada dividida em três parcelas aproximadamente equivalentes.
- Trajetórias: `one-timer` quando observado em um ano; `retirante` quando o último ano é até 2018; `entrante` quando o primeiro ano é a partir de 2020; `continuante` quando observado em pelo menos oito anos e com último ano em 2023 ou depois; `transiente` nos demais casos.

As trajetórias descrevem presença no corpus, não continuidade editorial. As zonas não representam qualidade, prestígio ou pertencimento a indexadores. As análises são associativas, não causais.

## Integridade e proveniência

Os hashes SHA-256 das entradas congeladas e bases centrais estão em `CHECKSUMS.sha256`. Para reproduzir os números, utilize exatamente esses arquivos. A consulta original do OpenAlex e a data, URL e filtros da exportação Latindex ainda precisam ser recuperados dos registros de coleta originais para permitir reconstrução completa desde as fontes externas.

## Dados, arquivamento e citação

Os arquivos completos de dados e os outputs analíticos, que não são versionados no GitHub por causa do tamanho, estão depositados no [Zenodo (dataset)](https://doi.org/10.5281/zenodo.19355939). A versão arquivada do código está associada ao [DOI do software](https://doi.org/10.5281/zenodo.19355940).

Ao reutilizar este material, cite o artigo, o dataset e a versão correspondente do código. A lista SciELO congelada permanece no repositório por ser uma entrada necessária à reprodução da análise complementar; os demais CSVs dessa análise são gerados pelos scripts e continuam ignorados pelo Git.
