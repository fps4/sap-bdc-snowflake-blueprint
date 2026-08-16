"""The generator's contract: a mode is a binding, and a constraint is a build failure.

The dbt project has its own tests — they run inside `dbt build` and assert things
about data. These assert the things that must hold *before* dbt ever runs, and the
one that dbt cannot check because it is about two files agreeing across a language
boundary (the sentinel).
"""

from pathlib import Path

import pytest
import yaml

from sapbdc.catalog import Mode, load_catalog
from sapbdc.dbtgen import (
    decided_model_sql,
    load_transform_config,
    register_seed_csv,
    sources_yml,
    write_all,
)
from sapbdc.rules import decide_all

ROOT = Path(__file__).resolve().parents[1]
TRANSFORM = ROOT / "transform"


@pytest.fixture(scope="module")
def decisions():
    cat = load_catalog()
    return decide_all(cat), cat, load_transform_config()


def test_every_bound_object_exists_in_the_catalog(decisions):
    _, cat, tcfg = decisions
    known = {o.id for o in cat.objects}
    assert set(tcfg.objects) <= known


def test_sources_are_grouped_by_the_mode_that_decided_them(decisions):
    ds, cat, tcfg = decisions
    doc = yaml.safe_load(sources_yml(ds, cat, tcfg).split("\n\n", 1)[1])
    by_group = {s["name"]: s for s in doc["sources"]}

    for mode, binding in tcfg.bindings.items():
        if binding.source_name not in by_group:
            continue
        for table in by_group[binding.source_name]["tables"]:
            assert table["meta"]["mode"] == mode.value


def test_exactly_one_binding_per_object_is_the_decided_one(decisions):
    ds, cat, tcfg = decisions
    doc = yaml.safe_load(sources_yml(ds, cat, tcfg).split("\n\n", 1)[1])
    decided = {}
    for source in doc["sources"]:
        for table in source["tables"]:
            meta = table["meta"]
            decided.setdefault(meta["object_id"], 0)
            decided[meta["object_id"]] += int(meta["is_decided_binding"])
    assert decided, "no bindings were emitted at all"
    assert all(n == 1 for n in decided.values()), decided


def test_the_share_binding_is_a_file_and_not_a_table(decisions):
    """A share that renders as a relation in your own account is a copy with a nicer
    name. The binding has to stay an external location or the claim is cosmetic."""
    ds, cat, tcfg = decisions
    doc = yaml.safe_load(sources_yml(ds, cat, tcfg).split("\n\n", 1)[1])
    share = next(s for s in doc["sources"] if s["name"] == tcfg.bindings[Mode.SHARE].source_name)
    assert "external_location" in share["meta"]
    assert "database" not in share


def test_an_object_held_in_sap_gets_no_source_and_no_model(decisions, tmp_path: Path):
    """R1 has to survive the trip into the transformation layer.

    Rewrites ACDOCA's governance so the residency rule holds it in SAP, then asserts
    that the generator emits nothing to select from and that the decided model
    refuses to compile rather than quietly falling back to another binding.
    """
    _, _, tcfg = decisions
    for name in ("landscape.yaml", "policy.yaml", "cost_model.yaml", "transform.yaml"):
        (tmp_path / name).write_text((ROOT / "config" / name).read_text(), encoding="utf-8")

    objects = yaml.safe_load((ROOT / "config" / "objects.yaml").read_text())
    acdoca = next(o for o in objects if o["id"] == "ACDOCA")
    acdoca["governance"]["residency"] = ["eu-central-1-de"]
    acdoca["governance"]["pii"] = True
    (tmp_path / "objects.yaml").write_text(yaml.safe_dump(objects), encoding="utf-8")

    cat = load_catalog(tmp_path)
    ds = decide_all(cat)
    assert next(d for d in ds if d.object_id == "ACDOCA").mode is Mode.KEEP_IN_SAP

    rendered = sources_yml(ds, cat, tcfg)
    doc = yaml.safe_load(rendered.split("\n\n", 1)[1])
    emitted = {t["meta"]["object_id"] for s in doc["sources"] for t in s["tables"]}
    assert "ACDOCA" not in emitted
    assert "ACDOCA" in rendered, "the exclusion must still be stated, not silently dropped"

    model = decided_model_sql(ds, tcfg)
    assert "raise_compiler_error" in model
    assert "select" not in model.split("{{")[1]


def test_generation_is_deterministic(decisions, tmp_path: Path):
    """CI gates the committed output against a re-run, so two runs must be identical."""
    ds, cat, tcfg = decisions
    first = [p.read_text(encoding="utf-8") for p in write_all(ds, cat, tcfg, tmp_path / "a")]
    second = [p.read_text(encoding="utf-8") for p in write_all(ds, cat, tcfg, tmp_path / "b")]
    assert first == second


def test_the_committed_dbt_files_match_the_register(decisions, tmp_path: Path):
    """The same gate CI runs, so a stale generated file fails locally first."""
    ds, cat, tcfg = decisions
    for path in write_all(ds, cat, tcfg, tmp_path):
        committed = TRANSFORM / path.relative_to(tmp_path)
        assert committed.read_text(encoding="utf-8") == path.read_text(encoding="utf-8"), (
            f"{committed.relative_to(ROOT)} is stale — run `make dbt-sources` and commit it"
        )


def test_the_seed_carries_every_object(decisions):
    ds, cat, _ = decisions
    rows = register_seed_csv(ds, cat).strip().splitlines()
    assert len(rows) == len(cat.objects) + 1


def test_the_dbt_sentinel_matches_the_simulation(decisions):
    """A sentinel that drifts turns the staleness test green for the wrong reason.

    `seam_binding_audit` asks each binding whether it can see the row the simulation
    changes after setup, and it recognises that row by amount. If the two constants
    ever diverge, no binding sees the change, every expectation reads `false`, and a
    test that was proving something starts proving nothing — silently.
    """
    from sapbdc.sim.modes import SENTINEL_AMOUNT

    project = yaml.safe_load((TRANSFORM / "dbt_project.yml").read_text(encoding="utf-8"))
    assert project["vars"]["sentinel_amount"] == SENTINEL_AMOUNT


def test_dbt_is_not_on_the_default_path():
    """ADR-0001: `make demo` must run with no dbt installed."""
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    required = pyproject.split("dependencies = [", 1)[1].split("]", 1)[0]
    assert "dbt" not in required
