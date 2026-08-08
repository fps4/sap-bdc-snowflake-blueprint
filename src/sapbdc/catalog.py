"""Typed catalog — the landscape, the objects, the policy and the cost model.

Everything the decision engine reasons about is data on disk under ``config/``.
Nothing about a particular estate is compiled into the rules (ADR-0005), so
pointing this at a different landscape is an edit to YAML, not to Python.
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field

CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"


class Mode(StrEnum):
    """The integration modes an object can be assigned.

    ``SHARE`` and ``KEEP_IN_SAP`` are the two most reference architectures leave
    out, and they are the two that most often turn out to be right.
    """

    SHARE = "SHARE"
    REPLICATE = "REPLICATE"
    FEDERATE = "FEDERATE"
    HYBRID = "HYBRID"
    KEEP_IN_SAP = "KEEP_IN_SAP"


#: The modes the economics stage costs and compares. HYBRID is derived from
#: REPLICATE afterwards; KEEP_IN_SAP is what is left when nothing may cross.
COSTED_MODES = (Mode.SHARE, Mode.REPLICATE, Mode.FEDERATE)

DeltaCapability = Literal["cds", "odp", "slt", "none", "native"]
Semantics = Literal["high", "medium", "low"]
JoinLocality = Literal["sap", "snowflake", "mixed"]
Direction = Literal["outbound", "inbound"]


class ConsumerProfile(BaseModel):
    """How the object is actually used. The half of the decision that has nothing
    to do with the object's size."""

    queries_per_day: float
    peak_concurrency: int
    scan_gb_per_query: float
    result_gb_per_query: float
    latency_slo_seconds: float
    freshness_slo_minutes: float
    join_locality: JoinLocality
    # A drill-down to full grain is a different workload from the dashboard that
    # sits on top of it: rarer, less concurrent, and allowed to be slower. Modelling
    # it separately is what makes a hybrid split arguable rather than a hedge.
    detail_drilldown: bool = False
    detail_queries_per_day: float = 0.0
    detail_peak_concurrency: int = 2
    detail_latency_slo_seconds: float = 120.0


class Governance(BaseModel):
    residency: list[str]
    pii: bool = False
    classification: str = "internal"


class DataObject(BaseModel):
    id: str
    name: str
    domain: str
    source: str
    direction: Direction = "outbound"
    size_gb: float
    daily_delta_gb: float
    delta_capability: DeltaCapability
    bdc_data_product: bool = False
    semantics: Semantics = "medium"
    consumer: ConsumerProfile
    governance: Governance


class SourceSystem(BaseModel):
    id: str
    name: str
    kind: str
    release: str | None = None
    extraction: list[str]
    residency: list[str]


class TargetPlatform(BaseModel):
    platform: str
    region: str
    regions_covered: list[str]


class SapLanding(BaseModel):
    bdc_tenant_region: str
    datasphere_space: str
    replication_min_schedule_minutes: float
    replication_default_schedule_minutes: float
    share_refresh_minutes: float


class Landscape(BaseModel):
    target: TargetPlatform
    sap: SapLanding
    systems: list[SourceSystem]

    def system(self, system_id: str) -> SourceSystem:
        for s in self.systems:
            if s.id == system_id:
                return s
        raise KeyError(f"unknown source system: {system_id}")


class ResidencyPolicy(BaseModel):
    block_copy_outside_allowed_regions: bool = True
    block_federation_of_pii_outside_allowed_regions: bool = True


class DeltaPolicy(BaseModel):
    full_reload_ceiling_gb: float = 50.0
    flag_slt_on_hot_tables: bool = True


class SharePolicy(BaseModel):
    requires_bdc_data_product: bool = True
    outbound_only: bool = True


class SemanticsPolicy(BaseModel):
    prefer_share_when_high: bool = True
    max_premium_ratio: float = 1.35


class HybridPolicy(BaseModel):
    max_detail_queries_per_day: float = 25.0


class Policy(BaseModel):
    residency: ResidencyPolicy = Field(default_factory=ResidencyPolicy)
    delta: DeltaPolicy = Field(default_factory=DeltaPolicy)
    share: SharePolicy = Field(default_factory=SharePolicy)
    semantics: SemanticsPolicy = Field(default_factory=SemanticsPolicy)
    hybrid: HybridPolicy = Field(default_factory=HybridPolicy)


class ReplicateCosts(BaseModel):
    initial_load_eur_per_gb: float
    amortise_initial_load_months: float
    delta_move_eur_per_gb: float
    target_storage_eur_per_gb_month: float
    outbound_block_gb_per_month: float
    outbound_block_eur_per_month: float
    ops_eur_per_object_month: float
    consumer_compute_eur_per_gb_scanned: float


class FederateCosts(BaseModel):
    source_compute_eur_per_gb_scanned: float
    egress_eur_per_gb: float
    ops_eur_per_object_month: float


class ShareCosts(BaseModel):
    consumer_compute_eur_per_gb_scanned: float
    ops_eur_per_object_month: float


class LatencyModel(BaseModel):
    federate_base_seconds: float
    federate_seconds_per_gb_scanned: float
    federate_concurrency_penalty_per_query: float
    replicate_base_seconds: float
    replicate_seconds_per_gb_scanned: float
    share_base_seconds: float
    share_seconds_per_gb_scanned: float


class CostModel(BaseModel):
    currency: str
    replicate: ReplicateCosts
    federate: FederateCosts
    share: ShareCosts
    latency: LatencyModel


class Catalog(BaseModel):
    """Everything loaded, in one object, so a caller passes one argument around."""

    landscape: Landscape
    policy: Policy
    costs: CostModel
    objects: list[DataObject]


def _read(path: Path) -> object:
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def load_catalog(config_dir: Path | None = None) -> Catalog:
    """Load and validate the whole configuration set.

    Validation is deliberately strict: a typo in a delta capability or a missing
    consumer profile should fail here, loudly, and not silently become a default
    that changes an architecture decision.
    """
    cfg = Path(config_dir) if config_dir else CONFIG_DIR
    landscape = Landscape.model_validate(_read(cfg / "landscape.yaml"))
    policy = Policy.model_validate(_read(cfg / "policy.yaml"))
    costs = CostModel.model_validate(_read(cfg / "cost_model.yaml"))
    objects = [DataObject.model_validate(o) for o in _read(cfg / "objects.yaml")]

    known = {s.id for s in landscape.systems}
    for obj in objects:
        if obj.source not in known:
            raise ValueError(f"{obj.id}: unknown source system {obj.source!r}")

    return Catalog(landscape=landscape, policy=policy, costs=costs, objects=objects)
