"""Street-level positions: one general rule for every market, fail-closed, bounded, cached."""
from datetime import date
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import position_resolver as pr
from export_static import normalize

TODAY = date(2026, 10, 25)
ISTAT = {"provinces_by_region": {"Lazio": {"Roma": "RM", "Fiumicino": "RM"}, "Toscana": {"Firenze": "FI"}}}


def market(slug, street, *, city="Roma", region="Lazio", lat=41.9, lng=12.5, **extra):
    return {"slug": slug, "nome": "Mercato " + slug, "citta": city, "regione": region, "provincia": "",
            "indirizzo": street, "lat": lat, "lng": lng, "position_quality": "non_verificata",
            "date": ["2027-06-01"], "fonte": "fixture", **extra}


def found(name, *, city="Roma", province="IT-RM", lat=41.95, lng=12.45, category="highway",
          kind="residential", osm_id=7, addresstype="road"):
    return {"lat": str(lat), "lon": str(lng), "category": category, "type": kind, "addresstype": addresstype,
            "osm_type": "way", "osm_id": osm_id, "display_name": name + ", Quartiere, " + city + ", Italia",
            "address": {"road": name, "city": city, "ISO3166-2-lvl6": province}}


class Lookup:
    """Fake Nominatim: answers by query text, records every call."""
    def __init__(self, answers):
        self.answers, self.calls = answers, []

    def __call__(self, text):
        self.calls.append(text)
        answer = self.answers.get(text.split(",")[0], [])
        if isinstance(answer, Exception):
            raise answer
        return answer


def run(rows, cache=None, lookup=None, **kw):
    cache = cache if cache is not None else pr.empty_cache()
    out, report = pr.resolve(rows, cache, today=kw.pop("today", TODAY), istat=ISTAT, lookup=lookup,
                             sleep=lambda s: None, **kw)
    return out, report, cache


STACK = [market("a", "Via Corinto"), market("b", "Piazza Epiro"), market("c", "Via Baccina")]


class StreetQueryTests(unittest.TestCase):
    def test_street_is_cut_from_titles_second_streets_and_numbers(self):
        cases = {
            '"Il Mercatino di Via Stilicone", via Flavio Stilicone (area pedonale)': "via Flavio Stilicone",
            "Via Napoleone Parboni E Via Angelo Bargoni": "Via Napoleone Parboni",
            "Corso trieste ang. Via bovio": "Corso trieste",
            "Via Fauglia, 22": "Via Fauglia",
            "PIAZZA DON GNOCCHI snc": "PIAZZA DON GNOCCHI",
            "via E. Gammieri": "via E. Gammieri",
            "Viale Rimembranza di Vercelli": "Viale Rimembranza",
            "Ippodromo del Visarno": "Ippodromo del Visarno",
        }
        for address, street in cases.items():
            with self.subTest(address=address):
                self.assertEqual(pr.street_query(address, "Vercelli"), street)

    def test_vague_area_damaged_or_generic_addresses_are_never_looked_up(self):
        for address in ("", "centro", "Centro Storico", "quartiere CEP", "località Rigutino", "Via",
                        "Via Dell'", "Piazza dell'Unit�", "MERCATO SETTIMANALE", "G", "Piazza a Carpi"):
            with self.subTest(address=address):
                self.assertIsNone(pr.street_query(address, "Carpi"))
        self.assertIsNone(pr.street_query("Casaloldo", "Casaloldo"))  # only the town's own name

    def test_a_match_needs_the_same_street_type_and_a_word_beyond_the_town(self):
        hit = lambda name, kind="highway": {"name": name, "class": kind}
        # Seen in the full run: a car park named after another square, on "Via San Parisio".
        self.assertFalse(pr.same_street("piazza s parisio",
                                        hit("Piazza San Francesco, Via San Parisio, Treviso", "amenity")))
        self.assertTrue(pr.same_street("piazza ghiberti",
                                       hit("Immobiliare, Piazza Lorenzo Ghiberti, Firenze", "shop")))
        self.assertTrue(pr.same_street("via 25 aprile", hit("Via Medaglie D'oro; Via 25 Aprile, Empoli")))
        self.assertTrue(pr.same_street("piazza chiesa", hit("Kirchplatz - Piazza Chiesa, Sarentino")))
        self.assertFalse(pr.same_street("via per camaiore", hit("Strada Provinciale Lucca-Camaiore, Lucca")))
        self.assertFalse(pr.same_street("casaloldo", hit("Scuola di Casaloldo, Via Roma", "building"),
                                        "casaloldo"))


