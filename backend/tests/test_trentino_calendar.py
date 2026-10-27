"""trentino.com market calendar: search pages, event pages, rows, date proof and contract."""
import json
import sys
import unittest
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import trentino_calendar as tc
from publisher_snapshot_date import make_event_change_proof, resolve_source_date
from recurrence_refresh import forecast_rule, project_dates
from source_contract_activation import read_source_snapshot
from source_lifecycle import candidate_record, istat_municipality, parse_rows, validate_contracts
from source_probe import safe_url

CONTRACTS = json.loads((Path(__file__).resolve().parents[1] / "data/market-source-contracts.json")
                       .read_text("utf-8"))
PROFILE = next(p for p in CONTRACTS["raw_profiles"] if p["id"] == "trentino-com-mercati")
TODAY = date(2026, 10, 27)


def comune(name):
    return istat_municipality("Trentino-Alto Adige", name) is not None


def weekly(first, weeks, step=7, hours=("08:00", "13:00")):
    return [[(first + timedelta(days=i * step)).isoformat(), *hours] for i in range(weeks)]


def search_html(total, first, items):
    """A trimmed search page: heading and one <li> per listed date (name, slug)."""
    lis = "".join(
        f'<li class="ui-cell e{i}" data-id="{i}"> <div class="wrapper"> '
        f'<a href="/it/calendario/dettagli/{slug}/#2026-10-27" class="general-link img_link">{name}</a> '
        f'<div itemscope itemtype="http://schema.org/Event"> <meta itemprop="name" content="{name}"> '
        f'</div></div> </li>' for i, (slug, name) in enumerate(items))
    return (f'<p class="list_filter_heading"> {total} Manifestazioni (1 - 15) </p>'.replace(
        "(1 - 15)", f"({first} - {first + len(items) - 1})") + "<ol>" + lis + "</ol>")


def event_html(title, place, address, dates, stated=None):
    """A trimmed event page: title, every date as microdata, the location block."""
    divs = "".join(
        f'<div itemscope itemtype="http://schema.org/Event" id="{d}" title="x" class="date" '
        f'data-date="{d}"' + (f' data-time-start="Inizio: {a}"' if a else "")
        + (f' data-time-end="Fine: {b}"' if b else "") + '> <span class="time"></span> </div>'
        for d, a, b in dates)
    return (f'<h1 class="title"> {title} </h1> <div class="dates"> {divs} </div> '
            f'<p><strong>{len(dates) if stated is None else stated} appuntamenti</strong></p> '
            f'<section> <h2>Informazioni</h2> <div> <div id="event-location"> '
            f'<meta itemprop="name" content="{place}" /> <meta itemprop="address" content="{address}"> '
            f'</div></div></section>')


def snapshot(*events, read_on="2026-10-27"):
    return {"schema": 1, "read_on": read_on, "window": ["2026-10-20", "2026-11-17"],
            "events": [{"slug": f"e{i}", "title": t, "place": p, "address": a, "dates": d}
                       for i, (t, p, a, d) in enumerate(events)]}


class PagesTests(unittest.TestCase):
    def test_search_page_lists_every_result_of_its_range(self):
        page = search_html(140, 16, [("mercato-a-cavalese", "Mercato a Cavalese")] * 30)
        total, first, last, items = tc.search_page(page)
        self.assertEqual((total, first, last, len(items)), (140, 16, 45, 30))
        self.assertEqual(items[0], ("mercato-a-cavalese", "Mercato a Cavalese"))
        with self.assertRaises(ValueError):  # a result went missing from the page
            tc.search_page(page.replace('<li class="ui-cell e3"', '<li class="other"'))
        with self.assertRaises(ValueError):  # no heading: the page changed
            tc.search_page("<ol></ol>")

    def test_event_page_reads_title_place_address_and_every_date(self):
        page = event_html("Mercato settimanale a Caldonazzo", "Caldonazzo", "Caldonazzo, Viale Stazione",
                          [["2026-01-09", "08:00", ""], ["2026-01-16", "08:00", ""]])
        event = tc.event_page("mercato-settimanale-a-caldonazzo", page)
        self.assertEqual(event["title"], "Mercato settimanale a Caldonazzo")
        self.assertEqual(event["address"], "Caldonazzo, Viale Stazione")
        self.assertEqual(event["dates"], [["2026-01-09", "08:00", ""], ["2026-01-16", "08:00", ""]])
        with self.assertRaises(ValueError):  # "54 appuntamenti" but fewer dates on the page
            tc.event_page("x", event_html("Mercato", "Cles", "Cles, centro", [["2026-01-05", "", ""]], stated=54))

    def test_only_the_two_calendar_paths_are_fetched(self):
        self.assertTrue(safe_url(tc.search_url(PROFILE, "2026-10-27", 3)))
        self.assertTrue(safe_url(tc.DETAIL_URL.format("mercato-a-male_87898")))
        for url in ("https://www.trentino.com/api/events", "https://www.trentino.com/it/map/",
                    "https://www.trentino.com/it/calendario/dettagli/x/?a=1"):
            self.assertFalse(safe_url(url))


