#!/usr/bin/env python3
"""Compara o corpus original com o cenario Latindex ampliado pela lista SciELO."""

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "analise_complementar_scielo"
NEW = OUT / "cenario_latindex_ampliado"


def metrics(base: pd.DataFrame, scenario: str) -> dict[str, object]:
    numeric = ["total_artigos", "proporcao_doi", "anos_com_indexacao", "lacuna_maxima"]
    for col in numeric:
        base[col] = pd.to_numeric(base[col], errors="coerce")
    return {
        "cenario": scenario,
        "periodicos": base["folio_u"].nunique(),
        "artigos": int(base["total_artigos"].sum()),
        "nucleo": int((base["zona_bradford"] == "núcleo").sum()),
        "zona_2": int((base["zona_bradford"] == "zona 2").sum()),
        "periferia": int((base["zona_bradford"] == "periferia").sum()),
        "continuantes": int((base["categoria_continuidade"] == "continuante").sum()),
        "continuantes_pct": round((base["categoria_continuidade"] == "continuante").mean() * 100, 2),
        "proporcao_doi_media": round(base["proporcao_doi"].mean(), 4),
        "anos_medios_presenca": round(base["anos_com_indexacao"].mean(), 4),
        "media_lacuna_maxima": round(base["lacuna_maxima"].mean(), 4),
    }


def main() -> None:
    original = pd.read_csv(ROOT / "outputs/05_resultados/base_analitica_periodicos.csv", dtype={"folio_u": str})
    expanded = pd.read_csv(NEW / "05_resultados/base_analitica_periodicos.csv", dtype={"folio_u": str})
    additions = pd.read_csv(OUT / "registros_scielo_adicionados.csv", dtype=str)
    scielo_table = pd.read_csv(NEW / "analise_scielo/tabela_scielo_bradford.csv")
    scielo_ind = pd.read_csv(NEW / "analise_scielo/tabela_scielo_indicadores.csv")

    comparison = pd.DataFrame([metrics(original.copy(), "original"), metrics(expanded.copy(), "latindex_ampliado_scielo")])
    comparison.to_csv(NEW / "comparacao_cenarios.csv", index=False, encoding="utf-8-sig")

    original_zones = original[["folio_u", "zona_bradford"]].rename(columns={"zona_bradford": "zona_original"})
    expanded_zones = expanded[["folio_u", "zona_bradford"]].rename(columns={"zona_bradford": "zona_ampliada"})
    migration = original_zones.merge(expanded_zones, on="folio_u", how="left", validate="one_to_one")
    migration["mudou_zona"] = migration["zona_original"] != migration["zona_ampliada"]
    migration.to_csv(NEW / "migracao_zonas_periodicos_originais.csv", index=False, encoding="utf-8-sig")
    migration_table = pd.crosstab(migration["zona_original"], migration["zona_ampliada"], margins=True)
    migration_table.to_csv(NEW / "tabela_migracao_zonas.csv", encoding="utf-8-sig")

    added_ids = set(additions["folio_u_sintetico"])
    added_observed = expanded[expanded["folio_u"].isin(added_ids)]
    not_observed = additions[~additions["folio_u_sintetico"].isin(set(expanded["folio_u"]))]
    not_observed.to_csv(NEW / "registros_scielo_adicionados_sem_presenca_openalex.csv", index=False, encoding="utf-8-sig")
    core = scielo_table[scielo_table["zona_bradford"] == "núcleo"].iloc[0]
    sci = scielo_ind[scielo_ind["grupo"] == "SciELO"].iloc[0]
    changed = int(migration["mudou_zona"].sum())
    o, n = comparison.iloc[0], comparison.iloc[1]

    text = f"""# Comparação entre o cenário original e o Latindex ampliado com SciELO

## Construção do cenário

O arquivo Latindex original foi preservado. Uma cópia recebeu 177 registros bibliográficos SciELO Brasil cujos ISSNs não estavam no CSV local. Os registros receberam identificadores sintéticos com prefixo `SCIELO-`; campos não disponíveis na fonte permaneceram vazios. O mesmo arquivo OpenAlex e os mesmos scripts, parâmetros, critérios de agregação, DOI, trajetória e Bradford do estudo principal foram utilizados.

Dos 177 registros adicionados, {len(added_observed)} apresentaram presença observada no OpenAlex e {len(not_observed)} não apresentaram. O corpus passou de {int(o.periodicos)} para {int(n.periodicos)} periódicos e de {int(o.artigos)} para {int(n.artigos)} artigos únicos agregados.

## Mudanças gerais

| Indicador | Original | Ampliado |
|---|---:|---:|
| Periódicos | {int(o.periodicos)} | {int(n.periodicos)} |
| Artigos agregados | {int(o.artigos)} | {int(n.artigos)} |
| Núcleo | {int(o.nucleo)} | {int(n.nucleo)} |
| Zona 2 | {int(o.zona_2)} | {int(n.zona_2)} |
| Periferia | {int(o.periferia)} | {int(n.periferia)} |
| Continuantes | {int(o.continuantes)} | {int(n.continuantes)} |
| Percentual continuante | {o.continuantes_pct:.2f}% | {n.continuantes_pct:.2f}% |
| Proporção DOI média | {o.proporcao_doi_media:.4f} | {n.proporcao_doi_media:.4f} |

A recomposição do universo alterou a zona de Bradford de {changed} dos {len(migration)} periódicos originais. Isso ocorre porque Bradford é recalculado sobre a distribuição acumulada de artigos do novo universo.

## SciELO no cenário ampliado

Foram identificados 421 periódicos SciELO entre os {int(n.periodicos)} periódicos do cenário ampliado ({421/int(n.periodicos)*100:.2f}%). No núcleo, {int(core['SciELO'])} de {int(core['Total'])} são SciELO ({core['pct_scielo_na_zona']:.2f}%). Dos 421 SciELO observados, {int(scielo_table.iloc[0]['SciELO'])} estão no núcleo, {int(scielo_table.iloc[1]['SciELO'])} na zona 2 e {int(scielo_table.iloc[2]['SciELO'])} na periferia.

Entre os SciELO, a média de anos com presença observada é {sci.anos_medios_com_presenca:.2f}, a média da maior lacuna é {sci.media_lacuna_maxima:.2f}, a cobertura média de DOI é {sci.cobertura_media_doi:.4f} e {sci.continuantes_pct:.2f}% foram classificados como continuantes.

## Interpretação e cautelas

Este resultado é uma análise de sensibilidade baseada em uma base ampliada, não uma correção silenciosa da análise principal. A inclusão dos registros SciELO muda o universo e, consequentemente, as zonas de Bradford. Os 177 títulos não foram validados como integrantes do arquivo Latindex histórico usado originalmente; foram adicionados a partir da fonte SciELO para avaliar o efeito de sua omissão.

A presença observada continua restrita aos trabalhos do OpenAlex entre 2000 e 2024 com ao menos um autor afiliado a instituição brasileira. Ausência nesse recorte não implica descontinuidade editorial. As comparações são descritivas e não causais.
"""
    (NEW / "RESUMO_COMPARACAO_CENARIOS.md").write_text(text, encoding="utf-8")
    print(f"Comparacao concluida; {changed} periodicos originais mudaram de zona.")


if __name__ == "__main__":
    main()
