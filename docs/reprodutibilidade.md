# Reprodutibilidade do estudo

## 1. Escopo

O repositório permite repetir computacionalmente dois cenários sobre arquivos congelados:

1. corpus principal, construído a partir do arquivo Latindex local e do recorte OpenAlex;
2. cenário de sensibilidade, no qual o arquivo Latindex local é complementado com registros da Coleção SciELO Brasil ausentes por ISSN.

A análise complementar também descreve como os periódicos SciELO se distribuem no corpus principal e no ampliado. O cenário ampliado não é uma atualização oficial do Latindex.

## 2. Entradas

### 2.1 OpenAlex

Arquivo: `data/openalex_BR_2000_2024_tratado.csv`.

Contém trabalhos de 2000–2024 com ao menos um autor afiliado a instituição brasileira. O arquivo tem aproximadamente 3,2 milhões de linhas e 743 MB. A consulta original, data de obtenção, versão do snapshot e transformações anteriores ao arquivo tratado ainda devem ser recuperadas e registradas para permitir reconstrução completa desde a fonte.

### 2.2 Latindex

Arquivo: `data/latindex-journals-brasileiros.csv`.

Contém 3.809 registros de periódicos brasileiros. A validação com a SciELO mostrou que esse arquivo não representa necessariamente todos os títulos disponíveis no portal Latindex. A data, URL, filtros e procedimento da exportação original ainda devem ser documentados.

### 2.3 SciELO Brasil

Arquivo congelado: `analise_complementar_scielo/scielo_lista_oficial.csv`.

- fonte: `https://www.scielo.br/journals/alpha?ilang=pt_BR` e páginas individuais dos periódicos;
- data da coleta: 2026-09-06;
- coleção: SciELO Brasil, sem outras coleções da SciELO Network;
- escopo: títulos correntes, com indexação interrompida e terminados;
- 432 registros retornados;
- 429 registros bibliográficos válidos;
- três registros técnicos anômalos preservados, mas impedidos de gerar matches.

O arquivo congelado deve ser usado para reproduzir os resultados. Consultar novamente o portal caracteriza atualização da fonte e exige nova auditoria.

## 3. Integridade dos arquivos

`CHECKSUMS.sha256` registra os SHA-256 das entradas e bases centrais. A validação automatizada confere as três entradas congeladas antes dos resultados.

```bash
.venv/bin/python analise_complementar_scielo/05_validar_reprodutibilidade.py
```

| Entrada | SHA-256 |
|---|---|
| `data/openalex_BR_2000_2024_tratado.csv` | `fb8ec4bfa1d8de9e1505d09a5161b4f544d39b11a6f1c511477249ff638b5dbb` |
| `data/latindex-journals-brasileiros.csv` | `1f78ced0d5b67226c53c72fe5791e58bf8d5a2c7f4fb38fb188679ad8dbaa0ec` |
| `analise_complementar_scielo/scielo_lista_oficial.csv` | `9c12e4aceb3a594c791d92f289938721e5dfcfbc6fa702b3dcd82b139a38c589` |

## 4. Ambiente

- Python 3.10+;
- `pandas==2.2.2`;
- `numpy==1.26.4`;
- `scipy==1.13.1`;
- `statsmodels==0.14.2`.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## 5. Pipeline principal

```bash
PYTHON_BIN=.venv/bin/python bash run_pipeline.sh
```

Etapas: cruzamento por ISSN; agregação periódico-ano; trajetórias; `proporcao_doi`; Bradford; tabelas; correlações e modelos OLS e logit.

O modelo OLS de `anos_com_indexacao` inclui três especificações comparáveis: DOI + Bradford; DOI + `log1p(total_artigos)`; e DOI + Bradford + `log1p(total_artigos)`. O relatório também apresenta a atenuação dos coeficientes de zona, VIF e testes de contribuição incremental entre modelos aninhados.

Resultados esperados:

- 2.861 periódicos e 30.133 registros periódico-ano;
- 1.000.587 artigos únicos agregados;
- Bradford: 128 no núcleo, 513 na zona 2 e 2.220 na periferia;
- trajetórias: 1.620 continuantes, 609 transientes, 409 entrantes, 100 retirantes e 123 one-timers.

