# src/wiki2crm/cli.py
import sys
import argparse
from importlib import import_module
from . import __version__

MODMAP = {
    "authors":   "wiki2crm.authors",
    "works":     "wiki2crm.works",
    "relations": "wiki2crm.relations",
    "merge":     "wiki2crm.merge",
    "map-align": "wiki2crm.map_and_align",
}

HELP_BY_CMD = {
    "authors":   "Build authors.ttl from a CSV of QIDs",
    "works":     "Build works.ttl from a CSV of QIDs",
    "relations": "Build relations.ttl from a CSV of QIDs",
    "merge":     "Merge authors/works/relations TTL into one",
    "map-align": "Add extra IDs + ontology alignments",
}

EXAMPLES = """Examples:
  wiki2crm authors --input /path/authors.csv --output /path/authors.ttl
  wiki2crm merge --authors a.ttl --works w.ttl --relations r.ttl --output all.ttl
  wiki2crm map-align --input all.ttl --output all_mapped-and-aligned.ttl
"""

def main(argv=None):
    argv = sys.argv[1:] if argv is None else list(argv)

    parser = argparse.ArgumentParser(
        prog="wiki2crm",
        description="Wikidata → CIDOC CRM",
        epilog=EXAMPLES,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--hello", action="store_true", help="Print a short greeting and exit")

    sub = parser.add_subparsers(dest="cmd")
    for cmd, help_text in HELP_BY_CMD.items():
        sub.add_parser(cmd, help=help_text)

    args, rest = parser.parse_known_args(argv)

    if args.hello:
        print("👋 hello from wiki2crm")
        return 0

    if not args.cmd:
        parser.print_help()
        return 0

    modname = MODMAP.get(args.cmd)
    if not modname:
        parser.error(f"Unknown command: {args.cmd}")

    try:
        mod = import_module(modname)
    except Exception as e:
        parser.error(f"Could not import subcommand module '{modname}': {e}")

    if not hasattr(mod, "main"):
        parser.error(f"Subcommand module '{modname}' has no function main(argv=None)")

    return mod.main(argv=rest)

if __name__ == "__main__":
    raise SystemExit(main())
