# Comparação entre o cenário original e o Latindex ampliado com SciELO

## Construção do cenário

O arquivo Latindex original foi preservado. Uma cópia recebeu 177 registros bibliográficos SciELO Brasil cujos ISSNs não estavam no CSV local. Os registros receberam identificadores sintéticos com prefixo `SCIELO-`; campos não disponíveis na fonte permaneceram vazios. O mesmo arquivo OpenAlex e os mesmos scripts, parâmetros, critérios de agregação, DOI, trajetória e Bradford do estudo principal foram utilizados.

Dos 177 registros adicionados, 170 apresentaram presença observada no OpenAlex e 7 não apresentaram. O corpus passou de 2861 para 3031 periódicos e de 1000587 para 1155089 artigos únicos agregados.

## Mudanças gerais

| Indicador | Original | Ampliado |
|---|---:|---:|
| Periódicos | 2861 | 3031 |
| Artigos agregados | 1000587 | 1155089 |
| Núcleo | 128 | 142 |
| Zona 2 | 513 | 531 |
| Periferia | 2220 | 2358 |
| Continuantes | 1620 | 1764 |
| Percentual continuante | 56.62% | 58.20% |
| Proporção DOI média | 0.9535 | 0.9551 |

A recomposição do universo alterou a zona de Bradford de 104 dos 2861 periódicos originais. Isso ocorre porque Bradford é recalculado sobre a distribuição acumulada de artigos do novo universo.

## SciELO no cenário ampliado

Foram identificados 421 periódicos SciELO entre os 3031 periódicos do cenário ampliado (13.89%). No núcleo, 102 de 142 são SciELO (71.83%). Dos 421 SciELO observados, 102 estão no núcleo, 203 na zona 2 e 116 na periferia.

Entre os SciELO, a média de anos com presença observada é 18.74, a média da maior lacuna é 0.43, a cobertura média de DOI é 0.9859 e 84.09% foram classificados como continuantes.

## Interpretação e cautelas

Este resultado é uma análise de sensibilidade baseada em uma base ampliada, não uma correção silenciosa da análise principal. A inclusão dos registros SciELO muda o universo e, consequentemente, as zonas de Bradford. Os 177 títulos não foram validados como integrantes do arquivo Latindex histórico usado originalmente; foram adicionados a partir da fonte SciELO para avaliar o efeito de sua omissão.

A presença observada continua restrita aos trabalhos do OpenAlex entre 2000 e 2024 com ao menos um autor afiliado a instituição brasileira. Ausência nesse recorte não implica descontinuidade editorial. As comparações são descritivas e não causais.