class RowsTests(unittest.TestCase):
    def test_town_is_the_comune_and_a_frazione_stays_in_the_street(self):
        rows = tc.rows(snapshot(
            ("Mercato settimanale a Strigno", "Strigno", "Castel Ivano, Strigno, nel paese",
             weekly(date(2026, 1, 13), 54)),
            ("Mercato a Molina di Fiemme", "Molina di Fiemme",
             "Castello Molina di Fiemme, Molina di Fiemme, Via Segheria", weekly(date(2026, 1, 12), 55)),
        ), comune)
        self.assertEqual({(r["comune"], r["luogo"]) for r in rows},
                         {("Castel Ivano", "Strigno, centro"),
                          ("Castello Molina di Fiemme", "Molina di Fiemme, Via Segheria")})

    def test_wordings_that_name_no_street_become_centro(self):
        self.assertEqual(tc.street("nel paese"), "centro")
        self.assertEqual(tc.street("Centro storico"), "centro")
        self.assertEqual(tc.street("per le vie del paese"), "centro")
        self.assertEqual(tc.street("in centro paese - Corso Dante"), "Corso Dante")
        self.assertEqual(tc.street("in P.zza G. Costanzi"), "P.zza G. Costanzi")
        self.assertEqual(tc.street("Via Fabio Filzi, San Giuseppe - Santa Chiara"),
                         "Via Fabio Filzi, San Giuseppe - Santa Chiara")

    def test_weekly_seasonal_and_fortnightly_markets(self):
        rows = {r["denominazione"]: r for r in tc.rows(snapshot(
            ("Mercato settimanale di Trento", "Trento", "Trento, centro storico",
             weekly(date(2026, 1, 8), 54, hours=("07:15", "14:00"))),
            ("Mercato ortofrutticolo a Malè", "Malé", "Malé, in P.zza G. Costanzi",
             weekly(date(2026, 5, 1), 27, hours=("09:00", "13:00"))),
            # Predazzo: first and third Tuesday, not a weekly market.
            ("Mercato a Predazzo", "Predazzo", "Predazzo, Piazza SS. Filippo e Giacomo",
             weekly(date(2026, 1, 20), 27, step=14)),
        ), comune)}
        trento = rows["Mercato settimanale di Trento"]
        self.assertEqual((trento["giorni"], trento["periodicita"], trento["orario"], trento["luogo"]),
                         ("giovedì", "annuale", "07:15 - 14:00", "centro"))
        male = rows["Mercato ortofrutticolo a Malè"]
        self.assertEqual((male["periodicita"], male["mesi"]), ("stagionale", "da maggio a ottobre"))
        self.assertEqual(rows["Mercato a Predazzo"]["periodicita"], "irregolare")


