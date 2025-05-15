"""
This script retrieves intertextual data from Wikidata based on a list of QIDs (from a CSV file)
and transforms it into RDF triples according to INTRO, LRMoo/FRBRoo and CIDOC CRM (OWL/eCRM).

The output is serialized as Turtle and written to 'relations.ttl'.

"""

import csv
import requests
from itertools import combinations
from functools import lru_cache
from rdflib import Graph, Namespace, URIRef, Literal
from rdflib.namespace import RDF, RDFS, OWL
from tqdm import tqdm
from typing import Union, Iterable, Tuple

# Namespaces
WD_ENTITY = "https://www.wikidata.org/entity/"
sappho   = Namespace("https://sappho-digital.com/")
ecrm     = Namespace("http://erlangen-crm.org/current/")
ecrm_uri = URIRef("http://erlangen-crm.org/current/")
crm = Namespace("http://www.cidoc-crm.org/cidoc-crm/")
crm_uri = URIRef("http://www.cidoc-crm.org/cidoc-crm/")
lrmoo    = Namespace("http://iflastandards.info/ns/lrm/lrmoo/")
lrmoo_uri = URIRef("http://iflastandards.info/ns/lrm/lrmoo/")
frbroo = Namespace("http://iflastandards.info/ns/fr/frbr/frbroo/")
frbroo_uri = URIRef("http://iflastandards.info/ns/fr/frbr/frbroo/")
intro    = Namespace("https://w3id.org/lso/intro/currentbeta#")
intro_uri = URIRef("https://w3id.org/lso/intro/currentbeta#")
prov     = Namespace("http://www.w3.org/ns/prov#")
prov_uri = URIRef("http://www.w3.org/ns/prov#")

# SPARQL Setup
SPARQL_URL = "https://query.wikidata.org/sparql"
HEADERS = {
    "Accept": "application/sparql-results+json",
    "User-Agent": "SapphoIntertextualRelationsBot/1.0 (laura.untner@fu-berlin.de)"
}
session = requests.Session()
session.headers.update(HEADERS)

@lru_cache(None)
def get_label(qid: str, lang: str = "en") -> str:
    for lg in (lang, "de"):
        q = f"""
          SELECT ?l WHERE {{
            wd:{qid} rdfs:label ?l .
            FILTER(LANG(?l)="{lg}")
          }} LIMIT 1
        """
        r = session.get(SPARQL_URL, params={"query": q}, timeout=120)
        r.raise_for_status()
        b = r.json()["results"]["bindings"]
        if b:
            return b[0]["l"]["value"]
    return qid

def run_sparql(query: str) -> dict:
    r = session.get(SPARQL_URL, params={"query": query}, timeout=120)
    r.raise_for_status()
    return r.json()

# Load QIDS
with open("work-qids.csv", newline="", encoding="utf-8") as f:
    reader = csv.reader(f)
    qids = [row[0] for row in reader if row and row[0].startswith("Q")]

# Graph & Prefixes
g = Graph()
for prefix, ns in [
    ("sappho", sappho),
    ("ecrm", ecrm),
    ("crm", crm),
    ("frbroo", frbroo),
    ("lrmoo", lrmoo),
    ("intro", intro),
    ("prov", prov),
]:
    g.bind(prefix, ns)
    g.bind("rdfs", RDFS)
    g.bind("owl", OWL)

# Ontology

ontology_uri = URIRef("https://sappho-digital.com/ontology/relations")

g.add((ontology_uri, RDF.type, OWL.Ontology))

g.add((ontology_uri, OWL.imports, crm_uri))
g.add((ontology_uri, OWL.imports, ecrm_uri))
g.add((ontology_uri, OWL.imports, frbroo_uri))
g.add((ontology_uri, OWL.imports, lrmoo_uri))
g.add((ontology_uri, OWL.imports, intro_uri))
g.add((ontology_uri, OWL.imports, prov_uri))

# ID-Type
ID_TYPE = URIRef(sappho + "id_type/wikidata")
g.add((ID_TYPE, RDF.type, ecrm.E55_Type))
g.add((ID_TYPE, RDFS.label, Literal("Wikidata ID", lang="en")))
g.add((ID_TYPE, OWL.sameAs, URIRef(WD_ENTITY + "Q43649390")))

