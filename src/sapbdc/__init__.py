"""sap-bdc-snowflake-blueprint — a reference architecture with a runnable decision.

The one-page architecture lives in ``docs/reference-architecture.md``. This
package is the part that keeps it honest: a typed catalog of a mixed SAP estate,
an ordered rule set that assigns each object an integration mode, a cost and
latency model that says where federation stops being cheaper than replication,
and a local simulation that executes all three modes so the claim is measured
rather than asserted.
"""

from .catalog import Catalog, DataObject, Mode, load_catalog
from .rules import Decision, decide_all, decide_object

__all__ = [
    "Catalog",
    "DataObject",
    "Decision",
    "Mode",
    "decide_all",
    "decide_object",
    "load_catalog",
]

__version__ = "0.1.0"