class PlaceholderTests(unittest.TestCase):
    def test_three_venues_on_one_rounded_point_make_a_placeholder_two_do_not(self):
        self.assertEqual(pr.placeholder_points(STACK, TODAY), {(41.9, 12.5)})
        self.assertEqual(pr.placeholder_points(STACK[:2] + [market("c", "Via Corinto")], TODAY), set())

    def test_precise_looking_points_and_hidden_markets_never_count(self):
        fine = [market(x, s, lat=41.912345, lng=12.512345) for x, s in (("a", "Via A1"), ("b", "Via B1"), ("c", "Via C1"))]
        self.assertEqual(pr.placeholder_points(fine, TODAY), set())
        hidden = STACK[:2] + [market("c", "Via Baccina", duplicato_di="a")]
        self.assertEqual(pr.placeholder_points(hidden, TODAY), set())

    def test_placeholder_is_withdrawn_even_without_a_street_and_kept_for_audit(self):
        rows = STACK + [market("d", "centro")]
        out, report, _ = run(rows)
        self.assertEqual(report["placeholders_withdrawn"], 4)
        self.assertEqual(report["no_street"], 1)
        row = out[3]
        self.assertEqual((row["lat"], row["lng"], row["position_quality"]), (None, None, "sconosciuta"))
        self.assertEqual(row["coordinate_originali"], {"lat": 41.9, "lng": 12.5})
        self.assertEqual(row["coordinate_sospese_motivo"], pr.PLACEHOLDER_REASON)