Na análise com controle de volume, o coeficiente periferia–núcleo passa de −12,502 para −2,704 anos, com atenuação absoluta de 78,4%, mantendo `p<0,001`. O coeficiente zona 2–núcleo passa de −3,640 para +0,302 (`p=0,454`). Os `R²` são 0,384 para DOI + Bradford, 0,609 para DOI + log(volume) e 0,630 para o modelo conjunto. Os VIFs dos termos não constantes são 5,71 (periferia), 4,33 (zona 2), 1,81 (log do volume) e 1,02 (DOI). Portanto, grande parte da associação bruta entre zona e duração é explicada pelo volume, embora permaneça uma associação residual para a periferia; a colinearidade moderada e a natureza derivada das zonas impedem interpretação causal.

## 6. Matching SciELO no corpus principal

O matching usa a interseção exata entre todos os ISSNs normalizados associados ao periódico. Não há fuzzy matching automático. Título idêntico sem ISSN coincidente é somente candidato manual.

```bash
.venv/bin/python analise_complementar_scielo/01_integrar_scielo.py \
  --base outputs/05_resultados/base_analitica_periodicos.csv \
  --scielo-csv analise_complementar_scielo/scielo_lista_oficial.csv \
  --outdir analise_complementar_scielo

.venv/bin/python analise_complementar_scielo/02_analisar_scielo.py
```

Resultados esperados: 251 periódicos SciELO, 84 no núcleo, zero matches ISSN ambíguos e dois candidatos por título sem confirmação por ISSN.

## 7. Cenário ampliado

```bash
.venv/bin/python analise_complementar_scielo/03_ampliar_latindex_com_scielo.py
```

O script adiciona 177 registros SciELO sem ISSN coincidente no CSV Latindex local. Cada registro recebe `folio_u` sintético `SCIELO-<acrônimo>`. Campos sem equivalente permanecem vazios e a proveniência é registrada em `registros_scielo_adicionados.csv`.

A entrada ampliada contém 3.986 registros únicos. Desses, 170 registros adicionados apresentam presença no OpenAlex e sete não apresentam presença no recorte.

## 8. Execução da análise complementar

O orquestrador reproduz o cenário descritivo atualmente arquivado:

```bash
PYTHON_BIN=.venv/bin/python bash run_analise_scielo.sh
```

Para incluir a reestimação dos modelos:

```bash
PYTHON_BIN=.venv/bin/python RUN_EXPANDED_MODELS=1 bash run_analise_scielo.sh
```

Os modelos ampliados não integram os resultados atuais. O segundo comando exige `statsmodels` e faz a validação requerer `cenario_latindex_ampliado/06_modelos/modelos_continuidade.txt`.

## 9. Resultados esperados do cenário ampliado

- 3.031 periódicos e 33.065 registros periódico-ano;
- 1.155.089 artigos únicos agregados;
- 421 periódicos SciELO;
- Bradford: 142 no núcleo, 531 na zona 2 e 2.358 na periferia;
- 102 periódicos SciELO no núcleo;
- 104 periódicos originais mudam de zona;
- trajetórias: 1.764 continuantes, 617 transientes, 412 entrantes, 113 retirantes e 125 one-timers.

## 10. Outputs complementares

- `scielo_matches.csv`: auditoria no corpus principal;
- `scielo_titulos_nao_encontrados.csv`: títulos sem match;
- `registros_scielo_adicionados.csv`: proveniência dos 177 registros;
- `latindex_journals_brasileiros_scielo_ampliada.csv`: entrada combinada;
- `cenario_latindex_ampliado/05_resultados/base_analitica_periodicos.csv`: base ampliada;
- `cenario_latindex_ampliado/analise_scielo/`: tabelas SciELO ampliadas;
- `comparacao_cenarios.csv`: comparação original × ampliado;
- `migracao_zonas_periodicos_originais.csv`: mudanças individuais de zona;
- `RESUMO_COMPARACAO_CENARIOS.md`: síntese metodológica.

## 11. Decisões e limitações

- Unidade analítica: periódico agregado por `folio_u`.
- DOI: usar exclusivamente `proporcao_doi`.
- Bradford representa posição na produção observada, não qualidade ou pertencimento à SciELO.
- Trajetórias representam presença observada, não continuidade editorial.
- A situação SciELO corresponde à data da coleta, não necessariamente a todo o período 2000–2024.
- O cenário ampliado é análise de sensibilidade, não atualização oficial do Latindex.
- Atualizações das fontes exigem novos snapshots, auditoria, checksums e valores esperados.

Os arquivos congelados e scripts permitem repetir os resultados atuais. A reconstrução desde as fontes externas ainda depende da documentação histórica da consulta OpenAlex e da exportação Latindex.
