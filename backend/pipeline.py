"""
Mercati d'Italia — Main Pipeline Orchestrator

Usage:
    python pipeline.py                          # scrape MVP regions, clean, save to JSON
    python pipeline.py --regioni Toscana Lazio  # scrape specific regions
    python pipeline.py --db                     # write to Firestore instead of JSON
    python pipeline.py --dry-run                # scrape + clean, print results only

Flow:
    1. Scrape sources → RawMarket objects
    2. Clean & normalize → CleanMarket objects
    3. Deduplicate across sources
    4. Store in DB (or export to JSON)
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone
from dataclasses import asdict
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from config import RawMarket, CleanMarket, REGIONI
from cleaner import clean_market, are_duplicates, merge_markets, content_hash
from scraper_eventiesagre import scrape_eventiesagre

console = Console()

# ═══════════════════════════════════════════════════════════════
# PIPELINE STEPS
# ═══════════════════════════════════════════════════════════════

def step_scrape(regioni: list[str]) -> list[RawMarket]:
    """Step 1: Scrape all sources for the given regions."""
    console.print(Panel(f"[bold]Step 1: Scraping[/bold]\nRegioni: {', '.join(regioni)}", style="blue"))

    raw_markets = []

    # Source 1: eventiesagre.it
    for market in scrape_eventiesagre(regioni=regioni):
        raw_markets.append(market)

    # Future sources would be added here:
    # for market in scrape_ilturista(regioni=regioni):
    #     raw_markets.append(market)
    # for market in scrape_cosedicasa(regioni=regioni):
    #     raw_markets.append(market)

    console.print(f"[green]→ {len(raw_markets)} mercati grezzi raccolti[/green]\n")
    return raw_markets


def step_clean(raw_markets: list[RawMarket]) -> list[CleanMarket]:
    """Step 2: Clean and normalize all raw markets."""
    console.print(Panel("[bold]Step 2: Pulizia e normalizzazione[/bold]", style="yellow"))

    clean_markets = []
    skipped = 0

    for raw in raw_markets:
        clean = clean_market(raw)
        if clean:
            clean_markets.append(clean)
        else:
            skipped += 1

    console.print(f"[green]→ {len(clean_markets)} mercati puliti[/green]")
    if skipped:
        console.print(f"[yellow]→ {skipped} scartati (dati insufficienti)[/yellow]")
    console.print()

    return clean_markets


def step_dedup(markets: list[CleanMarket]) -> list[CleanMarket]:
    """Step 3: Deduplicate markets found across multiple sources."""
    console.print(Panel("[bold]Step 3: Deduplicazione[/bold]", style="magenta"))

    unique: list[CleanMarket] = []
    merge_count = 0

    for market in markets:
        found_dup = False
        for i, existing in enumerate(unique):
            if are_duplicates(existing, market):
                unique[i] = merge_markets(existing, market)
                merge_count += 1
                found_dup = True
                break
        if not found_dup:
            unique.append(market)

    console.print(f"[green]→ {len(unique)} mercati unici ({merge_count} duplicati uniti)[/green]\n")
    return unique


def step_store_json(markets: list[CleanMarket], output_file: str = "mercati_clean.json"):
    """Step 4a: Export cleaned markets, recording catalog import time only."""
    console.print(Panel(f"[bold]Step 4: Salvataggio in {output_file}[/bold]", style="green"))

    output = []
    imported_at = datetime.now(timezone.utc).isoformat()
    for m in markets:
        d = asdict(m)
        d["categoria"] = m.categoria.value
        d["ricorrenza"] = m.ricorrenza.value
        d["importato_il"] = imported_at
        output.append(d)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    console.print(f"[green]→ Salvati {len(output)} mercati in {output_file}[/green]\n")


def step_store_db(markets: list[CleanMarket]):
    """Step 4b: Write markets without inventing publisher or verification dates.

    These cleaned records carry no authenticated source-read timestamp or
    publisher content date. A database write supplies only ``importato_il``;
    existing legacy/source/verification timestamps survive an update unchanged.
    """
    console.print(Panel("[bold]Step 4: Scrittura su Firestore[/bold]", style="green"))

    from config import FIREBASE_CREDENTIALS_PATH, FIREBASE_PROJECT_ID
    import firebase_admin
    from firebase_admin import credentials, firestore

    # Initialize Firebase Admin SDK
    if not firebase_admin._apps:
        if FIREBASE_CREDENTIALS_PATH and os.path.exists(FIREBASE_CREDENTIALS_PATH):
            cred = credentials.Certificate(FIREBASE_CREDENTIALS_PATH)
            firebase_admin.initialize_app(cred)
        elif FIREBASE_PROJECT_ID:
            # Use default credentials (Cloud Run, Cloud Functions, etc.)
            firebase_admin.initialize_app(options={"projectId": FIREBASE_PROJECT_ID})
        else:
            console.print("[red]✗ Configurazione Firebase mancante.[/red]")
            console.print("  Opzione 1: Scarica serviceAccountKey.json da Firebase Console")
            console.print("            → Project Settings → Service Accounts → Generate New Private Key")
            console.print("  Opzione 2: Imposta FIREBASE_PROJECT_ID in .env per default credentials")
            return

    db = firestore.client()
    inserted = 0
    updated = 0
    errors = 0
    imported_at = datetime.now(timezone.utc).isoformat()

    for market in markets:
        try:
            doc_ref = db.collection('mercati').document(market.slug)
            doc = doc_ref.get()

            market_data = {
                'nome': market.nome,
                'slug': market.slug,
                'citta': market.citta,
                'provincia': market.provincia,
                'regione': market.regione,
                'indirizzo': market.indirizzo,
                'lat': market.lat,
                'lng': market.lng,
                'luogo_nome': market.luogo_nome,
                'categoria': market.categoria.value,
                'tags': market.tags,
                'status': 'non_confermato',
                'ricorrenza': market.ricorrenza.value,
                'ricorrenza_testo': market.ricorrenza_testo,
                'orario_testo': market.orario_testo,
                'descrizione': market.descrizione,
                'confidence': 50,
                'date': market.date,
                'prossima_data': market.date[0] if market.date else None,
                'fonte': market.fonte_nome,
                'url_fonte': market.url_fonte,
                'importato_il': imported_at,
            }

            if doc.exists:
                doc_ref.update(market_data)
                updated += 1
            else:
                market_data['creato_il'] = imported_at
                doc_ref.set(market_data)
                inserted += 1

            # Store source info as subcollection
            fonte_ref = doc_ref.collection('fonti').document(market.fonte_nome)
            fonte_ref.set({
                'url_originale': market.url_fonte,
                'dati_grezzi': market.dati_grezzi,
                'hash_contenuto': content_hash(market),
                'importato_il': imported_at,
            }, merge=True)

        except Exception as e:
            console.print(f"[red]✗ Errore per {market.nome}: {e}[/red]")
            errors += 1

    console.print(f"[green]→ {inserted} inseriti, {updated} aggiornati[/green]")
    if errors:
        console.print(f"[red]→ {errors} errori[/red]")
    console.print()


def step_print_summary(markets: list[CleanMarket]):
    """Print a summary table of results."""
    table = Table(title="🏪 Mercati trovati", show_lines=True)
    table.add_column("Nome", style="bold", max_width=35)
    table.add_column("Città", max_width=15)
    table.add_column("Regione", max_width=18)
    table.add_column("Categoria", max_width=15)
    table.add_column("Ricorrenza", max_width=25)
    table.add_column("Orari", max_width=12)
    table.add_column("Date", max_width=8, justify="right")
    table.add_column("Coord.", max_width=6, justify="center")

    for m in markets[:50]:  # show first 50
        table.add_row(
            m.nome,
            m.citta,
            m.regione,
            m.categoria.value,
            m.ricorrenza_testo[:25] if m.ricorrenza_testo else "–",
            m.orario_testo or "–",
            str(len(m.date)),
            "✓" if m.lat else "✗",
        )

    console.print(table)

    if len(markets) > 50:
        console.print(f"  ... e altri {len(markets) - 50} mercati\n")

    # Stats
    cats = {}
    for m in markets:
        cats[m.categoria.value] = cats.get(m.categoria.value, 0) + 1

    stats_table = Table(title="Statistiche per categoria")
    stats_table.add_column("Categoria")
    stats_table.add_column("Quantità", justify="right")
    for cat, count in sorted(cats.items(), key=lambda x: -x[1]):
        stats_table.add_row(cat, str(count))
    console.print(stats_table)


# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Mercati d'Italia — Data Pipeline")
    parser.add_argument("--regioni", nargs="+", default=["Toscana", "Lazio", "Emilia-Romagna"],
                        help="Regioni da analizzare")
    parser.add_argument("--db", action="store_true",
                        help="Salva su Supabase invece che JSON")
    parser.add_argument("--dry-run", action="store_true",
                        help="Solo scrape + pulizia, nessun salvataggio")
    parser.add_argument("--output", default="mercati_clean.json",
                        help="File JSON di output (default: mercati_clean.json)")
    args = parser.parse_args()

    # Validate regions
    for r in args.regioni:
        if r not in REGIONI:
            console.print(f"[red]Regione sconosciuta: {r}[/red]")
            console.print(f"Regioni valide: {', '.join(REGIONI)}")
            sys.exit(1)

    console.print(Panel.fit(
        "[bold white]🏪 Mercati d'Italia — Data Pipeline[/bold white]\n"
        f"Regioni: {', '.join(args.regioni)}\n"
        f"Output: {'Firestore' if args.db else args.output}\n"
        f"Modalità: {'dry-run' if args.dry_run else 'completa'}",
        border_style="bright_blue"
    ))

    # Run pipeline
    raw = step_scrape(args.regioni)
    clean = step_clean(raw)
    unique = step_dedup(clean)

    # Summary
    step_print_summary(unique)

    # Store
    if not args.dry_run:
        if args.db:
            step_store_db(unique)
        else:
            step_store_json(unique, args.output)

    console.print("[bold green]✓ Pipeline completata![/bold green]")


if __name__ == "__main__":
    main()
