"""
Mercati d'Italia — Scraper: eventiesagre.it

EventieSagre is the most structured source. Its URL pattern:
  List:   https://www.eventiesagre.it/cerca/Mercatini/{sezione}/mesi/{Regione}/prov/cit/rilib
  Detail: https://www.eventiesagre.it/Mercatini_{sezione}/{id}_{Slug}.html

Sections: Antiquariato, Artigianato, Collezionismo, Usato, Enogastronomici, Filiera Corta, Vari, hobbisti creativi

We scrape the listing pages to get URLs, then each detail page for full data.
"""
import re
import time
import httpx
from bs4 import BeautifulSoup
from typing import Generator
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from config import (
    RawMarket, SCRAPE_DELAY_SECONDS, SCRAPE_MAX_PAGES_PER_REGION,
    REQUEST_TIMEOUT, USER_AGENT
)

console = Console()

# ─── Section ↔ URL mapping ───────────────────────────────────

SECTIONS = {
    "Antiquariato": "Antiquariato",
    "Artigianato": "Artigianato",
    "Collezionismo": "Collezionismo",
    "Usato": "Usato",
    "Enogastronomici": "Enogastronomici",
    "Filiera Corta": "Filiera+Corta",
    "Vari": "Vari",
}

# Regione name → URL segment
REGIONI_URL = {
    "Abruzzo": "Abruzzo",
    "Basilicata": "Basilicata",
    "Calabria": "Calabria",
    "Campania": "Campania",
    "Emilia-Romagna": "Emilia+Romagna",
    "Friuli Venezia Giulia": "Friuli+Venezia+Giulia",
    "Lazio": "Lazio",
    "Liguria": "Liguria",
    "Lombardia": "Lombardia",
    "Marche": "Marche",
    "Molise": "Molise",
    "Piemonte": "Piemonte",
    "Puglia": "Puglia",
    "Sardegna": "Sardegna",
    "Sicilia": "Sicilia",
    "Toscana": "Toscana",
    "Trentino-Alto Adige": "Trentino+Alto+Adige",
    "Umbria": "Umbria",
    "Valle d'Aosta": "Valle+D%27aosta",
    "Veneto": "Veneto",
}

BASE_URL = "https://www.eventiesagre.it"

# ─── HTTP client ─────────────────────────────────────────────

def _get_client() -> httpx.Client:
    return httpx.Client(
        timeout=REQUEST_TIMEOUT,
        headers={"User-Agent": USER_AGENT},
        follow_redirects=True,
    )


# ─── List page scraping ─────────────────────────────────────

def scrape_listing_page(client: httpx.Client, url: str) -> tuple[list[str], str | None]:
    """
    Scrape a listing page for market detail URLs and the next page URL.
    Returns (detail_urls, next_page_url_or_none).
    """
    try:
        resp = client.get(url)
        resp.raise_for_status()
    except httpx.HTTPError as e:
        console.print(f"[red]HTTP error fetching {url}: {e}[/red]")
        return [], None

    soup = BeautifulSoup(resp.text, "lxml")
    detail_urls = []

    # Event links typically match /Mercatini_*/*.html
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "/Mercatini_" in href and href.endswith(".html"):
            full_url = href if href.startswith("http") else BASE_URL + href
            if full_url not in detail_urls:
                detail_urls.append(full_url)

    # Pagination: look for "Avanti" or ">" link
    next_url = None
    for a in soup.find_all("a", href=True):
        text = a.get_text(strip=True).lower()
        if text in ("avanti", "›", ">", "prossima", "successiva"):
            next_href = a["href"]
            next_url = next_href if next_href.startswith("http") else BASE_URL + next_href
            break

    return detail_urls, next_url


# ─── Detail page scraping ───────────────────────────────────

def scrape_detail_page(client: httpx.Client, url: str, regione: str, section: str) -> RawMarket | None:
    """
    Scrape a single market detail page and extract structured data.
    """
    try:
        resp = client.get(url)
        resp.raise_for_status()
    except httpx.HTTPError as e:
        console.print(f"[red]HTTP error fetching {url}: {e}[/red]")
        return None

    soup = BeautifulSoup(resp.text, "lxml")

    # ── Extract name ──
    nome = ""
    h1 = soup.find("h1")
    if h1:
        nome = h1.get_text(strip=True)
    if not nome:
        title = soup.find("title")
        if title:
            nome = title.get_text(strip=True).split("|")[0].strip()

    if not nome:
        return None

    # ── Extract body text ──
    body_text = ""
    # Try common content containers
    for selector in [".testo_evento", ".descrizione", ".corpo", "article", ".content"]:
        el = soup.select_one(selector)
        if el:
            body_text = el.get_text(separator=" ", strip=True)
            break
    if not body_text:
        # Fallback: grab all paragraph text
        paras = soup.find_all("p")
        body_text = " ".join(p.get_text(strip=True) for p in paras[:10])

    # ── Extract city and province ──
    citta, provincia = _extract_location(soup, body_text)

    # ── Extract dates ──
    date_raw = _extract_dates(soup, body_text)

    # ── Extract hours ──
    orario = _extract_hours(soup, body_text)

    # ── Extract recurrence ──
    ricorrenza = _extract_recurrence(body_text)

    # ── Extract address ──
    indirizzo = _extract_address(soup, body_text)

    # ── Extract description ──
    descrizione = _clean_description(body_text, nome)

    return RawMarket(
        nome=nome,
        citta=citta,
        provincia=provincia,
        regione=regione,
        indirizzo=indirizzo,
        categoria_raw=section,
        descrizione=descrizione,
        orario_raw=orario,
        ricorrenza_raw=ricorrenza,
        date_raw=date_raw,
        tags_raw=[],
        url_fonte=url,
        fonte_nome="eventiesagre.it",
    )