# Wikidata IDs
def add_identifier(entity: URIRef, qid: str):
    uri = URIRef(f"{sappho}identifier/{qid}")
    pure = qid.split("_")[-1]
    g.add((uri, RDF.type, ecrm.E42_Identifier))
    g.add((uri, RDFS.label, Literal(pure, lang="en")))
    g.add((uri, ecrm.P2_has_type, ID_TYPE))
    g.add((ID_TYPE, ecrm.P2i_is_type_of, uri))
    g.add((uri, prov.wasDerivedFrom, URIRef(f"{WD_ENTITY}{pure}")))
    g.add((entity, ecrm.P1_is_identified_by, uri))
    g.add((uri, ecrm.P1i_identifies, entity))

# Expressions
def ensure_expression(qid: str, label: str = None) -> URIRef:
    uri = URIRef(f"{sappho}expression/{qid}")
    if (uri, RDF.type, lrmoo.F2_Expression) in g:
        return uri
    g.add((uri, RDF.type, lrmoo.F2_Expression))
    g.add((uri, RDFS.label, Literal(f"Expression of {label or qid}", lang="en")))
    g.add((uri, OWL.sameAs, URIRef(WD_ENTITY + qid)))
    return uri

# Features
def ensure_feature(
    qid: str,
    cls: URIRef,
    label: str,
    path: str = "feature"
) -> URIRef:
     uri = URIRef(f"{sappho}{path}/{qid}")
     if (uri, None, None) not in g:
         g.add((uri, RDF.type, cls))
         g.add((uri, RDFS.label, Literal(label, lang="en")))
         g.add((uri, OWL.sameAs, URIRef(WD_ENTITY + qid)))
         add_identifier(uri, qid)
     return uri

# Interpretations
def add_interpretation(
    target: URIRef,
    label: str,
    derived_from: Union[URIRef, Iterable[URIRef]]
) -> Tuple[URIRef, URIRef]:

    tid      = target.split("/")[-1]
    feat_uri = URIRef(f"{sappho}feature/interpretation/{tid}")
    if (feat_uri, None, None) not in g:
        g.add((feat_uri, RDF.type, intro.INT_Interpretation))
        g.add((feat_uri, RDFS.label, Literal(label, lang="en")))

    act_uri  = URIRef(f"{sappho}actualization/interpretation/{tid}")
    if (act_uri, None, None) not in g:
        g.add((act_uri, RDF.type, intro.INT2_ActualizationOfFeature))
        g.add((act_uri, RDFS.label, Literal(label, lang="en")))

        sources = [derived_from] if isinstance(derived_from, URIRef) else list(derived_from)
        for src in sources:
            qid = src.split("/")[-1]
            g.add((act_uri, prov.wasDerivedFrom, URIRef(WD_ENTITY + qid)))

        g.add((feat_uri, intro.R17i_featureIsActualizedIn, act_uri))
        g.add((act_uri, intro.R17_actualizesFeature, feat_uri))

    g.add((act_uri, intro.R21_identifies, target))
    g.add((target, intro.R21i_isIdentifiedBy, act_uri))

    return feat_uri, act_uri

# Actualizations
def add_actualization(feature: URIRef, expression: URIRef, label: str, relation: URIRef):
    parts = str(feature).rstrip("/").split("/")
    parts = [p for p in parts if p != "feature"]
    typ = parts[-2]
    qid = parts[-1]
    fid = f"{typ}/{qid}"
    eid = expression.split("/")[-1]
    act = URIRef(f"{sappho}actualization/{fid}_{eid}")
    if any(g.triples((act, None, None))):
        return act
    g.add((act, RDF.type, intro.INT2_ActualizationOfFeature))
    g.add((act, RDFS.label, Literal(label, lang="en")))
    g.add((feature, intro.R17i_featureIsActualizedIn, act))
    g.add((act, intro.R17_actualizesFeature, feature))
    g.add((act, intro.R18i_actualizationFoundOn, expression))
    g.add((expression, intro.R18_showsActualization, act))
    g.add((act, intro.R24i_isRelatedEntity, relation))
    g.add((relation, intro.R24_hasRelatedEntity, act))
    feat_intp, act_intp = add_interpretation(
        act,
        f"Interpretation of {label}",
        URIRef(WD_ENTITY + eid)
    )
    return act

