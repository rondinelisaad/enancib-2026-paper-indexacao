#!/usr/bin/env python3
"""Produz tabelas descritivas da analise complementar SciELO Brasil."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


ZONE_ORDER = ["núcleo", "zona 2", "periferia"]
TRAJECTORY_ORDER = ["continuante", "transiente", "entrante", "retirante", "one-timer"]
LIST_URL = "https://www.scielo.br/journals/alpha?ilang=pt_BR"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Analisa SciELO versus nao SciELO no corpus.")
    p.add_argument("--base", default="outputs/05_resultados/base_analitica_periodicos.csv")
    p.add_argument("--matches", default="analise_complementar_scielo/scielo_matches.csv")
    p.add_argument("--scielo-list", default="analise_complementar_scielo/scielo_lista_oficial.csv")
    p.add_argument("--outdir", default="analise_complementar_scielo")
    return p.parse_args()


def fmt_pct(value: float) -> str:
    return f"{value:.2f}%".replace(".", ",")


def main() -> None:
    args = parse_args()
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    base = pd.read_csv(args.base, low_memory=False)
    matches = pd.read_csv(args.matches, dtype={"folio_u": str}, low_memory=False)
    scielo_list = pd.read_csv(args.scielo_list, low_memory=False)
    required = {"folio_u", "zona_bradford", "categoria_continuidade", "anos_com_indexacao", "lacuna_maxima", "proporcao_doi"}
    missing = required - set(base.columns)
    if missing:
        raise ValueError(f"Colunas ausentes na base analitica: {sorted(missing)}")
    if len(base) != base["folio_u"].nunique() or len(matches) != matches["folio_u"].nunique():
        raise ValueError("Base ou auditoria fora do nivel de periodico agregado.")
    base["folio_u"] = base["folio_u"].astype(str)
    analysis = base.merge(matches[["folio_u", "scielo", "status_match"]], on="folio_u", how="left", validate="one_to_one")
    if analysis["scielo"].isna().any():
        raise ValueError("Ha periodicos sem classificacao SciELO apos o merge.")
    analysis["grupo_scielo"] = analysis["scielo"].map({1: "SciELO", 0: "Não SciELO"})

    cross = pd.crosstab(analysis["zona_bradford"], analysis["grupo_scielo"]).reindex(ZONE_ORDER, fill_value=0)
    for col in ["SciELO", "Não SciELO"]:
        if col not in cross:
            cross[col] = 0
    cross = cross[["SciELO", "Não SciELO"]]
    cross["Total"] = cross.sum(axis=1)
    cross["pct_scielo_na_zona"] = (cross["SciELO"] / cross["Total"] * 100).round(2)
    cross["pct_nao_scielo_na_zona"] = (cross["Não SciELO"] / cross["Total"] * 100).round(2)
    cross["pct_dos_scielo_nesta_zona"] = (cross["SciELO"] / cross["SciELO"].sum() * 100).round(2)
    cross["pct_dos_nao_scielo_nesta_zona"] = (cross["Não SciELO"] / cross["Não SciELO"].sum() * 100).round(2)
    total = pd.DataFrame({
        "SciELO": [cross["SciELO"].sum()], "Não SciELO": [cross["Não SciELO"].sum()], "Total": [cross["Total"].sum()],
        "pct_scielo_na_zona": [round(cross["SciELO"].sum() / cross["Total"].sum() * 100, 2)],
        "pct_nao_scielo_na_zona": [round(cross["Não SciELO"].sum() / cross["Total"].sum() * 100, 2)],
        "pct_dos_scielo_nesta_zona": [100.0], "pct_dos_nao_scielo_nesta_zona": [100.0],
    }, index=["Total"])
    cross = pd.concat([cross, total]).reset_index(names="zona_bradford")
    cross.to_csv(outdir / "tabela_scielo_bradford.csv", index=False, encoding="utf-8-sig")

    traj_n = pd.crosstab(analysis["categoria_continuidade"], analysis["grupo_scielo"]).reindex(TRAJECTORY_ORDER, fill_value=0)
    for col in ["SciELO", "Não SciELO"]:
        if col not in traj_n:
            traj_n[col] = 0
    traj = traj_n.reset_index().rename(columns={"categoria_continuidade": "trajetoria", "SciELO": "scielo_n", "Não SciELO": "nao_scielo_n"})
    traj["total_n"] = traj["scielo_n"] + traj["nao_scielo_n"]
    traj["scielo_pct_no_grupo"] = (traj["scielo_n"] / traj["scielo_n"].sum() * 100).round(2)
    traj["nao_scielo_pct_no_grupo"] = (traj["nao_scielo_n"] / traj["nao_scielo_n"].sum() * 100).round(2)
    traj["scielo_pct_na_trajetoria"] = (traj["scielo_n"] / traj["total_n"] * 100).round(2)
    traj = traj[["trajetoria", "scielo_n", "nao_scielo_n", "total_n", "scielo_pct_no_grupo", "nao_scielo_pct_no_grupo", "scielo_pct_na_trajetoria"]]
    traj.to_csv(outdir / "tabela_scielo_trajetorias.csv", index=False, encoding="utf-8-sig")

    rows = []
    for group in ["SciELO", "Não SciELO", "Total"]:
        d = (analysis if group == "Total" else analysis[analysis["grupo_scielo"] == group]).copy()
        for col in ["anos_com_indexacao", "lacuna_maxima", "proporcao_doi"]:
            d[col] = pd.to_numeric(d[col], errors="coerce")
        rows.append({
            "grupo": group,
            "periodicos": d["folio_u"].nunique(),
            "anos_medios_com_presenca": round(d["anos_com_indexacao"].mean(), 4),
            "mediana_anos_com_presenca": round(d["anos_com_indexacao"].median(), 4),
            "media_lacuna_maxima": round(d["lacuna_maxima"].mean(), 4),
            "cobertura_media_doi": round(d["proporcao_doi"].mean(), 4),
            "mediana_cobertura_doi": round(d["proporcao_doi"].median(), 4),
            "continuantes_n": int((d["categoria_continuidade"] == "continuante").sum()),
            "continuantes_pct": round((d["categoria_continuidade"] == "continuante").mean() * 100, 2),
        })
    indicators = pd.DataFrame(rows)
    indicators.to_csv(outdir / "tabela_scielo_indicadores.csv", index=False, encoding="utf-8-sig")

    n_total = len(analysis)
    n_scielo = int(analysis["scielo"].sum())
    core = cross[cross["zona_bradford"] == "núcleo"].iloc[0]
    source_date = str(scielo_list["data_coleta"].iloc[0])
    status_counts = scielo_list["status_scielo"].value_counts().to_dict()
    ambiguous = int((matches["status_match"] == "match_issn_ambiguo").sum())
    title_candidates = int((matches["status_match"] == "sem_match_issn_titulo_exato_para_revisao").sum())
    candidate_rows = matches[matches["status_match"] == "sem_match_issn_titulo_exato_para_revisao"]
    candidate_details = "; ".join(
        f"{row.titulo_base} (folio_u {row.folio_u}; ISSNs da base: {row.issns_base}; ISSNs SciELO: {row.issns_scielo})"
        for row in candidate_rows.itertuples()
    ) or "nenhum"
    failed_metadata = int((scielo_list["erro_coleta"].fillna("") != "").sum())
    ind = indicators.set_index("grupo")
    technical_records = int(scielo_list["registro_tecnico_invalido"].sum())
    bibliographic_records = len(scielo_list) - technical_records
    summary = f"""# Análise complementar SciELO Brasil

