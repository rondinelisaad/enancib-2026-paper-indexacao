# Reprodutibilidade do estudo

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.19355940.svg)](https://doi.org/10.5281/zenodo.19355940)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
![Reprodutibilidade](https://img.shields.io/badge/Reprodutível-Pipeline%20completo%20%2B%20Zenodo-blue)

Este repositório contém um pipeline totalmente reprodutível para análise da continuidade da presença de periódicos brasileiros no OpenAlex (2000–2024).

---

## 1. Escopo

O pipeline reproduz:

- construção da base analítica por periódico
- cálculo de indicadores de continuidade observada
- cálculo da proporção de DOI
- classificação estrutural (Bradford)
- geração das tabelas analíticas
- estimação de modelos estatísticos (OLS e logit)

---

## 2. Dados de entrada

Os dados utilizados não correspondem ao universo completo da produção científica, mas a um recorte específico:

- **OpenAlex:** artigos com pelo menos um autor com afiliação brasileira
- **Latindex:** periódicos brasileiros

Os datasets completos utilizados estão disponíveis em:

> 👉 https://doi.org/10.5281/zenodo.19355939

Arquivos principais:

- `openalex_BR_2000_2024_tratado.csv`
- `latindex-journals-brasileiros.csv`

---

## 3. Estrutura do pipeline

O pipeline é executado de forma sequencial:

1. Cruzamento OpenAlex × Latindex (ISSN)
2. Construção da base periódico-ano
3. Cálculo da proporção de DOI
4. Classificação estrutural (Bradford)
5. Geração das tabelas analíticas
6. Modelagem estatística

Todos os passos são executados via:

```bash
bash run_pipeline.sh
```

---

## 4. Ambiente

Requisitos:

- Python 3.9+

**Instalação das dependências:**

```bash
pip install -r requirements.txt
```

Principais bibliotecas:

- `pandas`
- `statsmodels`

---

## 5. Execução

**Execução padrão:**

```bash
bash run_pipeline.sh
```

**Execução com caminhos customizados:**

```bash
OPENALEX_INPUT="caminho/openalex.csv" \
LATINDEX_INPUT="caminho/latindex.csv" \
OUTPUT_DIR="caminho/outputs" \
bash run_pipeline.sh
```

---

## 6. Outputs esperados

Após execução completa:

```
outputs/
├── 01_crossmatch/
├── 02_classificacao/
├── 03_doi/
├── 04_bradford/
├── 05_resultados/
│   ├── base_analitica_periodicos.csv
│   ├── tabela_*.csv
│   └── resumo_resultados.txt
├── 06_modelos/
│   └── modelos_continuidade.txt
└── logs/
```

Resultados principais:

- ~2.800 periódicos analisados
- ~1.000.000 artigos agregados
- distribuição de Bradford em três zonas
- associação entre posição estrutural e continuidade observada

---

## 7. Validação dos resultados

Após execução, verificar:

- número de periódicos: ~2861
- registros periódico-ano: ~30133
- ausência de perdas no merge final
- geração de todos os arquivos CSV e TXT

---

## 8. Interpretação

**Os resultados devem ser interpretados como:**

- padrões de continuidade da presença observada no OpenAlex
- associações entre posição estrutural e continuidade
- efeito complementar da proporção de DOI

**Não devem ser interpretados como:**

- prova de desaparecimento de periódicos
- medida completa da produção editorial
- relações causais

---

## 9. Limitações da reprodução

- OpenAlex é usado como proxy de presença no recorte analisado
- o recorte inclui apenas produção com afiliação brasileira
- a proporção de DOI é calculada sobre o conjunto observado
- a deduplicação de artigos usa chave sintética (DOI + título + ano)
- a classificação de Bradford depende da distribuição observada

---

## 10. Reprodutibilidade e versionamento

- Código versionado no GitHub
- Dados com DOI no Zenodo
- Pipeline determinístico (sem uso de aleatoriedade)

Para garantir reprodutibilidade total:

- utilizar os mesmos datasets
- manter versões das dependências