# ─── Extraction helpers ─────────────────────────────────────

def _extract_location(soup: BeautifulSoup, body: str) -> tuple[str, str]:
    """Extract city and province code from the page."""
    citta, provincia = "", ""

    # Look for structured location elements
    for selector in [".luogo", ".localita", ".citta"]:
        el = soup.select_one(selector)
        if el:
            text = el.get_text(strip=True)
            # Pattern: "Firenze (FI)" or "Firenze - FI"
            match = re.search(r"([A-Za-zÀ-ú\s']+)\s*[\(\-]\s*([A-Z]{2})\s*\)?", text)
            if match:
                return match.group(1).strip(), match.group(2)
            citta = text
            break

    # Try from breadcrumb or path
    for a in soup.find_all("a", href=True):
        text = a.get_text(strip=True)
        # Pattern: "Toscana > Firenze (FI) > ..."
        match = re.search(r"([A-Za-zÀ-ú\s']+)\s*\(([A-Z]{2})\)", text)
        if match:
            citta = match.group(1).strip()
            provincia = match.group(2)
            break

    # Try from body text
    if not citta:
        match = re.search(r"(?:a|in|di)\s+([A-Z][a-zà-ú]+(?:\s[A-Z][a-zà-ú]+)*)\s*[\(\-]\s*([A-Z]{2})", body)
        if match:
            citta = match.group(1).strip()
            provincia = match.group(2)

    return citta, provincia


def _extract_dates(soup: BeautifulSoup, body: str) -> list[str]:
    """Extract date strings from the page."""
    dates = []

    # Look for structured date elements
    for selector in [".data_evento", ".date", "time", "[datetime]"]:
        for el in soup.select(selector):
            text = el.get("datetime", "") or el.get_text(strip=True)
            if text:
                dates.append(text)

    # Extract from body: DD/MM/YYYY patterns
    for match in re.findall(r"\d{1,2}/\d{1,2}/\d{2,4}", body):
        dates.append(match)

    # Also try: "Dal DD/MM al DD/MM/YYYY"
    dal_al = re.findall(r"[Dd]al\s+(\d{1,2}/\d{1,2}(?:/\d{2,4})?)\s+[Aa]l\s+(\d{1,2}/\d{1,2}/\d{2,4})", body)
    for start, end in dal_al:
        dates.extend([start, end])

    return list(set(dates))


def _extract_hours(soup: BeautifulSoup, body: str) -> str:
    """Extract opening hours from the page."""
    # Structured element
    for selector in [".orario", ".orari", ".time"]:
        el = soup.select_one(selector)
        if el:
            return el.get_text(strip=True)

    # Regex patterns in body
    patterns = [
        r"(?:dalle?\s+)?(\d{1,2}[.:]\d{2})\s*[-–]\s*(\d{1,2}[.:]\d{2})",
        r"ore\s+(\d{1,2}[.:]\d{2})\s*[-–]\s*(\d{1,2}[.:]\d{2})",
        r"dalle\s+(\d{1,2})\s+alle\s+(\d{1,2})",
    ]
    for pattern in patterns:
        match = re.search(pattern, body)
        if match:
            return match.group(0)

    return ""


def _extract_recurrence(body: str) -> str:
    """Extract recurrence pattern from body text."""
    patterns = [
        r"[Oo]gni\s+(?:prima|seconda|terza|quarta|ultima|1[ªa°]|2[ªa°]|3[ªa°]|4[ªa°])\s+\w+\s+del\s+mese",
        r"[Oo]gni\s+(?:luned[ìi]|marted[ìi]|mercoled[ìi]|gioved[ìi]|venerd[ìi]|sabato|domenica)",
        r"[Tt]utti\s+i\s+giorni(?:\s+tranne\s+\w+)?",
        r"[Oo]gni\s+(?:due\s+)?settiman[ae]",
        r"[Uu]na\s+\w+\s+al\s+mese",
    ]
    for pattern in patterns:
        match = re.search(pattern, body, re.IGNORECASE)
        if match:
            return match.group(0)
    return ""