## Fonte e definição operacional

A lista foi coletada em {source_date} na lista alfabética oficial da Coleção SciELO Brasil: {LIST_URL}. A página retornou {len(scielo_list)} registros: {bibliographic_records} registros bibliográficos válidos e {technical_records} registros técnicos anômalos do portal, preservados na auditoria mas impedidos de gerar correspondências. Segundo a situação exibida pela fonte, há {status_counts.get('corrente', 0)} registros correntes, {status_counts.get('indexacao_interrompida', 0)} com indexação interrompida e {status_counts.get('terminado', 0)} terminados. A fonte se refere exclusivamente à coleção Brasil, e não à SciELO Network.

A variável `scielo` indica correspondência exata de pelo menos um ISSN normalizado entre o periódico agregado do corpus e um título da lista oficial. Ela não indica pertencimento contínuo durante 2000–2024. O status corrente ou não corrente foi preservado como atributo da fonte. Títulos sem coincidência de ISSN não foram classificados automaticamente por semelhança textual.

## Correspondência

Foram identificados {n_scielo} periódicos SciELO entre os {n_total} periódicos do corpus ({fmt_pct(n_scielo / n_total * 100)}). O cruzamento produziu {ambiguous} correspondências por ISSN envolvendo mais de um título SciELO e {title_candidates} candidatos de título exato sem confirmação por ISSN. As {failed_metadata} falhas de coleta correspondem exclusivamente aos registros técnicos anômalos; os {bibliographic_records} registros bibliográficos válidos tiveram pelo menos um ISSN recuperado.

