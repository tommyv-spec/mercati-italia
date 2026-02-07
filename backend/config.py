"""
Mercati d'Italia — Scraper Pipeline Configuration
"""
import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

# ─── Environment ─────────────────────────────────────────────

FIREBASE_CREDENTIALS_PATH = os.getenv("FIREBASE_CREDENTIALS_PATH", "serviceAccountKey.json")
FIREBASE_PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID", "")
NOMINATIM_USER_AGENT = "mercati-italia-app/1.0"

# ─── Enums matching DB ───────────────────────────────────────

class Categoria(str, Enum):
    ALIMENTARE = "alimentare"
    ANTIQUARIATO = "antiquariato"
    VINTAGE = "vintage_abbigliamento"
    USATO = "usato"
    ARTIGIANATO = "artigianato"
    MISTO = "misto"

class Ricorrenza(str, Enum):
    GIORNALIERO = "giornaliero"
    SETTIMANALE = "settimanale"
    BISETTIMANALE = "bisettimanale"
    MENSILE_GIORNO = "mensile_giorno_fisso"
    MENSILE_DATA = "mensile_data_fissa"
    ANNUALE = "annuale"
    IRREGOLARE = "irregolare"
    SCONOSCIUTO = "sconosciuto"

# ─── Data classes ────────────────────────────────────────────

@dataclass
class RawMarket:
    """Raw data as scraped from a source, before cleaning."""
    nome: str
    citta: str = ""
    provincia: str = ""          # two-letter code e.g. "FI"
    regione: str = ""
    indirizzo: str = ""
    categoria_raw: str = ""      # original text from source
    descrizione: str = ""
    orario_raw: str = ""         # e.g. "dalle 9 alle 19"
    ricorrenza_raw: str = ""     # e.g. "ogni prima domenica del mese"
    date_raw: list[str] = field(default_factory=list)  # ["01/02/2026", ...]
    tags_raw: list[str] = field(default_factory=list)
    url_fonte: str = ""
    fonte_nome: str = ""
    lat: Optional[float] = None
    lng: Optional[float] = None

@dataclass
class CleanMarket:
    """Normalized market data, ready for DB insertion."""
    nome: str
    slug: str
    citta: str
    provincia: str
    regione: str
    indirizzo: str
    lat: float
    lng: float
    luogo_nome: str = ""
    categoria: Categoria = Categoria.MISTO
    tags: list[str] = field(default_factory=list)
    orario_testo: str = ""
    ricorrenza: Ricorrenza = Ricorrenza.SCONOSCIUTO
    ricorrenza_testo: str = ""
    descrizione: str = ""
    date: list[str] = field(default_factory=list)  # ISO format: ["2026-02-07", ...]
    url_fonte: str = ""
    fonte_nome: str = ""
    dati_grezzi: dict = field(default_factory=dict)

# ─── Regions lookup ──────────────────────────────────────────

REGIONI = [
    "Abruzzo", "Basilicata", "Calabria", "Campania",
    "Emilia-Romagna", "Friuli Venezia Giulia", "Lazio", "Liguria",
    "Lombardia", "Marche", "Molise", "Piemonte", "Puglia",
    "Sardegna", "Sicilia", "Toscana", "Trentino-Alto Adige",
    "Umbria", "Valle d'Aosta", "Veneto"
]

# Category keyword mapping for classification
CATEGORY_KEYWORDS = {
    Categoria.ALIMENTARE: [
        "alimentare", "alimentari", "cibo", "gastronomic", "enogastronomic",
        "farmer", "contadino", "produttori", "filiera corta", "km zero",
        "ortofrutt", "frutta", "verdura", "pesce", "carne", "biologico",
        "mercato coperto", "mercato rionale",
    ],
    Categoria.ANTIQUARIATO: [
        "antiquari", "antiquariat", "antico", "antichit", "brocante",
        "brocantage", "modernariato",
    ],
    Categoria.VINTAGE: [
        "vintage", "abbigliamento", "moda", "vestiti", "retro",
        "second hand", "fashion",
    ],
    Categoria.USATO: [
        "usato", "usati", "pulci", "svuota cantine", "svuota soffitte",
        "rigattiere", "conto vendita", "baratto",
    ],
    Categoria.ARTIGIANATO: [
        "artigian", "handmade", "fatto a mano", "ceramica", "ceramiche",
        "cartapesta", "tessuti", "gioielli artigianali", "creativo", "hobbist",
    ],
    Categoria.MISTO: [
        "misto", "vari", "generico", "mercatino", "fiera",
    ],
}

# ─── Scrape settings ─────────────────────────────────────────

SCRAPE_DELAY_SECONDS = 2.0          # polite delay between requests
SCRAPE_MAX_PAGES_PER_REGION = 10    # max pagination depth
REQUEST_TIMEOUT = 15                 # seconds
USER_AGENT = "Mozilla/5.0 (compatible; MercatiBot/1.0; +https://mercati-italia.app)"