# Interrelations
def get_or_create_int31_relation(expr1: URIRef, expr2: URIRef) -> URIRef:
    if expr1 == expr2:
        return None
    w1, w2 = expr1.split("/")[-1], expr2.split("/")[-1]

    if w1 < w2:
        rel_uri = URIRef(f"{sappho}relation/{w1}_{w2}")
    else:
        rel_uri = URIRef(f"{sappho}relation/{w2}_{w1}")

    if (rel_uri, RDF.type, intro.INT31_IntertextualRelation) not in g:
        g.add((rel_uri, RDF.type, intro.INT31_IntertextualRelation))
        g.add((rel_uri, RDFS.label,
               Literal(f"Intertextual relation between {get_label(w1)} and {get_label(w2)}", lang="en")))

        feat_intp, act_intp = add_interpretation(
            rel_uri,
            f"Interpretation of intertextual relation between {get_label(w1)} and {get_label(w2)}",
            [expr1, expr2]
        )
        
    return rel_uri

# Other Relations
def process_int31(qids):
    
    vals = " ".join(f"wd:{q}" for q in qids)

    sparql_fwd = f"""
PREFIX wdt: <http://www.wikidata.org/prop/direct/>
SELECT DISTINCT ?w1 ?w2 ?p WHERE {{
  VALUES ?w1 {{ {vals} }}
  VALUES ?w2 {{ {vals} }}
  ?w1 ?p ?w2 .
  FILTER(?p IN (wdt:P4969,wdt:P2512,wdt:P921))
}}
"""

    sparql_bwd = f"""
PREFIX wdt: <http://www.wikidata.org/prop/direct/>
SELECT DISTINCT ?w1 ?w2 ?p WHERE {{
  VALUES ?w1 {{ {vals} }}
  VALUES ?w2 {{ {vals} }}
  ?w2 ?p ?w1 .
  FILTER(?p IN (wdt:P144,wdt:P5059,wdt:P941))
  BIND(?w1 AS ?tmp) .
  BIND(?w2 AS ?w1) .
  BIND(?tmp AS ?w2) .
}}
"""

    tripel = []
    for row in run_sparql(sparql_fwd)["results"]["bindings"]:
        w1 = row["w1"]["value"].rsplit("/",1)[-1]
        w2 = row["w2"]["value"].rsplit("/",1)[-1]
        p  = row["p"]["value"].rsplit("/",1)[-1]
        if w1 == w2:
            continue
        tripel.append((w1, w2, p))
    for row in run_sparql(sparql_bwd)["results"]["bindings"]:
        w1 = row["w1"]["value"].rsplit("/",1)[-1]
        w2 = row["w2"]["value"].rsplit("/",1)[-1]
        p  = row["p"]["value"].rsplit("/",1)[-1]
        if w1 == w2:
            continue
        tripel.append((w1, w2, p))

    seen = set()
    for w1, w2, p in tripel:
        key = (w1, w2, p)
        if key in seen:
            continue
        seen.add(key)

        uri = f"{w1}_{w2}" if w1 < w2 else f"{w2}_{w1}"
        rel = URIRef(f"{sappho}relation/{uri}")

        if (rel, RDF.type, intro.INT31_IntertextualRelation) not in g:
            g.add((rel, RDF.type, intro.INT31_IntertextualRelation))
            g.add((rel, RDFS.label,
                   Literal(f"Intertextual relation ({p}) between {get_label(w1)} and {get_label(w2)}", lang="en")))