class SnapshotTests(unittest.TestCase):
    def pages(self):
        first = [("mercato-settimanale-di-trento", "Mercato settimanale di Trento"),
                 ("mercatino-di-natale-ad-arco", "Mercatino di Natale di Arco")] + [
                ("festa-della-castagna", "Festa della Castagna")] * 13
        second = [("mercato-a-predazzo", "Mercato a Predazzo")] * 5
        pages = {tc.search_url(PROFILE, "2026-10-27"): search_html(20, 1, first),
                 tc.search_url(PROFILE, "2026-10-27", 2): search_html(20, 16, second),
                 tc.DETAIL_URL.format("mercato-settimanale-di-trento"): event_html(
                     "Mercato settimanale di Trento", "Trento", "Trento, centro storico",
                     weekly(date(2026, 1, 8), 54)),
                 tc.DETAIL_URL.format("mercato-a-predazzo"): event_html(
                     "Mercato a Predazzo", "Predazzo", "Predazzo, Piazza SS. Filippo e Giacomo",
                     weekly(date(2026, 1, 20), 27, step=14))}
        return {url: page.encode("utf-8") for url, page in pages.items()}

    def test_every_search_page_then_only_market_event_pages(self):
        pages, calls = self.pages(), []

        def get(url):
            calls.append(url)
            return pages[url]

        raw = json.loads(tc.snapshot(PROFILE, get, "2026-10-27"))
        self.assertEqual([e["slug"] for e in raw["events"]],
                         ["mercato-a-predazzo", "mercato-settimanale-di-trento"])
        self.assertEqual(len(calls), 4)  # two search pages, two market pages; no Christmas market page
        self.assertEqual(raw["window"], ["2026-10-20", "2026-11-17"])
        with self.assertRaises(ValueError):
            tc.snapshot({**PROFILE, "max_search_pages": 1}, get, "2026-10-27")

    def test_pipeline_read_returns_one_snapshot_and_its_date_proof(self):
        pages = self.pages()

        def fetch(url, max_bytes):
            return pages[url], False

        blob, proof = read_source_snapshot(PROFILE, fetch=fetch, read_on="2026-10-27", today=TODAY)
        self.assertEqual(proof["source_date"], "2026-10-27")  # Predazzo is listed on the read day itself
        self.assertEqual(proof["request_url"], tc.search_url(PROFILE, "2026-10-27"))
        self.assertEqual(resolve_source_date(PROFILE, proof=proof, blob=blob, today=TODAY), "2026-10-27")


class ContractTests(unittest.TestCase):
    def blob(self):
        return json.dumps(snapshot(
            ("Mercato settimanale a Pieve Tesino", "Pieve Tesino", "Pieve Tesino, nel paese",
             weekly(date(2026, 1, 10), 54)),
            ("Mercato ortofrutticolo a Malè", "Malé", "Malé, in P.zza G. Costanzi",
             weekly(date(2026, 5, 1), 27, hours=("09:00", "13:00"))),
        )).encode("utf-8")

    def test_contract_validates_and_needs_its_search(self):
        validate_contracts(CONTRACTS)
        for changed in ({**PROFILE, "resource_url": "https://www.trentino.com/it/"},
                        {**PROFILE, "search_days_after_read": 90}):
            with self.assertRaises(ValueError):
                tc.validate_profile(changed)

    def test_rows_become_weekly_and_seasonal_cards(self):
        profile = {**PROFILE, "min_rows": 1}  # the real bound is 15 rows
        rows = {r["denominazione"]: r for r in parse_rows(profile, self.blob())}
        pieve, issue, _ = candidate_record(profile, rows["Mercato settimanale a Pieve Tesino"],
                                           today=TODAY, source_date="2026-10-24")
        self.assertIsNone(issue)
        self.assertEqual((pieve["citta"], pieve["indirizzo"], pieve["ricorrenza_testo"]),
                         ("Pieve Tesino", "centro", "settimanale - sabato"))
        self.assertEqual(pieve["orario_testo"], "08:00–13:00 (da verificare con il Comune)")
        male = candidate_record(profile, rows["Mercato ortofrutticolo a Malè"],
                                today=TODAY, source_date="2026-10-24")[0]
        self.assertEqual(male["ricorrenza_testo"], "settimanale - venerdi, da maggio a ottobre")
        self.assertEqual(project_dates(forecast_rule(male), TODAY, 120), ["2026-10-30"])

    def test_content_date_is_the_calendar_not_the_read_time(self):
        blob = self.blob()
        proof = make_event_change_proof(PROFILE, blob, read_on="2026-10-27", today=TODAY)
        self.assertEqual(proof["source_date"], "2026-10-24")  # the last listed Saturday
        with self.assertRaises(ValueError):
            resolve_source_date(PROFILE, proof={**proof, "source_date": "2026-10-27"}, blob=blob, today=TODAY)
        # A calendar that lists nothing after the read day no longer covers it.
        ended = json.dumps(snapshot(("Mercato", "Cles", "Cles, centro", weekly(date(2026, 1, 5), 10)))).encode()
        with self.assertRaises(ValueError):
            make_event_change_proof(PROFILE, ended, read_on="2026-10-27", today=TODAY)


if __name__ == "__main__":
    unittest.main()
