"""
This script merges ../authors/authors.ttl, ../works/works.ttl and ../relations/relations.ttl 
without duplications.

The output is serialized as Turtle and written to 'all.ttl'.

"""

import argparse
from collections import defaultdict
from pathlib import Path
from rdflib import Graph, Namespace, RDF, RDFS, OWL, URIRef

# Namespaces
sappho   = Namespace("https://sappho-digital.com/")
ecrm     = Namespace("http://erlangen-crm.org/current/")
ecrm_uri = URIRef("http://erlangen-crm.org/current/")
crm      = Namespace("http://www.cidoc-crm.org/cidoc-crm/")
lrmoo    = Namespace("http://iflastandards.info/ns/lrm/lrmoo/")
lrmoo_uri = URIRef("https://cidoc-crm.org/extensions/lrmoo/owl/1.0/LRMoo_v1.0.owl")
frbroo   = Namespace("http://iflastandards.info/ns/fr/frbr/frbroo/")
efrbroo  = Namespace("http://erlangen-crm.org/efrbroo/")
intro    = Namespace("https://w3id.org/lso/intro/currentbeta#")
intro_uri = URIRef("https://w3id.org/lso/intro/currentbeta#")
prov     = Namespace("http://www.w3.org/ns/prov#")

def load_graphs(authors_path: Path, works_path: Path, relations_path: Path) -> tuple[Graph, Graph, Graph]:
    """Load authors, works, and relations graphs from Turtle files."""
    g_authors = Graph().parse(str(authors_path), format="turtle")
    g_works = Graph().parse(str(works_path), format="turtle")
    g_relations = Graph().parse(str(relations_path), format="turtle")
    return g_authors, g_works, g_relations

def merge_graphs(graphs: list[Graph]) -> Graph:
    """Union all graphs into a new Graph (rdflib '+' semantics)."""
    g_all = Graph()
    for g in graphs:
        g_all += g
    return g_all

def cleanup_duplicate_labels(g_all: Graph) -> Graph:
    """
    Remove duplicate rdfs:label per subject.
    Keep exactly one label per subject: prefer a label with a language tag; 
    if multiple such labels exist, keep the first encountered; otherwise keep the first label.
    """
    label_map: dict[URIRef, list] = defaultdict(list)
    for s, p, o in g_all.triples((None, RDFS.label, None)):
        label_map[s].append(o)

    multi_label_subjects = {s for s, labels in label_map.items() if len(labels) > 1}

    cleaned_graph = Graph()
    for s, p, o in g_all:
        if p == RDFS.label and s in multi_label_subjects:
            labels = label_map[s]
            with_lang = [lbl for lbl in labels if getattr(lbl, "language", None)]
            keep = with_lang[0] if with_lang else labels[0]
            if o == keep:
                cleaned_graph.add((s, p, o))
        else:
            cleaned_graph.add((s, p, o))
    return cleaned_graph

def cleanup_ontology(g: Graph) -> Graph:
    """
    Remove any existing owl:Ontology nodes, then add the merged ontology node and imports.
    """
    for s, p, o in list(g.triples((None, RDF.type, OWL.Ontology))):
        g.remove((s, None, None))

    ontology_uri = URIRef("https://sappho-digital.com/ontology/all")
    g.add((ontology_uri, RDF.type, OWL.Ontology))
    g.add((ontology_uri, OWL.imports, ecrm_uri))
    g.add((ontology_uri, OWL.imports, lrmoo_uri))
    g.add((ontology_uri, OWL.imports, intro_uri))
    return g

def bind_namespaces(g: Graph) -> None:
    """Bind all project namespaces."""
    g.bind("sappho", sappho)
    g.bind("ecrm", ecrm)
    g.bind("crm", crm)
    g.bind("lrmoo", lrmoo)
    g.bind("frbroo", frbroo)
    g.bind("efrbroo", efrbroo)
    g.bind("intro", intro)
    g.bind("prov", prov)

def parse_args(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Merge authors.ttl, works.ttl, relations.ttl into one graph (de-duplicated labels)"
    )
    p.add_argument("--authors",   type=Path, help="Path to authors.ttl (e.g. examples/outputs/authors.ttl)")
    p.add_argument("--works",     type=Path, help="Path to works.ttl (e.g. examples/outputs/works.ttl)")
    p.add_argument("--relations", type=Path, help="Path to relations.ttl (e.g. examples/outputs/relations.ttl)")
    p.add_argument("--output",    type=Path, help="Output TTL (e.g. examples/outputs/all.ttl)")
    p.add_argument("--log-level", default="INFO", help="Logging level (default: INFO)")
    return p.parse_args(argv)

def main(argv=None) -> int:
    args = parse_args(argv)

    import logging
    logging.basicConfig(level=getattr(logging, args.log_level.upper(), logging.INFO),
                        format="%(levelname)s:%(name)s:%(message)s")

    if args.authors is None:
        cand = Path("examples/outputs/authors.ttl")
        if cand.exists(): args.authors = cand
        else: raise SystemExit("--authors is required (no examples/outputs/authors.ttl found)")

    if args.works is None:
        cand = Path("examples/outputs/works.ttl")
        if cand.exists(): args.works = cand
        else: raise SystemExit("--works is required (no examples/outputs/works.ttl found)")

    if args.relations is None:
        cand = Path("examples/outputs/relations.ttl")
        if cand.exists(): args.relations = cand
        else: raise SystemExit("--relations is required (no examples/outputs/relations.ttl found)")

    if args.output is None:
        outdir = Path("examples/outputs")
        args.output = (outdir / "all.ttl") if outdir.exists() else Path("all.ttl")

    args.output.parent.mkdir(parents=True, exist_ok=True)

    for name, p in (("authors", args.authors), ("works", args.works), ("relations", args.relations)):
        if not p.exists():
            raise SystemExit(f"--{name} not found: {p}")

    # Merge
    g_authors, g_works, g_relations = load_graphs(args.authors, args.works, args.relations)
    g_all = merge_graphs([g_authors, g_works, g_relations])
    cleaned = cleanup_duplicate_labels(g_all)
    cleaned = cleanup_ontology(cleaned)
    bind_namespaces(cleaned)

    cleaned.serialize(destination=str(args.output), format="turtle")
    print(f"✅ merged TTL written to {args.output}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())