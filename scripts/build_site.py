"""Assemble the published site: the one page, the register, the simulation, the docs.

There is no infrastructure to deploy here — the whole thing runs on a laptop by
design (ADR-0001) — so what ships is the artifact set. That only helps anyone if it
is *readable*: GitHub Pages serves a raw ``.md`` as plain text, and a decision
register nobody can read is back to being a file in a repo.

So the markdown is rendered, the mermaid diagram in the reference architecture is
rendered with it, and the dbt docs site is dropped in beside it. Run by the
``publish`` job in CI; runnable locally with ``python scripts/build_site.py site``.

Needs ``markdown``, which is *not* a project dependency — it is installed in the one
CI job that needs it, so ADR-0001's "no required external dependency on the default
path" survives.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

#: What gets rendered, in the order it appears on the landing page.
PAGES = [
    ("docs/reference-architecture.md", "reference-architecture.html", "The one page"),
    ("reports/decisions.md", "decisions.html", "The decision register"),
    ("reports/simulation.md", "simulation.html", "The simulation — three modes, measured"),
    ("docs/c-bdcda-study-map.md", "study-map.html", "C_BDCDA exam domains → artifacts"),
    ("docs/product/FS-0005-transformation-layer.md", "fs-0005.html",
     "FS-0005 — the transformation layer"),
    ("docs/design/decisions/0007-dbt-as-the-consumption-layer.md", "adr-0007.html",
     "ADR-0007 — dbt as the consumption layer"),
]

_CSS = """
:root { color-scheme: light dark; }
body { font: 16px/1.65 system-ui, -apple-system, sans-serif; max-width: 52rem;
       margin: 3rem auto; padding: 0 1.5rem; }
a { color: #1f4e79; } h1 { font-size: 1.5rem; } h2 { font-size: 1.2rem; margin-top: 2rem; }
table { border-collapse: collapse; width: 100%; overflow-x: auto; display: block; }
th, td { border: 1px solid #d1d5db; padding: .35rem .6rem; text-align: left; font-size: .92rem; }
code { background: #f3f4f6; padding: .1rem .3rem; border-radius: 3px; }
pre { background: #f3f4f6; padding: .8rem; overflow-x: auto; border-radius: 4px; }
pre code { background: none; }
.nav { margin-bottom: 2rem; font-size: .9rem; }
.note { border-left: 3px solid #b45309; padding-left: .9rem; color: #6b5b3c; font-size: .92rem; }
@media (prefers-color-scheme: dark) {
  body { background: #0f1115; color: #e5e7eb; }
  a { color: #7aa7d9; } th, td { border-color: #374151; }
  code, pre { background: #1a1d24; } .note { color: #cbb994; }
}
"""

_SHELL = """<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>{css}</style>
</head><body>
<p class="nav"><a href="index.html">&larr; sap-bdc-snowflake-blueprint</a></p>
{body}
<script type="module">
  import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs";
  // The reference architecture's diagram arrives as a fenced `mermaid` block; the
  // markdown renderer leaves it as <pre><code class="language-mermaid">.
  for (const el of document.querySelectorAll("code.language-mermaid")) {{
    const pre = el.parentElement;
    const div = document.createElement("div");
    div.className = "mermaid";
    div.textContent = el.textContent;
    pre.replaceWith(div);
  }}
  mermaid.initialize({{ startOnLoad: true,
    theme: window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "default" }});
</script>
</body></html>
"""

_INDEX = """<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>sap-bdc-snowflake-blueprint</title>
<style>{css}</style>
</head><body>
<h1>sap-bdc-snowflake-blueprint</h1>
<p>SAP sources &rarr; Business Data Cloud / Datasphere &rarr; Snowflake, with the
federate-vs-replicate-vs-share decision made explicit, priced and runnable.</p>
<p class="note"><strong>Honesty statement.</strong> No SAP system and no Snowflake
account are involved anywhere in this: DuckDB stands in for both sides of the seam.
The cost figures are illustrative placeholders shaped like list pricing, not quotes,
and the 24-object catalog is invented. The durable artifact is the decision
procedure, not the euro figures — see the repository README.</p>
<ul>
{items}
<li><a href="dbt/index.html">The transformation layer (dbt docs)</a> — sources
generated from the register, so a mode is a binding rather than a comment</li>
<li><a href="reports/crossover.png">Chart: where replication overtakes federation</a></li>
<li><a href="reports/mode-mix.png">Chart: what the decision is worth, by domain</a></li>
</ul>
<p><a href="https://github.com/fps4/sap-bdc-snowflake-blueprint">Source on GitHub</a></p>
</body></html>
"""


def build(out: Path) -> Path:
    import markdown

    out.mkdir(parents=True, exist_ok=True)
    md = markdown.Markdown(extensions=["extra", "tables", "fenced_code", "toc", "sane_lists"])

    items = []
    for source, target, label in PAGES:
        path = ROOT / source
        if not path.exists():
            # A missing report means an upstream job did not run. Say so on the page
            # rather than shipping a link that 404s.
            items.append(f'<li>{label} — <em>not generated in this build</em></li>')
            continue
        md.reset()
        (out / target).write_text(
            _SHELL.format(title=label, css=_CSS, body=md.convert(path.read_text(encoding="utf-8"))),
            encoding="utf-8",
        )
        items.append(f'<li><a href="{target}">{label}</a></li>')

    (out / "index.html").write_text(
        _INDEX.format(css=_CSS, items="\n".join(items)), encoding="utf-8"
    )

    reports = ROOT / "reports"
    if reports.exists():
        shutil.copytree(reports, out / "reports", dirs_exist_ok=True)
    return out


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "site"
    print(f"wrote {build(target)}")
