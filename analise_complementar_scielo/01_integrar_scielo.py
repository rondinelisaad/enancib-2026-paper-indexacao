#!/usr/bin/env python3
"""Coleta a lista oficial SciELO Brasil e cruza seus ISSNs com o corpus principal.

Esta etapa e inteiramente complementar: le a base analitica final, coleta metadados
publicos do portal SciELO Brasil e grava somente no diretorio de saida informado.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import html
import re
import time
import unicodedata
from datetime import date
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import pandas as pd


LIST_URL = "https://www.scielo.br/journals/alpha?ilang=pt_BR"
CSV_URL = "https://www.scielo.br/journals/download/alpha/csv/?ilang=pt_BR"
USER_AGENT = "Mozilla/5.0 (compatible; SciELO-complementary-analysis/1.0)"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Integra a lista oficial SciELO Brasil ao corpus.")
    p.add_argument("--base", default="outputs/05_resultados/base_analitica_periodicos.csv")
    p.add_argument("--outdir", default="analise_complementar_scielo")
    p.add_argument("--list-html", help="HTML local opcional da lista oficial SciELO.")
    p.add_argument("--scielo-csv", help="Lista SciELO previamente coletada; evita nova coleta.")
    p.add_argument("--delay", type=float, default=0.05, help="Intervalo entre paginas, em segundos.")
    return p.parse_args()


def normalize_issn(value: object) -> str | None:
    """Mesma regra usada no script 01 do pipeline principal."""
    if pd.isna(value):
        return None
    s = str(value).strip().upper()
    if not s or s in {"[]", "NAN", "NONE", "NULL"}:
        return None
    s = re.sub(r"[^0-9X]", "", s)
    if len(s) != 8:
        return None
    return f"{s[:4]}-{s[4:]}"


def normalize_title(value: object) -> str:
    s = "" if pd.isna(value) else str(value)
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c)).casefold()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def fetch_text(url: str, attempts: int = 3) -> str:
    last: Exception | None = None
    for attempt in range(attempts):
        try:
            req = Request(url, headers={"User-Agent": USER_AGENT})
            with urlopen(req, timeout=15) as response:
                return response.read().decode("utf-8", errors="replace")
        except (HTTPError, URLError, TimeoutError) as exc:
            last = exc
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"Falha ao consultar {url}: {last}")


def strip_tags(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", value))).strip()


def parse_list_page(page: str) -> list[dict[str, str]]:
    rows = re.findall(r'<tr>\s*<td colspan="2">(.*?)</td>\s*</tr>', page, flags=re.S)
    journals: list[dict[str, str]] = []
    for row in rows:
        title_m = re.search(r'<strong class="journalTitle">(.*?)</strong>', row, flags=re.S)
        acr_m = re.search(r'href="/j/([^/]+)/\?ilang=', row)
        if not title_m or not acr_m:
            continue
        if "indexação interrompida" in row:
            status = "indexacao_interrompida"
        elif "(terminado)" in row:
            status = "terminado"
        else:
            status = "corrente"
        continuation = ""
        cont_m = re.search(r'journalPreviousTitle.*?href="/j/([^/]+)/.*?<strong>(.*?)</strong>', row, flags=re.S)
        if cont_m:
            continuation = strip_tags(cont_m.group(2))
        journals.append({
            "scielo_acronimo": acr_m.group(1),
            "titulo_scielo": strip_tags(title_m.group(1)),
            "status_scielo": status,
            "continua_como": continuation,
            "registro_tecnico_invalido": int(
                acr_m.group(1) == "journal_acron" or strip_tags(title_m.group(1)).startswith("title-")
            ),
        })
    if not journals:
        raise ValueError("Nenhum periodico foi extraido da pagina oficial SciELO.")
    return journals


def parse_journal_metadata(page: str) -> dict[str, str]:
    block_m = re.search(r'<span class="issn">(.*?)<!-- Ini - Se houver um outro título-->', page, flags=re.S)
    candidates = []
    print_issn = ""
    online_issn = ""
    if block_m:
        block = block_m.group(1)
        candidates.extend(re.findall(r'(?<!\d)(\d{4}\s*-?\s*[\dXx]{4})(?!\w)', strip_tags(block)))
        for div in re.findall(r"<div>(.*?)</div>", block, flags=re.S):
            values = [x for raw in re.findall(r'(?<!\d)(\d{4}\s*-?\s*[\dXx]{4})(?!\w)', strip_tags(div)) if (x := normalize_issn(raw))]
            if not values:
                continue
            if "impressa" in div.casefold():
                print_issn = values[0]
            elif "on-line" in div.casefold() or "online" in div.casefold():
                online_issn = values[0]
    candidates.extend(re.findall(r'analytics\.scielo\.org/\?journal=([^&" ]+)', page))
    issns = sorted({v for x in candidates if (v := normalize_issn(x))})
    publisher_m = re.search(r'class="namePlublisher">(.*?)</strong>', page, flags=re.S)
    area_m = re.search(r'<span class="area">.*?</span>(.*?)</span>', page, flags=re.S)
    return {
        "issns_scielo": "; ".join(issns),
        "issn_imp_scielo": print_issn,
        "issn_e_scielo": online_issn,
        "editora_scielo": strip_tags(publisher_m.group(1)) if publisher_m else "",
        "area_scielo": strip_tags(area_m.group(1)) if area_m else "",
    }


def parse_journal_issns(page: str) -> set[str]:
    """Compatibilidade para testes e reutilizacao externa."""
    return split_issns(parse_journal_metadata(page)["issns_scielo"])


def collect_scielo(list_html: str, delay: float) -> pd.DataFrame:
    rows = parse_list_page(list_html)
    def enrich(row: dict[str, str]) -> dict[str, str]:
        url = f"https://www.scielo.br/j/{row['scielo_acronimo']}/?ilang=pt_BR"
        try:
            metadata = parse_journal_metadata(fetch_text(url))
            error = ""
        except RuntimeError as exc:
            metadata = {"issns_scielo": "", "issn_imp_scielo": "", "issn_e_scielo": "", "editora_scielo": "", "area_scielo": ""}
            error = str(exc)
        row.update(metadata)
        row["url_scielo"] = url
        row["erro_coleta"] = error
        if delay:
            time.sleep(delay)
        return row

    completed: list[dict[str, str]] = []
    with ThreadPoolExecutor(max_workers=12) as pool:
        futures = [pool.submit(enrich, row.copy()) for row in rows]
        for future in as_completed(futures):
            completed.append(future.result())
    return pd.DataFrame(completed).sort_values("titulo_scielo", key=lambda s: s.str.casefold()).reset_index(drop=True)


def split_issns(value: object) -> set[str]:
    if pd.isna(value):
        return set()
    return {v for part in re.split(r"[;,|]", str(value)) if (v := normalize_issn(part))}


def build_matches(base: pd.DataFrame, scielo: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    issn_index: dict[str, set[int]] = {}
    for i, row in scielo.iterrows():
        if int(row.get("registro_tecnico_invalido", 0)) == 1:
            continue
        for issn in split_issns(row["issns_scielo"]):
            issn_index.setdefault(issn, set()).add(i)
    title_index: dict[str, set[int]] = {}
    for i, title in scielo["titulo_scielo"].items():
        if int(scielo.at[i, "registro_tecnico_invalido"]) == 1:
            continue
        title_index.setdefault(normalize_title(title), set()).add(i)

    audit: list[dict[str, object]] = []
    matched_scielo_rows: set[int] = set()
    for _, row in base.iterrows():
        base_issns = split_issns(row.get("issns"))
        candidate_ids = sorted(set().union(*(issn_index.get(x, set()) for x in base_issns)))
        shared = sorted(x for x in base_issns if issn_index.get(x))
        method = "issn_exato" if candidate_ids else "nenhum"
        status = "match_issn_unico" if len(candidate_ids) == 1 else "match_issn_ambiguo" if candidate_ids else "sem_match"
        note = ""
        if not candidate_ids:
            exact_title = sorted(title_index.get(normalize_title(row.get("Revista")), set()))
            if exact_title:
                status = "sem_match_issn_titulo_exato_para_revisao"
                note = "Titulo normalizado identico; nao classificado como SciELO sem validacao por ISSN."
                candidate_ids = exact_title
                method = "titulo_exato_apenas_candidato"
        if status.startswith("match_issn"):
            matched_scielo_rows.update(candidate_ids)
        selected = scielo.loc[candidate_ids] if candidate_ids else scielo.iloc[0:0]
        audit.append({
            "folio_u": row.get("folio_u", ""),
            "titulo_base": row.get("Revista", ""),
            "issns_base": "; ".join(sorted(base_issns)),
            "titulo_scielo": " | ".join(selected["titulo_scielo"].astype(str)),
            "issns_scielo": " | ".join(selected["issns_scielo"].astype(str)),
            "status_scielo_fonte": " | ".join(selected["status_scielo"].astype(str)),
            "issns_coincidentes": "; ".join(shared),
            "metodo_match": method,
            "status_match": status,
            "scielo": int(status.startswith("match_issn")),
            "observacao": note,
        })
    unmatched = scielo.loc[~scielo.index.isin(matched_scielo_rows)].copy()
    unmatched["observacao"] = "Titulo SciELO sem correspondencia por ISSN no corpus principal."
    return pd.DataFrame(audit), unmatched


def main() -> None:
    args = parse_args()
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    base = pd.read_csv(args.base, dtype=str, low_memory=False)
    required = {"folio_u", "Revista", "issns"}
    missing = required - set(base.columns)
    if missing:
        raise ValueError(f"Colunas ausentes na base principal: {sorted(missing)}")
    if base["folio_u"].duplicated().any():
        raise ValueError("A base principal nao esta no nivel de um registro por folio_u.")

    if args.scielo_csv:
        scielo = pd.read_csv(args.scielo_csv, dtype=str, keep_default_na=False)
    else:
        list_html = Path(args.list_html).read_text(encoding="utf-8") if args.list_html else fetch_text(LIST_URL)
        scielo = collect_scielo(list_html, args.delay)
    if "data_coleta" not in scielo:
        scielo.insert(0, "data_coleta", date.today().isoformat())
    if "fonte_lista" not in scielo:
        scielo.insert(1, "fonte_lista", LIST_URL)
    frozen_output = outdir / "scielo_lista_oficial.csv"
    source_csv = Path(args.scielo_csv).resolve() if args.scielo_csv else None
    if source_csv != frozen_output.resolve():
        scielo.to_csv(frozen_output, index=False, encoding="utf-8-sig")

    matches, unmatched = build_matches(base, scielo)
    matches.to_csv(outdir / "scielo_matches.csv", index=False, encoding="utf-8-sig")
    unmatched.to_csv(outdir / "scielo_titulos_nao_encontrados.csv", index=False, encoding="utf-8-sig")
    print(f"SciELO: {len(scielo)} titulos; corpus: {len(base)} periodicos; matches: {int(matches['scielo'].sum())}.")


if __name__ == "__main__":
    main()
