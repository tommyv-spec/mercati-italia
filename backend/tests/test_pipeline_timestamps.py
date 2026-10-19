"""Storage timestamp regression tests; scraper and database are local doubles."""
import importlib.util
import json
import sys
import tempfile
import types
import unittest
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from unittest.mock import Mock, patch


class Category(Enum):
    MARKET = "mercato"


class Recurrence(Enum):
    WEEKLY = "settimanale"


@dataclass
class Market:
    slug: str = "fixture-market"
    nome: str = "Mercato fixture"
    citta: str = "Firenze"
    provincia: str = "FI"
    regione: str = "Toscana"
    indirizzo: str = "Via di prova"
    lat: object = None
    lng: object = None
    luogo_nome: str = ""
    categoria: Category = Category.MARKET
    tags: list = field(default_factory=list)
    ricorrenza: Recurrence = Recurrence.WEEKLY
    ricorrenza_testo: str = "sabato"
    orario_testo: str = ""
    descrizione: str = ""
    date: list = field(default_factory=lambda: ["2026-10-17"])
    fonte_nome: str = "fixture"
    url_fonte: str = "https://example.org/markets/fixture"
    dati_grezzi: dict = field(default_factory=dict)


class Document:
    def __init__(self, initial=None):
        self.data = deepcopy(initial)
        self.updates = []
        self.sets = []
        self.collections = {}

    def get(self):
        return types.SimpleNamespace(exists=self.data is not None,
                                     to_dict=lambda: deepcopy(self.data))

    def update(self, values):
        self.updates.append(deepcopy(values))
        self.data.update(values)

    def set(self, values, merge=False):
        self.sets.append((deepcopy(values), merge))
        self.data = {**(self.data or {}), **values} if merge else deepcopy(values)

    def collection(self, name):
        if name not in self.collections:
            self.collections[name] = Collection()
        return self.collections[name]


class Collection:
    def __init__(self, documents=None):
        self.documents = documents or {}

    def document(self, slug):
        if slug not in self.documents:
            self.documents[slug] = Document()
        return self.documents[slug]


@contextmanager
def local_pipeline(database=None):
    """Import the actual orchestrator without optional scraper dependencies."""
    config = types.ModuleType("config")
    config.RawMarket = config.CleanMarket = Market
    config.REGIONI = ["Toscana"]
    config.FIREBASE_CREDENTIALS_PATH = ""
    config.FIREBASE_PROJECT_ID = "fixture"
    cleaner = types.ModuleType("cleaner")
    for name in ("clean_market", "are_duplicates", "merge_markets"):
        setattr(cleaner, name, Mock(side_effect=AssertionError("No cleaning in storage test")))
    cleaner.content_hash = Mock(return_value="fixture-content-hash")
    scraper = types.ModuleType("scraper_eventiesagre")
    scraper.scrape_eventiesagre = Mock(side_effect=AssertionError("No network in storage test"))
    firebase = types.ModuleType("firebase_admin")
    firebase._apps = {"fixture": object()}
    firebase.credentials = types.SimpleNamespace(Certificate=Mock(side_effect=AssertionError("No credentials")))
    firebase.firestore = types.SimpleNamespace(client=Mock(return_value=database))
    firebase.initialize_app = Mock(side_effect=AssertionError("No external database initialization"))
    modules = {"config": config, "cleaner": cleaner, "scraper_eventiesagre": scraper,
               "firebase_admin": firebase, "rich": types.ModuleType("rich")}
    for module_name, class_name in (("rich.console", "Console"), ("rich.table", "Table"),
                                    ("rich.panel", "Panel")):
        module = types.ModuleType(module_name)
        setattr(module, class_name, Mock())
        modules[module_name] = module
    spec = importlib.util.spec_from_file_location(
        "pipeline_timestamp_test_subject", Path(__file__).resolve().parents[1] / "pipeline.py")
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, modules):
        spec.loader.exec_module(module)
        yield module


class PipelineTimestampTests(unittest.TestCase):
    def assert_import_only(self, payload, before, after):
        recorded = datetime.fromisoformat(payload["importato_il"])
        self.assertIsNotNone(recorded.tzinfo)
        self.assertLessEqual(before, recorded)
        self.assertLessEqual(recorded, after)
        for key in ("aggiornato_il", "fonte_letta_il", "fonte_aggiornata_il", "verificato_il"):
            self.assertNotIn(key, payload)

    def test_json_export_records_import_but_does_not_claim_source_read_or_update(self):
        market = Market()
        before_market = asdict(market)
        with tempfile.TemporaryDirectory() as tmp, local_pipeline() as pipeline:
            path = Path(tmp) / "markets.json"
            before = datetime.now(timezone.utc)
            pipeline.step_store_json([market], str(path))
            after = datetime.now(timezone.utc)
            output = json.loads(path.read_text("utf-8"))
        self.assertEqual(len(output), 1)
        self.assert_import_only(output[0], before, after)
        self.assertEqual(output[0]["date"], ["2026-10-17"])
        self.assertEqual(asdict(market), before_market)

    def test_existing_database_timestamps_survive_a_new_catalog_import(self):
        existing = {"slug": "fixture-market", "aggiornato_il": "2020-01-01T09:00:00",
                    "fonte_aggiornata_il": "2019-12-01", "fonte_letta_il": "2020-01-01",
                    "verificato_il": "2019-12-02", "creato_il": "2019-12-01",
                    "extra_existing_field": "keep me"}
        doc = Document(existing)
        source_doc = Document({"ultimo_visto": "2020-01-01", "fonte_aggiornata_il": "2019-12-01"})
        doc.collections["fonti"] = Collection({"fixture": source_doc})
        collection = Collection({"fixture-market": doc})
        database = types.SimpleNamespace(collection=Mock(return_value=collection))
        with local_pipeline(database) as pipeline:
            before = datetime.now(timezone.utc)
            pipeline.step_store_db([Market()])
            after = datetime.now(timezone.utc)
        self.assertEqual(len(doc.updates), 1)
        self.assertEqual(doc.sets, [])
        self.assert_import_only(doc.updates[0], before, after)
        for key, value in existing.items():
            self.assertEqual(doc.data[key], value)
        self.assertEqual(len(source_doc.sets), 1)
        payload, merge = source_doc.sets[0]
        self.assertTrue(merge)
        self.assertNotIn("ultimo_visto", payload)
        self.assertEqual(payload["importato_il"], doc.updates[0]["importato_il"])
        self.assertEqual(source_doc.data["ultimo_visto"], "2020-01-01")
        self.assertEqual(source_doc.data["fonte_aggiornata_il"], "2019-12-01")

    def test_new_database_record_has_no_invented_legacy_source_or_verification_date(self):
        collection = Collection()
        database = types.SimpleNamespace(collection=Mock(return_value=collection))
        with local_pipeline(database) as pipeline:
            before = datetime.now(timezone.utc)
            pipeline.step_store_db([Market()])
            after = datetime.now(timezone.utc)
        doc = collection.document("fixture-market")
        self.assertEqual(len(doc.sets), 1)
        self.assert_import_only(doc.data, before, after)
        self.assertEqual(doc.data["creato_il"], doc.data["importato_il"])
        self.assertEqual(doc.data["date"], ["2026-10-17"])
        self.assertEqual(doc.data["status"], "non_confermato")


if __name__ == "__main__":
    unittest.main()
