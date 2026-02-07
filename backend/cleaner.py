"""
Mercati d'Italia — Data Cleaning & Normalization Pipeline

Handles:
  - Category classification from raw Italian text
  - Recurrence pattern parsing ("ogni prima domenica del mese" → dates)
  - Hours normalization ("dalle 9 alle 19" → "9:00–19:00")
  - Address geocoding via Nominatim
  - Fuzzy deduplication across sources
  - Slug generation
  - Tag extraction
"""
import re
import hashlib
from datetime import date, datetime, timedelta
from typing import Optional
from slugify import slugify
from thefuzz import fuzz
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter

from config import (
    RawMarket, CleanMarket, Categoria, Ricorrenza,
    CATEGORY_KEYWORDS, NOMINATIM_USER_AGENT
)

# ─── Geocoder (rate-limited) ─────────────────────────────────

_geocoder = Nominatim(user_agent=NOMINATIM_USER_AGENT)
geocode = RateLimiter(_geocoder.geocode, min_delay_seconds=1.1)


# ═══════════════════════════════════════════════════════════════
# 1. CATEGORY CLASSIFICATION
# ═══════════════════════════════════════════════════════════════

def classify_category(raw_text: str, section_hint: str = "") -> Categoria:
    """
    Classify a market into a category based on its name, description,
    and the section it was found in on the source site.

    Priority: exact section match > keyword density in text.
    """
    combined = f"{section_hint} {raw_text}".lower()

    scores = {}
    for cat, keywords in CATEGORY_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in combined)
        # Boost if the section explicitly matches
        if cat == Categoria.ANTIQUARIATO and "antiquari" in section_hint.lower():
            score += 5
        elif cat == Categoria.USATO and "usato" in section_hint.lower():
            score += 5
        elif cat == Categoria.ARTIGIANATO and "artigian" in section_hint.lower():
            score += 5
        elif cat == Categoria.ALIMENTARE and ("filiera" in section_hint.lower() or "enogastro" in section_hint.lower()):
            score += 5
        scores[cat] = score

    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else Categoria.MISTO


# ═══════════════════════════════════════════════════════════════
# 2. RECURRENCE PARSING
# ═══════════════════════════════════════════════════════════════

GIORNO_MAP = {
    "luned": 0, "marted": 1, "mercoled": 2, "gioved": 3,
    "venerd": 4, "sabato": 5, "domenica": 6,
}

ORDINAL_MAP = {
    "prim": 1, "1°": 1, "1ª": 1, "prima": 1, "primo": 1,
    "second": 2, "2°": 2, "2ª": 2, "seconda": 2, "secondo": 2,
    "terz": 3, "3°": 3, "3ª": 3, "terza": 3, "terzo": 3,
    "quart": 4, "4°": 4, "4ª": 4, "quarta": 4, "quarto": 4,
    "ultim": -1, "ultima": -1, "ultimo": -1,
}


def parse_recurrence(text: str) -> tuple[Ricorrenza, str]:
    """
    Parse Italian recurrence text into a Ricorrenza enum + clean text.

    Examples:
      "Ogni prima domenica del mese" → (MENSILE_GIORNO, "Ogni 1ª domenica del mese")
      "Ogni sabato" → (SETTIMANALE, "Ogni sabato")
      "Tutti i giorni tranne domenica" → (GIORNALIERO, "Tutti i giorni tranne domenica")
      "Dal 01/03 al 05/03/2026" → (IRREGOLARE, "Dal 01/03 al 05/03/2026")
    """
    t = text.strip().lower()

    # Daily
    if any(p in t for p in ["tutti i giorni", "ogni giorno", "giornaliero", "quotidian"]):
        return Ricorrenza.GIORNALIERO, text.strip()

    # Weekly: "ogni sabato", "ogni venerdì"
    for giorno_prefix, _ in GIORNO_MAP.items():
        if re.search(rf"ogni\s+{giorno_prefix}", t):
            return Ricorrenza.SETTIMANALE, text.strip()

    # Monthly by weekday: "ogni prima domenica del mese"
    for ordinal_kw, _ in ORDINAL_MAP.items():
        for giorno_kw, _ in GIORNO_MAP.items():
            if ordinal_kw in t and giorno_kw in t and "mese" in t:
                return Ricorrenza.MENSILE_GIORNO, text.strip()

    # Monthly by date: "il 15 di ogni mese"
    if re.search(r"il\s+\d{1,2}\s+(di\s+)?ogni\s+mese", t):
        return Ricorrenza.MENSILE_DATA, text.strip()

    # Biweekly
    if "ogni due settimane" in t or "bisettimanale" in t:
        return Ricorrenza.BISETTIMANALE, text.strip()

    # Yearly / annual
    if "annuale" in t or "ogni anno" in t:
        return Ricorrenza.ANNUALE, text.strip()

    # If dates are mentioned, treat as irregular
    if re.search(r"\d{1,2}/\d{1,2}/\d{2,4}", t) or re.search(r"dal\s+\d", t):
        return Ricorrenza.IRREGOLARE, text.strip()

    return Ricorrenza.SCONOSCIUTO, text.strip()