# Plots
def process_plots(qids, props, target_q, cls, prefix, use_app=False):
    vals = " ".join(f"wd:{q}" for q in qids)

    query = f"""
PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX wd:   <http://www.wikidata.org/entity/>
SELECT ?wrk ?tgt WHERE {{
  VALUES ?wrk {{ {vals} }}
  {{
    SELECT ?tgt WHERE {{
      VALUES ?wrk {{ {vals} }}
      ?wrk ?p ?tgt .
      FILTER(?p IN ({', '.join('wdt:'+p for p in props)}))
      ?tgt wdt:P31/wdt:P279* wd:{target_q}
    }}
    GROUP BY ?tgt
    HAVING(COUNT(DISTINCT ?wrk) > 1)
  }}
  ?wrk ?p ?tgt .
  FILTER(?p IN ({', '.join('wdt:'+p for p in props)}))
  ?tgt wdt:P31/wdt:P279* wd:{target_q}
}}
"""
    res = run_sparql(query)["results"]["bindings"]

    mp = {}
    for b in res:
        w   = b["wrk"]["value"].rsplit("/",1)[-1]
        tgt = b["tgt"]["value"].rsplit("/",1)[-1]
        mp.setdefault(tgt, []).append(w)

    for tgt, works in mp.items():
        raw_lbl = get_label(tgt)
        feat_lbl = f"{raw_lbl} (plot)"
        feat = ensure_feature(tgt, intro.INT_Plot, feat_lbl, path="feature/plot")

        for w1, w2 in combinations(works, 2):
            expr1 = ensure_expression(w1, get_label(w1))
            expr2 = ensure_expression(w2, get_label(w2))
            rel   = get_or_create_int31_relation(expr1, expr2)
            if rel is None:
                continue

            if (feat, intro.R22_providesSimilarityForRelation, rel) not in g:
                g.add((feat, intro.R22_providesSimilarityForRelation, rel))
                g.add((rel, intro.R22i_relationIsBasedOnSimilarity, feat))

            add_actualization(feat, expr1, f"{raw_lbl} in {get_label(w1)}", rel)
            add_actualization(feat, expr2, f"{raw_lbl} in {get_label(w2)}", rel)

# Topics
def process_topics(qids):
    vals = " ".join(f"wd:{q}" for q in qids)

    query = f"""
PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX wd:   <http://www.wikidata.org/entity/>
SELECT ?wrk ?tgt WHERE {{
  VALUES ?wrk {{ {vals} }}
  {{
    SELECT ?tgt WHERE {{
      VALUES ?wrk {{ {vals} }}
      ?wrk ?p ?tgt .
      FILTER(?p IN (wdt:P921, wdt:P180, wdt:P527))
      ?tgt wdt:P31/wdt:P279* wd:Q26256810 .
    }}
    GROUP BY ?tgt
    HAVING(COUNT(DISTINCT ?wrk) > 1)
  }}
  ?wrk ?p ?tgt .
  FILTER(?p IN (wdt:P921, wdt:P180, wdt:P527))
}}
"""
    res = run_sparql(query)["results"]["bindings"]

    mp = {}
    for b in res:
        w = b["wrk"]["value"].rsplit("/",1)[-1]
        t = b["tgt"]["value"].rsplit("/",1)[-1]
        mp.setdefault(t, []).append(w)

    for tgt, works in mp.items():
            raw_lbl = get_label(tgt)
            feat_lbl = f"{raw_lbl} (topic)"
            feat = ensure_feature(tgt, intro.INT_Topic, feat_lbl, path="feature/topic")

            for w1, w2 in combinations(works, 2):
                expr1 = ensure_expression(w1, get_label(w1))
                expr2 = ensure_expression(w2, get_label(w2))

                rel = get_or_create_int31_relation(expr1, expr2)
                if rel is None:
                    continue

                if (feat, intro.R22_providesSimilarityForRelation, rel) not in g:
                    g.add((feat, intro.R22_providesSimilarityForRelation, rel))
                    g.add((rel, intro.R22i_relationIsBasedOnSimilarity, feat))

                add_actualization(feat, expr1, f"{raw_lbl} in {get_label(w1)}", rel)
                add_actualization(feat, expr2, f"{raw_lbl} in {get_label(w2)}", rel)

