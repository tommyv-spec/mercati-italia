import copy
import json
import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from publisher_refresh import catalog_resources
from source_lifecycle import digest

DATA = Path(__file__).resolve().parents[1] / "data"
CONTRACTS = json.loads((DATA / "market-source-contracts.json").read_text())
ADMISSIONS = json.loads((DATA / "approved-source-admissions.json").read_text())
POLICY = json.loads((DATA.parent / "autopilot_policy.json").read_text())
PAGES = {"schema": 1, "publication_channel": "dev-only", "sources": []}
TODAY = date(2026, 10, 19)
BOLOGNA = next(p for p in CONTRACTS["raw_profiles"] if p["source_id"] == "bologna")
CORCIANO = next(p for p in CONTRACTS["raw_profiles"] if p["source_id"] == "corciano")
VENICE = "https://www.happings.com/it/mercati-settimanali-a-venezia.html"
VENICE_FINAL = "https://www.happings.com/it/mercati-settimanali-a-venezia-e-provincia/"
TREVISO = "https://www.happings.com/it/mercati-settimanali-a-treviso.html"
SPINEA = "https://www.happings.com/it/mercato-settimanale-a-spinea.html"


def market(slug, url):
    return {"slug": slug, "url_fonte": url, "indirizzo": "", "orario_testo": ""}


def happings_market(slug, url=VENICE, *, city="Spinea", province="VE", **changes):
    row = {**market(slug, url), "nome": "Mercato settimanale di " + city,
           "citta": city, "provincia": province, "regione": "Veneto",
           "fonte": "happings.com", "ricorrenza_testo": "settimanale - mercoledì"}
    row.update(changes)
    return row


def happings_acquisition_report(rows, selected_urls, *, pages=(), failures=(), **changes):
    protected = sorted(row["slug"] for row in rows if row.get("fonte") == "happings.com")
    catalog_ids = sorted(row["slug"] for row in rows)
    report = {"schema": 1, "publisher": "happings.com", "date": TODAY.isoformat(),
              "enabled": True, "fetch_authorized": True, "status": "retrieved",
              "protected_existing_market_ids": len(protected), "protected_ids_sha256": digest(protected),
              "protected_catalog_market_ids": len(catalog_ids),
              "protected_catalog_ids_sha256": digest(catalog_ids),
              "selected_urls": selected_urls, "source_pages": list(pages),
              "page_failures": list(failures), "source_evidence_reused": False}
    report.update(changes)
    return report


def coverage(rows, **kwargs):
    settings = dict(source_contracts=CONTRACTS, source_admissions=ADMISSIONS,
                    source_policy=POLICY["sources"], admissions_enabled=True, today=TODAY)
    settings.update(kwargs)
    return catalog_resources(rows, PAGES, **settings)