def generate_dates_from_recurrence(
    ricorrenza: Ricorrenza,
    testo: str,
    raw_dates: list[str],
    months_ahead: int = 6
) -> list[str]:
    """
    Generate concrete ISO date strings from recurrence info.
    Falls back to parsing raw date strings.
    Returns dates from today up to `months_ahead` months forward.
    """
    today = date.today()
    end = today + timedelta(days=months_ahead * 30)
    dates = []

    # First, try to parse any explicit dates from raw_dates
    for d_str in raw_dates:
        parsed = _parse_date_string(d_str)
        if parsed and today <= parsed <= end:
            dates.append(parsed.isoformat())

    # If we have a parseable recurrence, generate additional dates
    if ricorrenza == Ricorrenza.SETTIMANALE:
        weekday = _extract_weekday(testo)
        if weekday is not None:
            d = today
            while d <= end:
                if d.weekday() == weekday:
                    dates.append(d.isoformat())
                d += timedelta(days=1)

    elif ricorrenza == Ricorrenza.MENSILE_GIORNO:
        ordinal, weekday = _extract_ordinal_weekday(testo)
        if ordinal is not None and weekday is not None:
            for month_offset in range(months_ahead + 1):
                m = today.month + month_offset
                y = today.year + (m - 1) // 12
                m = ((m - 1) % 12) + 1
                d = _nth_weekday_of_month(y, m, weekday, ordinal)
                if d and today <= d <= end:
                    dates.append(d.isoformat())

    elif ricorrenza == Ricorrenza.GIORNALIERO:
        # Don't generate 180 dates, just next 30 days
        for i in range(30):
            d = today + timedelta(days=i)
            # Skip Sundays if "tranne domenica" is in text
            if "domenica" in testo.lower() and d.weekday() == 6:
                continue
            dates.append(d.isoformat())

    return sorted(set(dates))


def _parse_date_string(s: str) -> Optional[date]:
    """Parse various Italian date formats into a date object."""
    s = s.strip()
    for fmt in ["%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d/%m/%y", "%d %B %Y"]:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _extract_weekday(text: str) -> Optional[int]:
    t = text.lower()
    for prefix, day_num in GIORNO_MAP.items():
        if prefix in t:
            return day_num
    return None


def _extract_ordinal_weekday(text: str) -> tuple[Optional[int], Optional[int]]:
    t = text.lower()
    ordinal = None
    weekday = None
    for kw, val in ORDINAL_MAP.items():
        if kw in t:
            ordinal = val
            break
    for prefix, day_num in GIORNO_MAP.items():
        if prefix in t:
            weekday = day_num
            break
    return ordinal, weekday


def _nth_weekday_of_month(year: int, month: int, weekday: int, n: int) -> Optional[date]:
    """Get the nth weekday of a given month. n=-1 for last."""
    if n == -1:
        # Last occurrence
        if month == 12:
            last_day = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            last_day = date(year, month + 1, 1) - timedelta(days=1)
        d = last_day
        while d.weekday() != weekday:
            d -= timedelta(days=1)
        return d
    else:
        first = date(year, month, 1)
        d = first
        while d.weekday() != weekday:
            d += timedelta(days=1)
        d += timedelta(weeks=n - 1)
        if d.month == month:
            return d
        return None