# Motifs
def process_motifs(qids):
    vals = " ".join(f"wd:{q}" for q in qids)
    query = f"""
PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX wd:   <http://www.wikidata.org/entity/>
SELECT ?wrk ?motif WHERE {{
  VALUES ?wrk {{ {vals} }}
  VALUES ?class {{ wd:Q1229071 wd:Q68614425 wd:Q1697305 }}
  {{
    SELECT ?motif WHERE {{
      VALUES ?wrk {{ {vals} }}
      {{ ?wrk wdt:P6962 ?motif . }}
      UNION
      {{
        ?wrk wdt:P180|wdt:P527 ?x .
        ?x wdt:P31/wdt:P279* ?class ;
           owl:sameAs ?motif .
      }}
    }}
    GROUP BY ?motif
    HAVING(COUNT(DISTINCT ?wrk) > 1)
  }}
  {{ ?wrk wdt:P6962 ?motif . }}
  UNION
  {{
    ?wrk wdt:P180|wdt:P527 ?x .
    ?x wdt:P31/wdt:P279* ?class ;
       owl:sameAs ?motif .
  }}
}}
"""
    res = run_sparql(query)["results"]["bindings"]

    mp = {}
    for b in res:
        w = b["wrk"]["value"].rsplit("/",1)[-1]
        m = b["motif"]["value"].rsplit("/",1)[-1]
        mp.setdefault(m, []).append(w)

    for motif, works in mp.items():
            raw_lbl = get_label(motif)
            feat_lbl = f"{raw_lbl} (motif)"
            feat = ensure_feature(motif, intro.INT_Motif, feat_lbl, path="feature/motif")

            for w1, w2 in combinations(works, 2):
                expr1 = ensure_expression(w1, get_label(w1))
                expr2 = ensure_expression(w2, get_label(w2))

                rel = get_or_create_int31_relation(expr1, expr2)
                if rel is None:
                    continue

                if (feat, intro.R22_providesSimilarityForRelation, rel) not in g:
                    g.add((feat, intro.R22_providesSimilarityForRelation, rel))
                    g.add((rel, intro.R22i_relationIsBasedOnSimilarity, feat))

                add_actualization(feat, expr1, f"{raw_lbl} in {get_label(w1)}", rel)
                add_actualization(feat, expr2, f"{raw_lbl} in {get_label(w2)}", rel)

# Person References
def process_person(qids):
    vals = " ".join(f"wd:{q}" for q in qids)
    q = f"""
SELECT DISTINCT ?wrk ?pers WHERE {{
  VALUES ?wrk {{ {vals} }}
  ?wrk ?p ?pers .
  FILTER(?p IN (wdt:P180,wdt:P921,wdt:P527))
  ?pers wdt:P31/wdt:P279* wd:Q5
}}
"""
    mp = {}
    for row in run_sparql(q)["results"]["bindings"]:
        w = row["wrk"]["value"].split("/")[-1]
        p = row["pers"]["value"].split("/")[-1]
        mp.setdefault(p, set()).add(w)

    for p, works in mp.items():
        if len(works) < 2:
            continue

        name  = get_label(p)
        p_uri = URIRef(f"{sappho}person/{p}")

        g.add((p_uri, RDF.type, ecrm.E21_Person))
        g.add((p_uri, RDFS.label, Literal(name, lang="en")))
        g.add((p_uri, OWL.sameAs, URIRef(WD_ENTITY + p)))
        add_identifier(p_uri, p)  

        feat = URIRef(f"{sappho}feature/person_ref/{p}")
        if (feat, None, None) not in g:
            g.add((feat, RDF.type, intro.INT18_Reference))
            g.add((feat, RDFS.label,
                   Literal(f"Reference to {name} (person)", lang="en")))

        for w1, w2 in combinations(sorted(works), 2):
            expr1 = ensure_expression(w1, get_label(w1))
            expr2 = ensure_expression(w2, get_label(w2))

            rel = get_or_create_int31_relation(expr1, expr2)
            if rel is None:
                continue

            if (feat, intro.R22_providesSimilarityForRelation, rel) not in g:
                g.add((feat, intro.R22_providesSimilarityForRelation, rel))
                g.add((rel, intro.R22i_relationIsBasedOnSimilarity, feat))

            add_actualization(feat, expr1, f"{name} in {get_label(w1)}", rel)
            act1 = add_actualization(feat, expr1, f"Reference to {name} in {get_label(w1)}", rel)
            g.add((act1, ecrm.P67_refers_to, p_uri))
            g.add((p_uri,  ecrm.P67i_is_referred_to_by, act1))

            add_actualization(feat, expr2, f"{name} in {get_label(w2)}", rel)
            act2 = add_actualization(feat, expr2, f"Reference to {name} in {get_label(w2)}", rel)
            g.add((act2, ecrm.P67_refers_to, p_uri))
            g.add((p_uri,  ecrm.P67i_is_referred_to_by, act2))