class ResolveTests(unittest.TestCase):
    def test_accepted_street_point_is_approximate_with_osm_provenance(self):
        lookup = Lookup({"Via Corinto": [found("Via Corinto", lat=41.85, lng=12.48)]})
        out, report, cache = run(STACK, lookup=lookup)
        row = out[0]
        self.assertEqual((row["lat"], row["lng"], row["position_quality"]), (41.85, 12.48, "approssimata"))
        self.assertEqual(row["posizione_fonte"]["fonte"], "openstreetmap")
        self.assertEqual(row["posizione_fonte"]["attribuzione"], "© OpenStreetMap contributors")
        self.assertEqual(row["posizione_fonte"]["osm"], "way/7")
        self.assertEqual(row["coordinate_originali"], {"lat": 41.9, "lng": 12.5})
        self.assertEqual(report["accepted"]["placeholder"], 1)
        self.assertEqual(report["rejected"], {"nessun_risultato": 2})
        self.assertEqual(lookup.calls[0], "Piazza Epiro, Roma, Italia")  # deterministic queue order
        self.assertIn("via corinto|roma|rm", cache["entries"])

    def test_every_result_is_checked_and_the_first_valid_one_wins(self):
        lookup = Lookup({"Via Corinto": [
            found("Roma", category="place", kind="city", addresstype="city"),  # town only
            found("Via Corinto", city="Fiumicino"),                            # other municipality
            found("Via Corinto", province="IT-FI"),                            # other province
            found("Piazza San Domenico"),                                      # another street
            found("Via Corinto", osm_id=99),
        ]})
        out, _, _ = run(STACK, lookup=lookup)
        self.assertEqual(out[0]["posizione_fonte"]["osm"], "way/99")

    def test_rejections_are_cached_with_their_reason_and_never_shown(self):
        cases = {"solo_localita": found("Roma", category="boundary", kind="administrative"),
                 "comune_diverso": found("Via Corinto", city="Fiumicino"),
                 "provincia_diversa": found("Via Corinto", province="IT-FI"),
                 "via_diversa": found("Piazza San Domenico")}
        for reason, result in cases.items():
            with self.subTest(reason=reason):
                out, report, cache = run(STACK, lookup=Lookup({"Via Corinto": [result]}))
                self.assertIsNone(out[0]["lat"])
                self.assertEqual(cache["entries"]["via corinto|roma|rm"]["miss"], reason)
                self.assertEqual(report["rejected"][reason], 1)

    def test_own_rounded_point_bounds_distance_but_a_placeholder_does_not(self):
        far = {"Via Corinto": [found("Via Corinto", lat=41.73, lng=12.27)]}  # ~27 km away
        alone = [market("a", "Via Corinto")]
        out, report, _ = run(alone, lookup=Lookup(far))
        self.assertEqual((out[0]["lat"], report["rejected"]), (41.9, {"lontano_dal_punto_originale": 1}))
        out, report, _ = run(STACK, lookup=Lookup(far))
        self.assertEqual(out[0]["lat"], 41.73)

    def test_rounded_point_replaced_keeps_original_for_audit(self):
        out, _, _ = run([market("a", "Via Corinto")], lookup=Lookup({"Via Corinto": [found("Via Corinto")]}))
        self.assertEqual(out[0]["coordinate_sospese_motivo"], pr.ROUNDED_REASON)
        self.assertEqual(out[0]["coordinate_originali"], {"lat": 41.9, "lng": 12.5})

    def test_records_owned_by_other_steps_or_held_today_are_untouched(self):
        rows = STACK + [
            market("p", "Via Ostiense", position_quality="precisa"),
            market("n", "Via Tiburtina", lat=None, lng=None, navigazione_sospesa_motivo="x"),
            market("h", "Via Appia", lat=None, lng=None, coordinate_sospese_motivo="other",
                   coordinate_originali={"lat": 41.9, "lng": 12.5}),
            market("new", "Via Nomentana", lat=None, lng=None),
        ]
        lookup = Lookup({})
        out, report, _ = run(rows, lookup=lookup, held_ids=frozenset({"new"}))
        self.assertEqual(out[3:], rows[3:])
        self.assertEqual(sum(report["excluded"].values()), 4)
        self.assertFalse(any(call.startswith(("Via Ostiense", "Via Tiburtina", "Via Appia", "Via Nomentana"))
                             for call in lookup.calls))

    def test_second_run_reuses_cache_and_changes_nothing(self):
        lookup = Lookup({"Via Corinto": [found("Via Corinto")]})
        first, _, cache = run(STACK, lookup=lookup)
        again = Lookup({})
        second, report, _ = run(first, cache=cache, lookup=again)
        self.assertEqual((second, again.calls, report["cache_hits"], report["cache_misses_reused"]),
                         (first, [], 1, 2))
        offline, report, _ = run(first, cache=cache)
        self.assertEqual((offline, report["status"]), (first, "offline_cache_only"))

    def test_changed_address_drops_the_old_street_point(self):
        first, _, cache = run(STACK, lookup=Lookup({"Via Corinto": [found("Via Corinto")]}))
        moved = [dict(first[0], indirizzo="Via Locke")] + first[1:]
        second, _, _ = run(moved, cache=cache)
        self.assertNotIn("posizione_fonte", second[0])
        self.assertIsNone(second[0]["lat"])
        self.assertEqual(second[0]["coordinate_sospese_motivo"], pr.PLACEHOLDER_REASON)

    def test_a_newer_source_point_wins_over_our_old_one(self):
        first, _, cache = run([market("a", "Via Corinto")], lookup=Lookup({"Via Corinto": [found("Via Corinto")]}))
        refreshed = [dict(first[0], lat=41.912345, lng=12.512345, position_quality="non_verificata")]
        second, _, _ = run(refreshed, cache=cache)
        self.assertEqual((second[0]["lat"], "posizione_fonte" in second[0]), (41.912345, False))

    def test_budget_rate_limit_and_errors_stop_cleanly_without_caching_errors(self):
        rows = [market(str(i), "Via Numero%s" % chr(65 + i), lat=None, lng=None) for i in range(5)]
        _, report, _ = run(rows, lookup=Lookup({}), max_lookups=2)
        self.assertEqual((report["lookups"], report["status"]), (2, "budget_exhausted"))
        limited = Lookup({"Via NumeroA": HTTPError("u", 429, "Too Many", {}, None)})
        _, report, cache = run(rows, lookup=limited)
        self.assertEqual((report["status"], len(limited.calls), cache["entries"]), ("stopped_http_429", 1, {}))
        broken = Lookup({"Via Numero" + c: OSError("down") for c in "ABCDE"})
        _, report, cache = run(rows, lookup=broken)
        self.assertEqual((report["status"], report["errors"], cache["entries"]), ("stopped_errors", 3, {}))

    def test_requests_respect_one_per_second(self):
        waits, ticks = [], iter(range(100))
        rows = [market(str(i), "Via Numero%s" % chr(65 + i), lat=None, lng=None) for i in range(3)]
        pr.resolve(rows, pr.empty_cache(), today=TODAY, istat=ISTAT, lookup=Lookup({}),
                   sleep=waits.append, clock=lambda: next(ticks) * 0.01)
        self.assertEqual(len(waits), 2)
        self.assertTrue(all(wait >= 1.0 for wait in waits))

    def test_misses_are_retried_after_ninety_days_only(self):
        _, _, cache = run(STACK, lookup=Lookup({}))
        later = Lookup({})
        run(STACK, cache=cache, lookup=later, today=date(2026, 12, 1))
        self.assertEqual(later.calls, [])
        run(STACK, cache=cache, lookup=later, today=date(2027, 1, 24))
        self.assertEqual(len(later.calls), 3)

    def test_request_identifies_the_app_and_never_sends_an_email(self):
        seen = []

        class Response:
            def __enter__(self): return self
            def __exit__(self, *a): return False
            def read(self, n): return b"[]"

        with patch("position_resolver.urlopen", lambda request, timeout: seen.append(request) or Response()):
            self.assertEqual(pr.nominatim("Via Corinto, Roma, Italia"), [])
        request = seen[0]
        self.assertEqual(request.get_header("User-agent"), pr.USER_AGENT)
        self.assertNotIn("@", request.full_url + pr.USER_AGENT)
        self.assertIn("countrycodes=it", request.full_url)
        self.assertIn("format=jsonv2", request.full_url)