def _extract_address(soup: BeautifulSoup, body: str) -> str:
    """Extract street address."""
    for selector in [".indirizzo", ".address", "address"]:
        el = soup.select_one(selector)
        if el:
            return el.get_text(strip=True)

    # Try to find patterns like "Via/Piazza/Corso X, N"
    match = re.search(
        r"(?:Via|Viale|Piazza|P\.za|P\.zza|Corso|Largo|Lungomare|Vicolo|Contrada)\s+[A-Za-zÀ-ú\s']+(?:,?\s*\d+)?",
        body
    )
    if match:
        return match.group(0).strip()

    return ""


def _clean_description(body: str, nome: str) -> str:
    """Extract a clean description, trimmed to reasonable length."""
    # Remove the market name from the beginning
    desc = body
    if nome.lower() in desc.lower()[:100]:
        idx = desc.lower().find(nome.lower())
        desc = desc[idx + len(nome):].strip(" -–:.,")

    # Trim to first 500 chars at sentence boundary
    if len(desc) > 500:
        cut = desc[:500].rfind(".")
        if cut > 200:
            desc = desc[:cut + 1]
        else:
            desc = desc[:500] + "…"

    return desc.strip()


# ═══════════════════════════════════════════════════════════════
# MAIN SCRAPER FUNCTION
# ═══════════════════════════════════════════════════════════════

def scrape_eventiesagre(
    regioni: list[str] | None = None,
    sezioni: list[str] | None = None,
) -> Generator[RawMarket, None, None]:
    """
    Scrape eventiesagre.it for markets.

    Args:
        regioni: List of region names to scrape (default: all)
        sezioni: List of section names to scrape (default: all)

    Yields:
        RawMarket objects for each market found.
    """
    target_regioni = regioni or list(REGIONI_URL.keys())
    target_sezioni = sezioni or list(SECTIONS.keys())

    client = _get_client()
    total_found = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold]{task.description}"),
        console=console,
    ) as progress:

        for regione in target_regioni:
            regione_url = REGIONI_URL.get(regione, regione)

            for section_name in target_sezioni:
                section_url = SECTIONS.get(section_name, section_name)
                task = progress.add_task(
                    f"{regione} → {section_name}", total=None
                )

                # Build listing URL
                list_url = f"{BASE_URL}/cerca/Mercatini/{section_url}/mesi/{regione_url}/prov/cit/rilib"

                page = 0
                detail_urls_all = []

                # Paginate through listings
                while list_url and page < SCRAPE_MAX_PAGES_PER_REGION:
                    progress.update(task, description=f"{regione} → {section_name} (p.{page + 1})")
                    detail_urls, next_url = scrape_listing_page(client, list_url)
                    detail_urls_all.extend(detail_urls)
                    list_url = next_url
                    page += 1
                    time.sleep(SCRAPE_DELAY_SECONDS)

                # Deduplicate URLs
                detail_urls_all = list(dict.fromkeys(detail_urls_all))

                progress.update(task, description=f"{regione} → {section_name}: {len(detail_urls_all)} mercati")

                # Scrape each detail page
                for url in detail_urls_all:
                    market = scrape_detail_page(client, url, regione, section_name)
                    if market:
                        total_found += 1
                        yield market
                    time.sleep(SCRAPE_DELAY_SECONDS)

                progress.remove_task(task)

    console.print(f"\n[bold green]✓ Scraping completato: {total_found} mercati trovati[/bold green]")
    client.close()


# ═══════════════════════════════════════════════════════════════
# CLI entry point
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys
    import json

    regioni_arg = sys.argv[1:] if len(sys.argv) > 1 else ["Toscana", "Lazio", "Emilia-Romagna"]

    console.print(f"\n[bold]🏪 Scraping eventiesagre.it[/bold]")
    console.print(f"   Regioni: {', '.join(regioni_arg)}\n")

    markets = []
    for raw_market in scrape_eventiesagre(regioni=regioni_arg):
        markets.append({
            "nome": raw_market.nome,
            "citta": raw_market.citta,
            "provincia": raw_market.provincia,
            "regione": raw_market.regione,
            "indirizzo": raw_market.indirizzo,
            "categoria_raw": raw_market.categoria_raw,
            "orario_raw": raw_market.orario_raw,
            "ricorrenza_raw": raw_market.ricorrenza_raw,
            "date_raw": raw_market.date_raw,
            "url_fonte": raw_market.url_fonte,
        })
        console.print(f"  [{raw_market.citta}] {raw_market.nome}")

    # Save raw results
    output_file = "scraped_raw.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(markets, f, ensure_ascii=False, indent=2)

    console.print(f"\n[bold]Salvati {len(markets)} mercati in {output_file}[/bold]")
