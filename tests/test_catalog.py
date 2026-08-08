from pathlib import Path

import pytest
import yaml

from sapbdc.catalog import Mode, load_catalog


def test_catalog_loads_and_validates():
    cat = load_catalog()
    assert len(cat.objects) >= 20
    assert {o.id for o in cat.objects} == {o.id for o in cat.objects}, "object ids must be unique"
    assert cat.landscape.target.platform == "snowflake"


def test_every_object_names_a_known_source_system():
    cat = load_catalog()
    known = {s.id for s in cat.landscape.systems}
    assert all(o.source in known for o in cat.objects)


def test_unknown_source_system_is_rejected(tmp_path: Path):
    src = Path("config")
    for name in ("landscape.yaml", "policy.yaml", "cost_model.yaml"):
        (tmp_path / name).write_text((src / name).read_text(), encoding="utf-8")
    objects = yaml.safe_load((src / "objects.yaml").read_text())
    objects[0]["source"] = "does_not_exist"
    (tmp_path / "objects.yaml").write_text(yaml.safe_dump(objects), encoding="utf-8")

    with pytest.raises(ValueError, match="unknown source system"):
        load_catalog(tmp_path)


def test_mode_enum_covers_every_outcome_the_rules_can_return():
    assert {m.value for m in Mode} == {
        "SHARE",
        "REPLICATE",
        "FEDERATE",
        "HYBRID",
        "KEEP_IN_SAP",
    }