# Place References
def process_place(qids):
    vals = " ".join(f"wd:{q}" for q in qids)
    q = f"""
SELECT DISTINCT ?wrk ?pers WHERE {{
  VALUES ?wrk {{ {vals} }}
  ?wrk ?p ?pers .
  FILTER(?p IN (wdt:P180, wdt:P921, wdt:P527))
  ?pers wdt:P31/wdt:P279* wd:Q2221906
}}
"""
    mp = {}
    for row in run_sparql(q)["results"]["bindings"]:
        w = row["wrk"]["value"].split("/")[-1]
        p = row["pers"]["value"].split("/")[-1]
        mp.setdefault(p, set()).add(w)

    for pl, works in mp.items():
        if len(works) < 2:
            continue

        name  = get_label(pl)
        p_uri = URIRef(f"{sappho}place/{pl}")
        g.add((p_uri, RDF.type, ecrm.E53_Place))
        g.add((p_uri, RDFS.label, Literal(name, lang="en")))
        g.add((p_uri, OWL.sameAs, URIRef(WD_ENTITY + pl)))
        add_identifier(p_uri, pl) 

        feat = URIRef(f"{sappho}feature/place_ref/{pl}")
        if (feat, None, None) not in g:
            g.add((feat, RDF.type, intro.INT18_Reference))
            g.add((feat, RDFS.label,
                   Literal(f"Reference to {name} (place)", lang="en")))

        for w1, w2 in combinations(sorted(works), 2):
            expr1 = ensure_expression(w1, get_label(w1))
            expr2 = ensure_expression(w2, get_label(w2))
            rel   = get_or_create_int31_relation(expr1, expr2)
            if rel is None:
                continue
            
            if (feat, intro.R22_providesSimilarityForRelation, rel) not in g:
                g.add((feat, intro.R22_providesSimilarityForRelation, rel))
                g.add((rel, intro.R22i_relationIsBasedOnSimilarity, feat))

            add_actualization(feat, expr1, f"{name} in {get_label(w1)}", rel)
            fid = feat.split("/")[-1]
            eid = expr1.split("/")[-1]
            act1 = URIRef(f"{sappho}actualization/place_ref/{fid}_{eid}")
            g.add((act1, ecrm.P67_refers_to, p_uri))
            g.add((p_uri,  ecrm.P67i_is_referred_to_by, act1))

            add_actualization(feat, expr2, f"{name} in {get_label(w2)}", rel)
            eid = expr2.split("/")[-1]
            act2 = URIRef(f"{sappho}actualization/place_ref/{fid}_{eid}")
            g.add((act2, ecrm.P67_refers_to, p_uri))
            g.add((p_uri,  ecrm.P67i_is_referred_to_by, act2))

# Work References
def process_work_references(qids):
    vals = " ".join(f"wd:{q}" for q in qids)

    sparql = f"""
PREFIX wdt: <http://www.wikidata.org/prop/direct/>
SELECT DISTINCT ?src ?tgt WHERE {{
  VALUES ?src {{ {vals} }}
  ?src ?p ?tgt .
  FILTER(?p IN (wdt:P361,wdt:P1299))
  FILTER(STRSTARTS(STR(?tgt),"http://www.wikidata.org/entity/Q"))
}}
"""
    binds = run_sparql(sparql)["results"]["bindings"]

    all_srcs = {
        row["src"]["value"].rsplit("/", 1)[-1]
        for row in binds
        if row["src"]["value"].rsplit("/", 1)[-1] in qids
    }

    ref_map: dict[str, set[str]] = {}
    for row in binds:
        src = row["src"]["value"].rsplit("/", 1)[-1]
        tgt = row["tgt"]["value"].rsplit("/", 1)[-1]
        if src in qids and tgt in qids and tgt not in all_srcs:
            ref_map.setdefault(src, set()).add(tgt)

    for src, tgts in ref_map.items():
        src_lbl   = get_label(src)
        feat = URIRef(f"{sappho}feature/work_ref/{src}")
        if (feat, RDF.type, intro.INT18_Reference) not in g:
            g.add((feat, RDF.type, intro.INT18_Reference))
            g.add((feat, RDFS.label,
                   Literal(f"Reference to {src_lbl} (expression)", lang="en")))

        expr_src = ensure_expression(src, src_lbl)

        for tgt in sorted(tgts):
            tgt_lbl  = get_label(tgt)
            expr_tgt = ensure_expression(tgt, tgt_lbl)
            rel      = get_or_create_int31_relation(expr_src, expr_tgt)
            if rel is None:
                continue

            if (feat, intro.R22_providesSimilarityForRelation, rel) not in g:
                g.add((feat, intro.R22_providesSimilarityForRelation, rel))
                g.add((rel, intro.R22i_relationIsBasedOnSimilarity, feat))

            add_actualization(
                feat,
                expr_tgt,
                f"{src_lbl} in {tgt_lbl}",
                rel
            )
            
            fid = feat.split("/")[-1]
            eid = expr_tgt.split("/")[-1]
            act = URIRef(f"{sappho}actualization/work_ref/{fid}_{eid}")
            g.add((act, ecrm.P67_refers_to, expr_src))
            g.add((expr_src, ecrm.P67i_is_referred_to_by, act))
            
