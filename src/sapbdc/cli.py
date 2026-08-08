"""Command line: ``decide``, ``explain``, ``simulate``."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .catalog import Mode, load_catalog
from .report import console_summary, write_all
from .rules import decide_all


def cmd_decide(args: argparse.Namespace) -> int:
    cat = load_catalog(args.config)
    decisions = decide_all(cat)
    print(console_summary(decisions, cat))
    if not args.no_report:
        written = write_all(decisions, cat, args.reports)
        print("\n" + "\n".join(f"wrote {p}" for p in written))
    return 0


def cmd_explain(args: argparse.Namespace) -> int:
    cat = load_catalog(args.config)
    decisions = {d.object_id: d for d in decide_all(cat)}
    d = decisions.get(args.object_id)
    if d is None:
        print(f"unknown object {args.object_id!r}; known: {', '.join(decisions)}", file=sys.stderr)
        return 2

    print(f"{d.object_id} — {d.object_name}")
    print(f"  decision   {d.mode.value}  (rule {d.rule_id}, {d.direction})")
    print(f"  because    {d.primary_reason}")
    if d.eliminated:
        print("  ruled out")
        for m, why in d.eliminated.items():
            print(f"    - {m.value}: {why}")
    if d.economics:
        print("  economics")
        for m in (Mode.SHARE, Mode.REPLICATE, Mode.FEDERATE):
            e = d.economics[m]
            print(
                f"    {m.value:<10} €{e.monthly_eur:>10,.0f}/mo  "
                f"(fixed €{e.fixed_eur_month:,.0f} + €{e.variable_eur_per_query:.4f}/query)  "
                f"p95 {e.p95_latency_seconds:,.1f}s  freshness {e.freshness_minutes:,.0f} min"
            )
    if d.crossover_queries_per_day is not None:
        print(f"  crossover  {d.crossover_queries_per_day:,.0f} queries/day")
    for n in d.notes:
        print(f"  note       {n}")
    if d.flags:
        print(f"  flags      {', '.join(d.flags)}")
    return 0


def cmd_simulate(args: argparse.Namespace) -> int:
    from .sim.run import main as sim_main

    sim_main()
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="sapbdc", description=__doc__)
    p.add_argument("--config", type=Path, default=None, help="config directory")
    sub = p.add_subparsers(dest="command", required=True)

    d = sub.add_parser("decide", help="assign an integration mode to every object")
    d.add_argument("--reports", type=Path, default=None, help="output directory")
    d.add_argument("--no-report", action="store_true", help="console only")
    d.set_defaults(func=cmd_decide)

    e = sub.add_parser("explain", help="show the full reasoning for one object")
    e.add_argument("object_id")
    e.set_defaults(func=cmd_explain)

    s = sub.add_parser("simulate", help="run all three modes on synthetic local data")
    s.set_defaults(func=cmd_simulate)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