Candidatos reservados para validação manual: {candidate_details}.

## Bradford

Dos 128 periódicos do núcleo, {int(core['SciELO'])} pertencem à coleção SciELO Brasil ({fmt_pct(float(core['pct_scielo_na_zona']))} do núcleo). Entre os periódicos SciELO encontrados no corpus, {int(cross.iloc[0]['SciELO'])} ({fmt_pct(float(cross.iloc[0]['pct_dos_scielo_nesta_zona']))}) estão no núcleo, {int(cross.iloc[1]['SciELO'])} ({fmt_pct(float(cross.iloc[1]['pct_dos_scielo_nesta_zona']))}) na zona 2 e {int(cross.iloc[2]['SciELO'])} ({fmt_pct(float(cross.iloc[2]['pct_dos_scielo_nesta_zona']))}) na periferia.

As zonas de Bradford representam posição na distribuição da produção observada. O pertencimento à SciELO representa inclusão em uma coleção com critérios próprios; as classificações não são equivalentes.

## Indicadores descritivos

Os periódicos SciELO apresentam média de {ind.loc['SciELO', 'anos_medios_com_presenca']:.2f} anos com presença observada e mediana de {ind.loc['SciELO', 'mediana_anos_com_presenca']:.2f}; entre os não SciELO, os valores são {ind.loc['Não SciELO', 'anos_medios_com_presenca']:.2f} e {ind.loc['Não SciELO', 'mediana_anos_com_presenca']:.2f}. A média da maior lacuna observada é {ind.loc['SciELO', 'media_lacuna_maxima']:.2f} para SciELO e {ind.loc['Não SciELO', 'media_lacuna_maxima']:.2f} para não SciELO.

A cobertura média de DOI (`proporcao_doi`) é {ind.loc['SciELO', 'cobertura_media_doi']:.4f} entre SciELO e {ind.loc['Não SciELO', 'cobertura_media_doi']:.4f} entre não SciELO; as medianas são {ind.loc['SciELO', 'mediana_cobertura_doi']:.4f} e {ind.loc['Não SciELO', 'mediana_cobertura_doi']:.4f}. A proporção classificada como continuante é {fmt_pct(ind.loc['SciELO', 'continuantes_pct'])} entre SciELO e {fmt_pct(ind.loc['Não SciELO', 'continuantes_pct'])} entre não SciELO.

Esses resultados descrevem associações e distribuições da presença observada no corpus. Não permitem inferir continuidade editorial, qualidade ou efeito causal da SciELO.

## Limitações

- A lista oficial consultada é uma fotografia da coleção na data da coleta, embora inclua títulos não correntes e relações históricas de títulos.
- Não foi reconstruída uma série anual de entrada e saída da coleção entre 2000 e 2024.
- Mudanças de título e de ISSN podem produzir mais de um registro SciELO para uma mesma linhagem editorial; a auditoria mantém os casos observados.
- A ausência no corpus significa somente ausência no recorte OpenAlex analisado, não descontinuidade editorial.
- Correspondências por título sem ISSN coincidente permanecem como candidatos para validação manual e não entram nas estatísticas SciELO.

## Resultados adequados para o artigo

São suficientemente robustos para apresentação: o número de periódicos com correspondência exata por ISSN; a composição SciELO de cada zona; a distribuição dos periódicos SciELO entre as zonas; e as estatísticas descritivas por grupo, sempre acompanhadas da definição operacional e das limitações acima. Casos ambíguos ou candidatos por título devem ser validados antes da versão final do manuscrito.
"""
    (outdir / "RESUMO_ANALISE_SCIELO.md").write_text(summary, encoding="utf-8")
    print(f"Analise concluida: {n_scielo} periodicos SciELO em {n_total}.")


if __name__ == "__main__":
    main()
