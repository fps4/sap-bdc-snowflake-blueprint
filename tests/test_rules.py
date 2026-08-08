"""Each test pins one rule, so a change to the rule set has to be deliberate."""

import copy

from sapbdc.catalog import Mode, load_catalog
from sapbdc.econ import DAYS_PER_MONTH
from sapbdc.rules import decide_all, decide_object


def _cat():
    return load_catalog()


def _obj(cat, object_id):
    return next(o for o in cat.objects if o.id == object_id)


def _decisions():
    cat = _cat()
    return cat, {d.object_id: d for d in decide_all(cat)}


# ---- R1 · residency and personal data ---------------------------------------

def test_r1_residency_plus_pii_keeps_the_workload_in_sap():
    _, d = _decisions()
    assert d["PA0002"].mode is Mode.KEEP_IN_SAP
    assert d["PA0002"].rule_id == "R1"
    assert Mode.REPLICATE in d["PA0002"].eliminated
    assert Mode.FEDERATE in d["PA0002"].eliminated


def test_r1_prices_the_forbidden_options_anyway():
    """A constraint nobody has priced is a constraint somebody will argue away."""
    _, d = _decisions()
    assert d["PA0002"].economics, "eliminated modes must still be costed"
    assert d["PA0002"].economics[Mode.REPLICATE].monthly_eur > 0


def test_r1_residency_without_pii_leaves_federation_standing():
    """Only results cross, never the object — so a copy is out but a query is not."""
    cat = _cat()
    obj = copy.deepcopy(_obj(cat, "MSEG"))
    obj.governance.residency = ["ap-southeast-2"]
    obj.governance.pii = False
    decision = decide_object(obj, cat)
    assert decision.mode is not Mode.KEEP_IN_SAP
    assert Mode.REPLICATE in decision.eliminated
    assert Mode.FEDERATE not in decision.eliminated


# ---- R2 · delta capability ---------------------------------------------------

def test_r2_no_delta_above_the_ceiling_rules_out_replication():
    cat, d = _decisions()
    zfi = d["ZFI_ALLOC"]
    assert _obj(cat, "ZFI_ALLOC").delta_capability == "none"
    assert Mode.REPLICATE in zfi.eliminated
    assert "no-delta-at-volume" in zfi.flags


def test_r2_no_delta_below_the_ceiling_is_only_a_note():
    cat, d = _decisions()
    kna1 = d["KNA1"]
    assert _obj(cat, "KNA1").size_gb < cat.policy.delta.full_reload_ceiling_gb
    assert Mode.REPLICATE not in kna1.eliminated
    assert any("full reload per" in n for n in kna1.notes)


def test_r2_flags_slt_because_it_changes_the_source_system():
    """An SLT trigger is a change to a live ERP's runtime, so it must be visible on
    the card rather than buried in a pipeline config."""
    cat = _cat()
    obj = copy.deepcopy(_obj(cat, "PA0002"))
    # Lift the residency constraint so the object reaches R2 at all — R1 exits early
    # for the catalog's real HR objects, which never cross the seam.
    obj.governance.residency = [cat.landscape.target.region]
    obj.governance.pii = False
    assert obj.delta_capability == "slt"
    assert "slt-trigger-on-source" in decide_object(obj, cat).flags


# ---- R4 · latency under concurrency -----------------------------------------

def test_r4_federation_fails_the_slo_at_peak_concurrency_not_at_rest():
    cat = _cat()
    obj = _obj(cat, "ACDOCA")
    decision = decide_object(obj, cat)
    fed = decision.economics[Mode.FEDERATE]
    assert fed.p95_latency_seconds > obj.consumer.latency_slo_seconds
    assert Mode.FEDERATE in decision.eliminated

    # The same object at low concurrency passes: the concurrency term, not the
    # object, is what eliminates federation here.
    quiet = copy.deepcopy(obj)
    quiet.consumer.peak_concurrency = 1
    assert Mode.FEDERATE not in decide_object(quiet, cat).eliminated


# ---- R5 · share availability -------------------------------------------------