# Characters
from itertools import combinations

def ensure_person_reference(char_qid: str):
    p_uri  = URIRef(f"{sappho}person/{char_qid}")
    feat   = URIRef(f"{sappho}feature/person_ref/{char_qid}")
    name   = get_label(char_qid)

    if (p_uri, RDF.type, ecrm.E21_Person) not in g:
        g.add((p_uri, RDF.type, ecrm.E21_Person))
        g.add((p_uri, RDFS.label, Literal(name, lang="en")))
        g.add((p_uri, OWL.sameAs, URIRef(WD_ENTITY + char_qid)))
        add_identifier(p_uri, char_qid)

    if (feat, RDF.type, intro.INT18_Reference) not in g:
        g.add((feat, RDF.type, intro.INT18_Reference))
        g.add((feat, RDFS.label,
               Literal(f"Reference to {name} (person)", lang="en")))

    return p_uri, feat

def process_characters(qids):
    vals = " ".join(f"wd:{q}" for q in qids)
    sparql = f"""
PREFIX wdt: <http://www.wikidata.org/prop/direct/>
SELECT DISTINCT ?wrk ?char WHERE {{
  VALUES ?wrk {{ {vals} }}
  {{ ?wrk wdt:P674 ?char . }}
  UNION
  {{
    ?wrk ?p ?char .
    FILTER(?p IN (wdt:P180, wdt:P921, wdt:P527))
    VALUES ?cls {{ wd:Q95074 wd:Q3658341 wd:Q15632617 wd:Q97498056 wd:Q122192387 wd:Q115537581 }}
    ?char wdt:P31/wdt:P279* ?cls .
  }}
}}
"""
    res = run_sparql(sparql)["results"]["bindings"]

    char_map: dict[str, set[str]] = {}
    for b in res:
        w    = b["wrk"]["value"].rsplit("/",1)[-1]
        char = b["char"]["value"].rsplit("/",1)[-1]
        char_map.setdefault(char, set()).add(w)

    for char, works in char_map.items():
        if len(works) < 2:
            continue

        lbl = get_label(char)
        
        is_person = run_sparql(f"""
          SELECT ?x WHERE {{
            wd:{char} wdt:P31/wdt:P279* wd:Q5.
          }} LIMIT 1
        """)["results"]["bindings"]
        if is_person:
            p_node, p_ref = ensure_person_reference(char)
        else:
            p_node = p_ref = None

        feat = URIRef(f"{sappho}feature/character/{char}")
        if (feat, None, None) not in g:
            g.add((feat, RDF.type, intro.INT_Character))
            g.add((feat, RDFS.label, Literal(lbl, lang="en")))
            g.add((feat, OWL.sameAs, URIRef(f"{WD_ENTITY}{char}")))
            add_identifier(feat, char)

        for w1, w2 in combinations(sorted(works), 2):
            expr1 = ensure_expression(w1, get_label(w1))
            expr2 = ensure_expression(w2, get_label(w2))

            rel = get_or_create_int31_relation(expr1, expr2)
            if rel is None:
                continue

            if (feat, intro.R22_providesSimilarityForRelation, rel) not in g:
                g.add((feat, intro.R22_providesSimilarityForRelation, rel))
                g.add((rel, intro.R22i_relationIsBasedOnSimilarity, feat))

            act1 = add_actualization(feat, expr1, f"{lbl} in {get_label(w1)}", rel)
            act2 = add_actualization(feat, expr2, f"{lbl} in {get_label(w2)}", rel)

            if p_node is not None:
                for act in (act1, act2):
                    g.add((act, ecrm.P67_refers_to, p_node))
                    g.add((p_node, ecrm.P67i_is_referred_to_by, act))
            
            for act, expr, work in ((act1, expr1, w1), (act2, expr2, w2)):
                feat_intp, act_intp = add_interpretation(
                    act,
                    f"Interpretation of {lbl} in {get_label(work)}",
                    URIRef(WD_ENTITY + expr.split('/')[-1])
                )