# ═══════════════════════════════════════════════════════════════
# 3. HOURS NORMALIZATION
# ═══════════════════════════════════════════════════════════════

def normalize_hours(raw: str) -> str:
    """
    Normalize Italian time strings.
    "dalle 9 alle 19"       → "9:00–19:00"
    "ore 8:30 - 14:00"      → "8:30–14:00"
    "9.00-18.00"             → "9:00–18:00"
    """
    if not raw:
        return ""

    t = raw.strip().lower()
    t = t.replace(".", ":").replace("–", "-").replace("—", "-")
    t = re.sub(r"dalle\s*", "", t)
    t = re.sub(r"alle\s*", "- ", t)
    t = re.sub(r"ore\s*", "", t)

    # Extract time pairs
    match = re.findall(r"(\d{1,2}(?::\d{2})?)", t)
    if len(match) >= 2:
        start = match[0] if ":" in match[0] else f"{match[0]}:00"
        end = match[1] if ":" in match[1] else f"{match[1]}:00"
        return f"{start}–{end}"

    return raw.strip()


# ═══════════════════════════════════════════════════════════════
# 4. GEOCODING
# ═══════════════════════════════════════════════════════════════

_geocode_cache: dict[str, tuple[float, float]] = {}

def geocode_address(address: str, city: str, provincia: str = "") -> tuple[Optional[float], Optional[float]]:
    """
    Geocode an Italian address using Nominatim (OpenStreetMap).
    Returns (lat, lng) or (None, None).
    """
    cache_key = f"{address}|{city}|{provincia}"
    if cache_key in _geocode_cache:
        return _geocode_cache[cache_key]

    queries = [
        f"{address}, {city}, Italia",
        f"{city}, {provincia}, Italia" if provincia else f"{city}, Italia",
    ]

    for q in queries:
        try:
            location = geocode(q, country_codes="it", timeout=10)
            if location:
                result = (location.latitude, location.longitude)
                _geocode_cache[cache_key] = result
                return result
        except Exception:
            continue

    _geocode_cache[cache_key] = (None, None)
    return (None, None)


# ═══════════════════════════════════════════════════════════════
# 5. TAG EXTRACTION
# ═══════════════════════════════════════════════════════════════

TAG_PATTERNS = {
    "al chiuso": ["al chiuso", "coperto", "indoor", "interno"],
    "all'aperto": ["all'aperto", "aperto", "outdoor", "esterno", "piazza", "strada"],
    "serale": ["serale", "sera", "notturno", "notte"],
    "collezionismo": ["collezion", "numismatic", "filateli"],
    "dischi": ["dischi", "vinili", "vinyl", "vinyl"],
    "modernariato": ["modernariato", "anni 50", "anni 60", "anni 70", "design"],
    "produttori locali": ["produttori locali", "km zero", "km 0", "filiera corta", "contadini"],
}

def extract_tags(text: str, existing_tags: list[str] = None) -> list[str]:
    """Extract tags from text based on keyword matching."""
    tags = set(existing_tags or [])
    t = text.lower()
    for tag, keywords in TAG_PATTERNS.items():
        if any(kw in t for kw in keywords):
            tags.add(tag)
    return sorted(tags)


# ═══════════════════════════════════════════════════════════════
# 6. DEDUPLICATION
# ═══════════════════════════════════════════════════════════════

def are_duplicates(a: CleanMarket, b: CleanMarket, threshold: int = 80) -> bool:
    """
    Check if two markets are likely the same using:
    - Name fuzzy match (weighted heavily)
    - City exact match
    - Geo proximity (< 1km)
    """
    # Different cities → not duplicates
    if a.citta.lower() != b.citta.lower():
        return False

    # Name similarity
    name_score = fuzz.token_sort_ratio(a.nome.lower(), b.nome.lower())

    # Geo proximity (if both have coordinates)
    geo_close = False
    if a.lat and b.lat:
        # Simple approximation: 0.01° ≈ 1.1km
        dist = ((a.lat - b.lat) ** 2 + (a.lng - b.lng) ** 2) ** 0.5
        geo_close = dist < 0.01  # ~1km

    # If names are very similar, it's a duplicate
    if name_score >= threshold:
        return True

    # If names are somewhat similar AND geographically close
    if name_score >= 60 and geo_close:
        return True

    return False