class SourceRefreshCoverageTests(unittest.TestCase):
    def test_approved_bologna_contract_is_routed_without_enabling_duplicate_adapter(self):
        rows = [market("bo-open-source-id", BOLOGNA["attribution_url"])]
        before = copy.deepcopy(rows)
        result = coverage(rows)
        resource = result["resources"][0]
        self.assertEqual(resource["mode"], "source_contract_active")
        self.assertEqual(resource["source_layout_status"], "supported")
        self.assertEqual(resource["source_read_status"], "not_observed")
        self.assertEqual({r["source_id"]: r["mode"] for r in resource["readers"]}, {
            BOLOGNA["id"]: "source_contract_active", "bologna": "official_adapter_disabled",
        })
        self.assertEqual(rows, before)

    def test_global_or_reviewed_profile_disable_is_explicit(self):
        row = market("bo-open-source-id", BOLOGNA["attribution_url"])
        self.assertEqual(coverage([row], admissions_enabled=False)["resources"][0]["mode"],
                         "source_contract_disabled")
        config, registry = copy.deepcopy(CONTRACTS), copy.deepcopy(ADMISSIONS)
        profile = next(p for p in config["raw_profiles"] if p["id"] == BOLOGNA["id"])
        profile["enabled"] = False
        certificate = next(a for a in registry["approvals"] if a["source_id"] == profile["id"])
        certificate["reviewed_profile_sha256"] = digest(profile)
        result = coverage([row], source_contracts=config, source_admissions=registry)
        self.assertEqual(result["resources"][0]["mode"], "source_contract_disabled")
        self.assertEqual(result["resources"][0]["source_read_status"], "disabled")

    def test_absent_or_invalid_registry_does_not_infer_permission_from_url(self):
        row = market("bo-open-source-id", BOLOGNA["attribution_url"])
        for registry, expected in ((None, "source_contract_registry_missing"),
                                   ({}, "source_contract_registry_invalid")):
            with self.subTest(registry=registry):
                resource = coverage([row], source_admissions=registry)["resources"][0]
                self.assertEqual(resource["mode"], expected)
                self.assertEqual(resource["source_layout_status"], "approval_required")
        wrong = copy.deepcopy(ADMISSIONS)
        wrong["approvals"][1]["reviewed_profile_sha256"] = "0" * 64
        self.assertEqual(coverage([row], source_admissions=wrong)["resources"][0]["mode"],
                         "source_contract_registry_invalid")

    def test_disabled_profile_still_requires_matching_reviewed_certificate(self):
        config = copy.deepcopy(CONTRACTS)
        next(p for p in config["raw_profiles"] if p["id"] == BOLOGNA["id"])["enabled"] = False
        result = coverage([market("bo-open-source-id", BOLOGNA["attribution_url"])],
                          source_contracts=config)
        self.assertEqual(result["resources"][0]["mode"], "source_contract_registry_invalid")

    def test_wrong_certificate_fields_do_not_become_an_active_route(self):
        registry = copy.deepcopy(ADMISSIONS)
        registry["approvals"][1]["source_specific_geo_approval"] = True
        result = coverage([market("bo-open-source-id", BOLOGNA["attribution_url"])],
                          source_admissions=registry)
        self.assertEqual(result["resources"][0]["mode"], "source_contract_registry_invalid")

    def test_known_official_adapter_remains_supported_when_source_is_unavailable(self):
        row = market("pg-corciano-source-id", CORCIANO["attribution_url"])
        result = coverage([row], source_status={"corciano": {"status": "unavailable"}})
        resource = result["resources"][0]
        self.assertEqual(resource["mode"], "official_adapter")
        self.assertEqual(resource["source_layout_status"], "supported")
        self.assertEqual(resource["source_read_status"], "unavailable")
        self.assertEqual(result["market_dispositions"], {"official_adapter": 1})

    def test_adapter_policy_disable_does_not_reuse_a_previous_successful_fetch(self):
        source = next(p for p in CONTRACTS["normalized_profiles"] if p["id"] == "milano")
        row = market("mi-mss-source-id", source["source_pages"][0])
        policy = copy.deepcopy(POLICY["sources"])
        next(p for p in policy if p["id"] == "milano")["enabled"] = False
        resource = coverage([row], source_policy=policy, official_urls=[row["url_fonte"]],
                            source_status={"milano": {"status": "retrieved"}})["resources"][0]
        self.assertEqual(resource["mode"], "official_adapter_disabled")
        self.assertEqual(resource["source_read_status"], "disabled")

    def test_host_only_adapter_requires_its_source_identity(self):
        good = market("fi-feelflorence-source-id", "https://www.feelflorence.it/it/punti-di-interesse/mercato")
        other = market("unknown-source-id", "https://www.feelflorence.it/it/altro-elenco")
        resources = {r["url"]: r for r in coverage([good, other])["resources"]}
        self.assertEqual(resources[good["url_fonte"]]["mode"], "official_adapter")
        self.assertEqual(resources[other["url_fonte"]]["mode"], "source_layout_needed")

    def test_contract_read_status_requires_same_registry_contract_and_reference_day(self):
        row = market("bo-open-source-id", BOLOGNA["attribution_url"])
        report = {"source_contract_sha256": digest(CONTRACTS),
                  "source_registry_sha256": digest(ADMISSIONS), "reference_date": TODAY.isoformat(),
                  "per_source": {BOLOGNA["id"]: {"status": "publisher_source_held_for_review"}}}
        resource = coverage([row], admission_report=report)["resources"][0]
        self.assertEqual(resource["mode"], "source_contract_active")
        self.assertEqual(resource["source_read_status"], "publisher_source_held_for_review")
        for key, value in (("source_contract_sha256", "0" * 64),
                           ("source_registry_sha256", "0" * 64), ("reference_date", "2026-10-18")):
            with self.subTest(key=key):
                wrong = {**report, key: value}
                resource = coverage([row], admission_report=wrong)["resources"][0]
                self.assertEqual(resource["source_read_status"], "not_observed")

    def test_happings_and_unrelated_urls_are_not_granted_coverage(self):
        result = coverage([market("legacy", "https://www.happings.com/it/mercati.html"),
                           market("other", "https://unknown.example/markets")])
        self.assertEqual(result["market_dispositions"], {
            "happings_gate_not_active": 1, "source_layout_needed": 1,
        })

    def test_happings_flag_does_not_grant_a_reader_to_every_publisher_path(self):
        rows = [happings_market("index"), happings_market("town", SPINEA),
                happings_market("festival", "https://www.happings.com/it/sagra-a-spinea.html"),
                happings_market("other-town", "https://www.happings.com/it/mercato-settimanale-a-dolo.html"),
                happings_market("wrong-scope", province="PD"),
                happings_market("tracking-url", VENICE + "?utm_source=legacy")]
        before = copy.deepcopy(rows)
        result = coverage(rows, happings_enabled=True)
        self.assertEqual(result["market_layout_statuses"], {"supported": 2, "unsupported": 4})
        self.assertEqual(result["market_dispositions"]["happings_province_index"], 2)
        town = next(item for item in result["resources"] if item["url"] == SPINEA)
        self.assertEqual(town["source_route_url"], VENICE)
        self.assertEqual(town["source_route_method"], "province_index_join")
        self.assertEqual(town["source_read_status"], "not_observed")
        self.assertEqual(rows, before)

    def test_happings_town_needs_an_existing_coherent_province_source(self):
        row = happings_market("town", SPINEA)
        unsupported = coverage([row], happings_enabled=True)
        self.assertEqual(unsupported["market_layout_statuses"], {"unsupported": 1})
        other_province = happings_market("other", TREVISO, city="Treviso", province="TV")
        result = coverage([row, other_province], happings_enabled=True)
        self.assertEqual(result["market_layout_statuses"], {"unsupported": 1, "supported": 1})
        self.assertEqual(next(item for item in result["resources"] if item["url"] == SPINEA)["mode"],
                         "happings_source_scope_unproven")

    def test_happings_town_punctuation_does_not_reconstruct_missing_letters(self):
        rows = [happings_market("index"),
                happings_market("punctuation", SPINEA.replace("spinea.html", "spinea--.html")),
                happings_market("missing-letter", SPINEA.replace("spinea.html", "spine--.html"))]
        result = coverage(rows, happings_enabled=True)
        self.assertEqual(result["market_layout_statuses"], {"supported": 2, "unsupported": 1})

    def test_happings_coverage_persists_after_addresses_are_filled(self):
        rows = [happings_market("index", indirizzo="Via Prova 10"),
                happings_market("town", SPINEA, indirizzo="Piazza Prova 20")]
        result = coverage(rows, happings_enabled=True)
        self.assertEqual(result["market_layout_statuses"], {"supported": 2})
        self.assertEqual(sum(item["missing_address"] for item in result["resources"]), 0)

    def test_happings_shared_url_preserves_mixed_geographic_dispositions(self):
        rows = [happings_market("supported"), happings_market("invalid", province="PD")]
        result = coverage(rows, happings_enabled=True)
        self.assertEqual(result["markets"], 2)
        self.assertEqual(result["unique_primary_urls"], 1)
        self.assertEqual(result["market_layout_statuses"], {"supported": 1, "unsupported": 1})
        self.assertEqual(sum(item["markets"] for item in result["resources"]), 2)
        self.assertEqual(len(result["resources"]), 2)

    def test_happings_read_statuses_follow_pages_not_whole_domain(self):
        rows = [happings_market("index"), happings_market("town", SPINEA),
                happings_market("failed", TREVISO, city="Treviso", province="TV"),
                happings_market("unselected", "https://www.happings.com/it/mercati-settimanali-a-padova.html",
                                city="Padova", province="PD")]
        page = {"requested_url": VENICE, "final_url": VENICE_FINAL,
                "source_html_sha256": "a" * 64, "status": "parsed", "source_rows": 1}
        report = happings_acquisition_report(rows, [VENICE, TREVISO], pages=[page],
                                            failures=[{"requested_url": TREVISO, "error_type": "HTTPError"}],
                                            status="partial_unavailable")
        result = coverage(rows, happings_enabled=True, happings_report=report)
        self.assertEqual(result["market_layout_statuses"], {"supported": 4})
        self.assertEqual(result["market_read_statuses"], {"retrieved": 2, "unavailable": 1, "not_selected": 1})
        report["source_evidence_reused"] = True
        resumed = coverage(rows, happings_enabled=True, happings_report=report)
        self.assertEqual(resumed["market_read_statuses"],
                         {"resumed_checkpoint": 2, "unavailable": 1, "not_selected": 1})

    def test_happings_layout_change_and_absent_checkpoint_are_explicit(self):
        rows = [happings_market("index")]
        page = {"requested_url": VENICE, "final_url": VENICE_FINAL,
                "source_html_sha256": "a" * 64, "status": "layout_changed"}
        report = happings_acquisition_report(rows, [VENICE], pages=[page], status="layout_changed")
        result = coverage(rows, happings_enabled=True, happings_report=report)
        self.assertEqual(result["market_layout_statuses"], {"supported": 1})
        self.assertEqual(result["market_read_statuses"], {"layout_changed": 1})
        for status in ("offline_skipped", "resume_missing_evidence"):
            with self.subTest(status=status):
                report = happings_acquisition_report(rows, [VENICE], status=status)
                self.assertEqual(coverage(rows, happings_enabled=True, happings_report=report)
                                 ["market_read_statuses"], {status: 1})

    def test_happings_read_report_must_match_date_cohort_and_observed_page(self):
        rows = [happings_market("index")]
        page = {"requested_url": VENICE, "final_url": VENICE_FINAL,
                "source_html_sha256": "a" * 64, "status": "parsed", "source_rows": 1}
        report = happings_acquisition_report(rows, [VENICE], pages=[page])
        variants = [dict(report, date="2026-10-18"),
                    dict(report, protected_ids_sha256="0" * 64),
                    dict(report, selected_urls=[TREVISO]),
                    dict(report, source_pages=[dict(page, final_url=TREVISO)]),
                    dict(report, source_pages=[dict(page, source_html_sha256="invalid")]),
                    dict(report, page_failures=[{"requested_url": VENICE, "error_type": "HTTPError"}])]
        for invalid in variants:
            with self.subTest(report=invalid):
                result = coverage(rows, happings_enabled=True, happings_report=invalid)
                self.assertEqual(result["market_layout_statuses"], {"supported": 1})
                self.assertEqual(result["market_read_statuses"], {"not_observed": 1})

    def test_happings_report_cannot_bypass_inactive_authorization(self):
        rows = [happings_market("index")]
        report = happings_acquisition_report(rows, [VENICE], status="blocked_rights", fetch_authorized=False)
        result = coverage(rows, happings_enabled=True, happings_report=report)
        self.assertEqual(result["market_layout_statuses"], {"disabled": 1})
        self.assertEqual(result["market_read_statuses"], {"disabled": 1})

    def test_secondary_comparison_does_not_change_primary_reader_coverage(self):
        origin = "https://www.eventiesagre.it/Mercati-Settimanali/spinea.html"
        rows = [happings_market("index"),
                happings_market("other-origin", origin, fonte="eventiesagre.it", indirizzo="Via Roma"),
                happings_market("empty-address", origin, fonte="eventiesagre.it"),
                happings_market("vague-address", origin, fonte="eventiesagre.it", indirizzo="centro storico")]
        before = copy.deepcopy(rows)
        result = coverage(rows, happings_enabled=True)
        resource = next(r for r in result["resources"] if r["url"] == origin)
        self.assertEqual(resource["mode"], "source_layout_needed")
        self.assertEqual(resource["source_layout_status"], "unsupported")
        self.assertEqual(resource["source_read_status"], "not_read")
        self.assertEqual(resource["secondary_corroboration_routes"], [
            {"publisher": "happings.com", "source_route_url": VENICE,
             "eligible_markets": 1, "source_read_status": "not_observed"}])
        self.assertEqual(result["market_layout_statuses"], {"supported": 1, "unsupported": 3})
        self.assertEqual(result["secondary_corroboration"], {
            "publisher": "happings.com", "mode": "existing_address_exact_match",
            "counts_describe": "comparison_eligibility", "eligible_markets": 1,
            "unique_source_urls": 1, "market_read_statuses": {"not_observed": 1}})
        self.assertEqual(rows, before)

    def test_secondary_read_status_uses_existing_page_and_all_catalog_ids(self):
        origin = "https://www.eventiesagre.it/Mercati-Settimanali/spinea.html"
        rows = [happings_market("index"),
                happings_market("other-origin", origin, fonte="eventiesagre.it", indirizzo="Via Roma")]
        page = {"requested_url": VENICE, "final_url": VENICE_FINAL,
                "source_html_sha256": "a" * 64, "status": "parsed", "source_rows": 1}
        report = happings_acquisition_report(rows, [VENICE], pages=[page])
        result = coverage(rows, happings_enabled=True, happings_report=report)
        self.assertEqual(result["market_read_statuses"], {"retrieved": 1, "not_read": 1})
        self.assertEqual(result["secondary_corroboration"]["market_read_statuses"], {"retrieved": 1})
        for changes in ({"protected_catalog_ids_sha256": "0" * 64},
                        {"protected_catalog_market_ids": 1}):
            with self.subTest(changes=changes):
                invalid = coverage(rows, happings_enabled=True, happings_report={**report, **changes})
                self.assertEqual(invalid["secondary_corroboration"]["market_read_statuses"],
                                 {"not_observed": 1})
        changed = copy.deepcopy(rows)
        changed[1]["slug"] = "different-origin-id"
        result = coverage(changed, happings_enabled=True, happings_report=report)
        self.assertEqual(result["secondary_corroboration"]["market_read_statuses"], {"not_observed": 1})

    def test_secondary_comparison_cannot_create_pages_or_bypass_inactive_phase(self):
        origin = "https://www.eventiesagre.it/Mercati-Settimanali/spinea.html"
        other = happings_market("other-origin", origin, fonte="eventiesagre.it", indirizzo="Via Roma")
        self.assertEqual(coverage([other], happings_enabled=True)["secondary_corroboration"]
                         ["eligible_markets"], 0)
        rows = [happings_market("index"), other]
        self.assertEqual(coverage(rows)["secondary_corroboration"]["eligible_markets"], 0)
        report = happings_acquisition_report(rows, [VENICE], status="blocked_rights", fetch_authorized=False)
        self.assertEqual(coverage(rows, happings_enabled=True, happings_report=report)
                         ["secondary_corroboration"]["eligible_markets"], 0)

    def test_secondary_outage_is_separate_from_field_verification(self):
        origin = "https://www.eventiesagre.it/Mercati-Settimanali/spinea.html"
        rows = [happings_market("index"),
                happings_market("other-origin", origin, fonte="eventiesagre.it", indirizzo="Via Roma")]
        report = happings_acquisition_report(rows, [VENICE], status="unavailable",
                                            failures=[{"requested_url": VENICE, "error_type": "HTTPError"}])
        result = coverage(rows, happings_enabled=True, happings_report=report)
        self.assertEqual(result["secondary_corroboration"]["eligible_markets"], 1)
        self.assertEqual(result["secondary_corroboration"]["market_read_statuses"], {"unavailable": 1})
        self.assertEqual(result["market_layout_statuses"], {"supported": 1, "unsupported": 1})
        self.assertNotIn("verified_markets", result["secondary_corroboration"])


if __name__ == "__main__":
    unittest.main()