def test_r5_share_needs_a_bdc_data_product():
    cat, d = _decisions()
    assert _obj(cat, "BSEG").bdc_data_product is False
    assert Mode.SHARE in d["BSEG"].eliminated


def test_r5_inbound_objects_are_never_shared():
    cat, d = _decisions()
    for oid in ("SF_MKT_TOUCHPOINTS", "SF_WEB_SESSIONS"):
        assert _obj(cat, oid).direction == "inbound"
        assert d[oid].mode is not Mode.SHARE
        assert Mode.SHARE in d[oid].eliminated


# ---- R6 · semantics ----------------------------------------------------------

def test_r6_semantics_buys_a_share_only_within_the_policy_premium():
    cat, d = _decisions()
    acdoca = d["ACDOCA"]
    assert acdoca.mode is Mode.SHARE
    assert acdoca.rule_id == "R6"
    premium = (
        acdoca.economics[Mode.SHARE].monthly_eur
        / acdoca.economics[Mode.REPLICATE].monthly_eur
    )
    assert 1.0 < premium <= cat.policy.semantics.max_premium_ratio


def test_r6_a_premium_above_policy_falls_back_to_economics():
    cat = _cat()
    cat.policy.semantics.max_premium_ratio = 1.0001
    decision = decide_object(_obj(cat, "ACDOCA"), cat)
    # The share loses; what economics chose instead (here a replicate leg, which R8
    # then splits) is not the point — the point is that the premium was refused and
    # said so.
    assert decision.mode is not Mode.SHARE
    assert any("above the" in n for n in decision.notes)


# ---- R7 · economics ----------------------------------------------------------

def test_r7_chooses_the_cheapest_mode_that_survived():
    cat, decisions = _decisions()
    for d in decisions.values():
        if d.rule_id != "R7":
            continue
        survivors = {
            m: e for m, e in d.economics.items() if m not in d.eliminated
        }
        assert d.mode is min(survivors, key=lambda m: survivors[m].monthly_eur)


def test_r7_never_picks_an_eliminated_mode():
    _, decisions = _decisions()
    for d in decisions.values():
        assert d.mode not in d.eliminated


# ---- R8 · hybrid -------------------------------------------------------------

def test_r8_splits_an_object_whose_drilldown_is_rare_and_tolerant():
    cat, d = _decisions()
    matdoc = d["MATDOC"]
    assert matdoc.mode is Mode.HYBRID
    obj = _obj(cat, "MATDOC")
    assert obj.consumer.detail_queries_per_day <= cat.policy.hybrid.max_detail_queries_per_day
    # ...and it is priced as the copy plus the federated detail traffic, not as
    # a copy with the detail waved through for free.
    assert matdoc.monthly_eur > matdoc.economics[Mode.REPLICATE].monthly_eur


def test_r8_does_not_split_when_the_drilldown_is_frequent():
    cat = _cat()
    obj = copy.deepcopy(_obj(cat, "MATDOC"))
    obj.consumer.detail_queries_per_day = 500
    assert decide_object(obj, cat).mode is Mode.REPLICATE


# ---- whole-catalog invariants ------------------------------------------------

def test_every_object_gets_a_decision_with_a_reason():
    _, decisions = _decisions()
    assert len(decisions) == len(_cat().objects)
    for d in decisions.values():
        assert d.primary_reason.strip()
        assert d.rule_id


def test_deciding_is_deterministic():
    cat = _cat()
    assert [d.mode for d in decide_all(cat)] == [d.mode for d in decide_all(cat)]


def test_the_decision_beats_replicating_everything():
    """Not a claim about savings — a check that the engine is doing something."""
    cat, decisions = _decisions()
    decided = sum(d.monthly_eur for d in decisions.values())
    naive = sum(d.economics[Mode.REPLICATE].monthly_eur for d in decisions.values())
    assert decided < naive


def test_hybrid_pricing_matches_its_definition():
    _, d = _decisions()
    m = d["MATDOC"]
    expected = (
        m.economics[Mode.REPLICATE].monthly_eur
        + m.economics[Mode.FEDERATE].variable_eur_per_query
        * m.detail_queries_per_day
        * DAYS_PER_MONTH
    )
    assert m.monthly_eur == expected