def merge_markets(existing: CleanMarket, new: CleanMarket) -> CleanMarket:
    """
    Merge two duplicate market entries, preferring non-empty fields
    from the newer source.
    """
    merged = CleanMarket(
        nome=existing.nome,  # keep original name
        slug=existing.slug,
        citta=existing.citta or new.citta,
        provincia=existing.provincia or new.provincia,
        regione=existing.regione or new.regione,
        indirizzo=existing.indirizzo or new.indirizzo,
        lat=existing.lat or new.lat,
        lng=existing.lng or new.lng,
        luogo_nome=existing.luogo_nome or new.luogo_nome,
        categoria=existing.categoria if existing.categoria != Categoria.MISTO else new.categoria,
        tags=sorted(set(existing.tags + new.tags)),
        orario_testo=existing.orario_testo or new.orario_testo,
        ricorrenza=existing.ricorrenza if existing.ricorrenza != Ricorrenza.SCONOSCIUTO else new.ricorrenza,
        ricorrenza_testo=existing.ricorrenza_testo or new.ricorrenza_testo,
        descrizione=max(existing.descrizione, new.descrizione, key=len),  # keep longer
        date=sorted(set(existing.date + new.date)),
        url_fonte=existing.url_fonte,  # keep original source
        fonte_nome=existing.fonte_nome,
    )
    return merged


# ═══════════════════════════════════════════════════════════════
# 7. FULL CLEANING PIPELINE
# ═══════════════════════════════════════════════════════════════

def clean_market(raw: RawMarket) -> Optional[CleanMarket]:
    """
    Full cleaning pipeline: raw scraped data → normalized CleanMarket.
    Returns None if the data is too incomplete to be useful.
    """
    # Must have at least a name and city
    if not raw.nome or not raw.citta:
        return None

    # Classify category
    combined_text = f"{raw.nome} {raw.descrizione} {raw.categoria_raw} {' '.join(raw.tags_raw)}"
    categoria = classify_category(combined_text, raw.categoria_raw)

    # Parse recurrence
    ricorrenza, ricorrenza_testo = parse_recurrence(raw.ricorrenza_raw)

    # Generate dates
    date_list = generate_dates_from_recurrence(ricorrenza, raw.ricorrenza_raw, raw.date_raw)

    # Normalize hours
    orario = normalize_hours(raw.orario_raw)

    # Geocode if needed
    lat, lng = raw.lat, raw.lng
    if not lat or not lng:
        lat, lng = geocode_address(raw.indirizzo, raw.citta, raw.provincia)

    # Still no coordinates? Use city-level geocoding
    if not lat or not lng:
        lat, lng = geocode_address("", raw.citta, raw.provincia)

    if not lat or not lng:
        return None  # can't place on map without coordinates

    # Extract tags
    tags = extract_tags(combined_text, raw.tags_raw)

    # Generate slug
    slug = slugify(f"{raw.nome}-{raw.citta}", max_length=80)

    # Build raw data snapshot for provenance
    dati_grezzi = {
        "nome_originale": raw.nome,
        "categoria_raw": raw.categoria_raw,
        "orario_raw": raw.orario_raw,
        "ricorrenza_raw": raw.ricorrenza_raw,
        "date_raw": raw.date_raw,
    }

    return CleanMarket(
        nome=raw.nome.strip(),
        slug=slug,
        citta=raw.citta.strip(),
        provincia=raw.provincia.strip().upper() if raw.provincia else "",
        regione=raw.regione.strip(),
        indirizzo=raw.indirizzo.strip(),
        lat=lat,
        lng=lng,
        categoria=categoria,
        tags=tags,
        orario_testo=orario,
        ricorrenza=ricorrenza,
        ricorrenza_testo=ricorrenza_testo,
        descrizione=raw.descrizione.strip(),
        date=date_list,
        url_fonte=raw.url_fonte,
        fonte_nome=raw.fonte_nome,
        dati_grezzi=dati_grezzi,
    )


def content_hash(market: CleanMarket) -> str:
    """Generate a hash of market content for change detection."""
    content = f"{market.nome}|{market.orario_testo}|{market.ricorrenza_testo}|{','.join(market.date)}"
    return hashlib.md5(content.encode()).hexdigest()