class CacheAndGuardTests(unittest.TestCase):
    def test_cache_file_is_deterministic_lf_json_and_validated(self):
        _, _, cache = run(STACK, lookup=Lookup({"Via Corinto": [found("Via Corinto")]}))
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "geocode-cache.json"
            pr.save_cache(path, cache)
            raw = path.read_bytes()
            self.assertNotIn(b"\r\n", raw)
            self.assertEqual(json.loads(raw), cache)
            self.assertEqual(raw.decode("utf-8"), json.dumps(cache, ensure_ascii=False, indent=1, sort_keys=True) + "\n")
            self.assertEqual(pr.load_cache(path), cache)
            cache["entries"]["via corinto|roma|rm"]["osm"] = "file/1"
            with self.assertRaises(ValueError):
                pr.save_cache(path, cache)

    def test_exporter_keeps_provenance_only_with_its_own_point(self):
        out, _, _ = run(STACK, lookup=Lookup({"Via Corinto": [found("Via Corinto")]}))
        exported, error = normalize(out[0], TODAY)
        self.assertIsNone(error)
        self.assertEqual(exported["posizione_fonte"], out[0]["posizione_fonte"])
        self.assertEqual(exported["position_quality"], "approssimata")
        self.assertEqual(exported["coordinate_sospese_motivo"], pr.PLACEHOLDER_REASON)
        withdrawn, _ = normalize(out[1], TODAY)
        self.assertEqual(withdrawn["coordinate_originali"], {"lat": 41.9, "lng": 12.5})
        detached, _ = normalize(dict(out[0], lat=41.0), TODAY)
        self.assertNotIn("posizione_fonte", detached)

    def test_guards_reject_unowned_changes_leaks_and_unreproducible_points(self):
        cache = pr.empty_cache()
        out, _, _ = run(STACK, cache=cache, lookup=Lookup({"Via Corinto": [found("Via Corinto")]}))
        self.assertTrue(pr.verify_diff(STACK, out)["release_safe"])
        self.assertTrue(pr.verify_static(out, cache, today=TODAY, istat=ISTAT)["release_safe"])
        with self.assertRaisesRegex(ValueError, "unowned"):
            pr.verify_diff(STACK, [dict(out[0], nome="Altro")] + out[1:])
        with self.assertRaisesRegex(ValueError, "placeholder"):
            pr.verify_static(out[:2] + [STACK[2]], cache, today=TODAY, istat=ISTAT)
        with self.assertRaisesRegex(ValueError, "reproducible"):
            pr.verify_static([dict(out[0], indirizzo="Via Locke")] + out[1:], cache, today=TODAY, istat=ISTAT)
        with self.assertRaisesRegex(ValueError, "reproducible"):
            pr.verify_static(out, pr.empty_cache(), today=TODAY, istat=ISTAT)


if __name__ == "__main__":
    unittest.main()
