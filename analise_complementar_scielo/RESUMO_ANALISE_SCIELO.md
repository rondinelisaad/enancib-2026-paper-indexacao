# Análise complementar SciELO Brasil

## Fonte e definição operacional

A lista foi coletada em 2026-09-06 na lista alfabética oficial da Coleção SciELO Brasil: https://www.scielo.br/journals/alpha?ilang=pt_BR. A página retornou 432 registros: 429 registros bibliográficos válidos e 3 registros técnicos anômalos do portal, preservados na auditoria mas impedidos de gerar correspondências. Segundo a situação exibida pela fonte, há 334 registros correntes, 48 com indexação interrompida e 50 terminados. A fonte se refere exclusivamente à coleção Brasil, e não à SciELO Network.

A variável `scielo` indica correspondência exata de pelo menos um ISSN normalizado entre o periódico agregado do corpus e um título da lista oficial. Ela não indica pertencimento contínuo durante 2000–2024. O status corrente ou não corrente foi preservado como atributo da fonte. Títulos sem coincidência de ISSN não foram classificados automaticamente por semelhança textual.

## Correspondência

Foram identificados 251 periódicos SciELO entre os 2861 periódicos do corpus (8,77%). O cruzamento produziu 0 correspondências por ISSN envolvendo mais de um título SciELO e 2 candidatos de título exato sem confirmação por ISSN. As 3 falhas de coleta correspondem exclusivamente aos registros técnicos anômalos; os 429 registros bibliográficos válidos tiveram pelo menos um ISSN recuperado.

Candidatos reservados para validação manual: Educação em Revista (folio_u 25437; ISSNs da base: 2236-5192; ISSNs SciELO: 0102-4698; 1982-6621); Movimento (folio_u 23161; ISSNs da base: 1518-0344; 2359-3296; ISSNs SciELO: 0104-754X; 1982-8918).

## Bradford

Dos 128 periódicos do núcleo, 84 pertencem à coleção SciELO Brasil (65,62% do núcleo). Entre os periódicos SciELO encontrados no corpus, 84 (33,47%) estão no núcleo, 112 (44,62%) na zona 2 e 55 (21,91%) na periferia.

As zonas de Bradford representam posição na distribuição da produção observada. O pertencimento à SciELO representa inclusão em uma coleção com critérios próprios; as classificações não são equivalentes.

## Indicadores descritivos

Os periódicos SciELO apresentam média de 19.75 anos com presença observada e mediana de 22.00; entre os não SciELO, os valores são 9.65 e 9.00. A média da maior lacuna observada é 0.33 para SciELO e 0.85 para não SciELO.

A cobertura média de DOI (`proporcao_doi`) é 0.9890 entre SciELO e 0.9501 entre não SciELO; as medianas são 1.0000 e 1.0000. A proporção classificada como continuante é 83,67% entre SciELO e 54,02% entre não SciELO.

Esses resultados descrevem associações e distribuições da presença observada no corpus. Não permitem inferir continuidade editorial, qualidade ou efeito causal da SciELO.

## Limitações

- A lista oficial consultada é uma fotografia da coleção na data da coleta, embora inclua títulos não correntes e relações históricas de títulos.
- Não foi reconstruída uma série anual de entrada e saída da coleção entre 2000 e 2024.
- Mudanças de título e de ISSN podem produzir mais de um registro SciELO para uma mesma linhagem editorial; a auditoria mantém os casos observados.
- A ausência no corpus significa somente ausência no recorte OpenAlex analisado, não descontinuidade editorial.
- Correspondências por título sem ISSN coincidente permanecem como candidatos para validação manual e não entram nas estatísticas SciELO.

## Resultados adequados para o artigo

São suficientemente robustos para apresentação: o número de periódicos com correspondência exata por ISSN; a composição SciELO de cada zona; a distribuição dos periódicos SciELO entre as zonas; e as estatísticas descritivas por grupo, sempre acompanhadas da definição operacional e das limitações acima. Casos ambíguos ou candidatos por título devem ser validados antes da versão final do manuscrito.