# Citations & Passages
def process_citations(qids):
    vals = " ".join(f"wd:{q}" for q in qids)

    q1 = f"""
PREFIX wdt: <http://www.wikidata.org/prop/direct/>
SELECT DISTINCT ?src ?tgt WHERE {{
  VALUES ?src {{ {vals} }}
  ?tgt ?p ?src FILTER(?p IN (wdt:P2860,wdt:P6166))
}}
"""
    binds = run_sparql(q1)["results"]["bindings"]

    pair_set = set()
    for row in binds:
        s = row["src"]["value"].rsplit("/",1)[-1]
        t = row["tgt"]["value"].rsplit("/",1)[-1]
        if s in qids or t in qids:
            pair_set.add(tuple(sorted((s, t))))

    for w1, w2 in pair_set:
        expr1 = ensure_expression(w1, get_label(w1))
        expr2 = ensure_expression(w2, get_label(w2))
        rel   = get_or_create_int31_relation(expr1, expr2)
        if rel is None:
            continue

        for X, expr in ((w1, expr1), (w2, expr2)):
            tp_qid  = f"{X}_{(w2 if X==w1 else w1)}"
            tp_uri  = URIRef(f"{sappho}textpassage/{tp_qid}")
            tp_label = f"Text passage in {get_label(X)}"

            if (tp_uri, None, None) not in g:
                g.add((tp_uri, RDF.type, intro.INT21_TextPassage))
                g.add((tp_uri, RDFS.label, Literal(tp_label, lang="en")))
                
                other_qid = w2
                wd_uri    = URIRef(WD_ENTITY + other_qid)
                g.add((tp_uri, prov.wasDerivedFrom, wd_uri))

            g.add((expr, intro.R30_hasTextPassage, tp_uri))
            g.add((tp_uri, intro.R30i_isTextPassageOf, expr))

            g.add((rel, intro.R24_hasRelatedEntity, tp_uri))
            g.add((tp_uri, intro.R24i_isRelatedEntity, rel))

# Main execution
if __name__ == "__main__":
    processors = [
        lambda q: process_int31(q),
        lambda q: process_plots(q, ["P180","P527","P921"], "Q42109240", intro.INT_Plot, "plot_", True),
        process_person,
        process_citations,
        process_topics,
        process_motifs,
        process_place,
        process_characters,
        process_work_references
    ]

    for fn in tqdm(processors, unit="task"):
        fn(qids)
    
    # Mapping
    
    ecrm_classes = [
        "E21_Person",
        "E42_Identifier",
        "E53_Place",
        "E55_Type",
    ]
    for cls in ecrm_classes:
        g.add((ecrm[cls], OWL.equivalentClass, crm[cls]))

    ecrm_props = [
        ("P1_is_identified_by",  "P1i_identifies"),
        ("P2_has_type",           "P2i_is_type_of"),
        ("P67_refers_to",         "P67i_is_referred_to_by"),
    ]
    for direct, inverse in ecrm_props:
        g.add((ecrm[direct],  OWL.equivalentProperty, crm[direct]))
        g.add((ecrm[inverse], OWL.equivalentProperty, crm[inverse]))
        g.add((ecrm[direct],  OWL.inverseOf, ecrm[inverse]))
        g.add((ecrm[inverse], OWL.inverseOf, ecrm[direct]))
    
    g.add((lrmoo.F2_Expression, OWL.equivalentClass, frbroo.F2_Expression))

    # Serialize
    g.serialize(destination="relations.ttl", format="turtle")
