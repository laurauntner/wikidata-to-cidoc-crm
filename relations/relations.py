"""
This script retrieves intertextual data from Wikidata based on a list of QIDs (from a CSV file)
and transforms it into RDF triples according to INTRO, LRMoo/FRBRoo and CIDOC CRM (OWL/eCRM).

The output is serialized as Turtle and written to 'relations.ttl'.

"""

import csv
import time
import argparse
from functools import lru_cache
from itertools import combinations
from typing import Union, Iterable, Tuple, List, Dict, Any, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone

from rdflib import Graph, Namespace, URIRef, Literal
from rdflib.namespace import RDF, RDFS, OWL
from tqdm import tqdm

# Settings
INPUT_CSV_DEFAULT = "work-qids.csv"
OUTPUT_TTL_DEFAULT = "relations.ttl"

SPARQL_URL = "https://query.wikidata.org/sparql"
USER_AGENT = "SapphoIntertextualRelationsBot/1.0 (laura.untner@fu-berlin.de)"
HTTP_TIMEOUT = 120
MAX_RETRIES = 5

# Namespaces
WD_ENTITY = "http://www.wikidata.org/entity/"
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

# HTTP helpers
def _parse_retry_after(header_val: str) -> Optional[float]:
    """
    Parse 'Retry-After' (seconds or HTTP-date). Return seconds as float, or None.
    """
    if not header_val:
        return None
    header_val = header_val.strip()
    if header_val.isdigit():
        return float(header_val)
    try:
        dt = parsedate_to_datetime(header_val)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return max(0.0, (dt - datetime.now(timezone.utc)).total_seconds())
    except Exception:
        return None

def make_session() -> requests.Session:
    """
    Create pooled session; manual retry control respects Retry-After fully.
    """
    sess = requests.Session()
    sess.headers.update({"Accept": "application/sparql-results+json", "User-Agent": USER_AGENT})
    retry = Retry(
        total=0,
        respect_retry_after_header=True,
        backoff_factor=0,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["GET", "POST"]),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=20)
    sess.mount("http://", adapter)
    sess.mount("https://", adapter)
    return sess

SESSION = make_session()

def http_request_with_retry(
    method: str,
    url: str,
    *,
    params: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    ok_statuses: Iterable[int] = (200,),
    max_retries: int = MAX_RETRIES,
    timeout: int = HTTP_TIMEOUT,
) -> requests.Response:
    """
    Perform HTTP request; retry on 429/5xx. Respect Retry-After; otherwise gentle backoff.
    """
    tries = 0
    while True:
        tries += 1
        resp = SESSION.request(method, url, params=params, headers=headers, timeout=timeout)

        if resp.status_code in ok_statuses:
            return resp

        if resp.status_code == 429:
            retry_after = _parse_retry_after(resp.headers.get("Retry-After", ""))
            wait_s = retry_after if retry_after is not None else 5.0
            print(f"429 Too Many Requests – waiting {wait_s:.1f}s (try {tries}/{max_retries})")
            if tries >= max_retries:
                resp.raise_for_status()
            time.sleep(wait_s)
            continue

        if 500 <= resp.status_code < 600:
            retry_after = _parse_retry_after(resp.headers.get("Retry-After", "")) or min(10.0, 1.5 ** (tries - 1))
            print(f"{resp.status_code} Server error – waiting {retry_after:.1f}s (try {tries}/{max_retries})")
            if tries >= max_retries:
                resp.raise_for_status()
            time.sleep(retry_after)
            continue

        resp.raise_for_status()

def run_sparql(query: str) -> dict:
    """
    Run a SPARQL query using the Retry-After-aware HTTP routine.
    """
    resp = http_request_with_retry("GET", SPARQL_URL, params={"query": query})
    return resp.json()

# Label helper
@lru_cache(None)
def get_label(qid: str, lang: str = "en") -> str:
    for lg in (lang, "de"):
        q = f"""
          SELECT ?l WHERE {{
            wd:{qid} rdfs:label ?l .
            FILTER(LANG(?l)="{lg}")
          }} LIMIT 1
        """
        data = run_sparql(q)
        b = data["results"]["bindings"]
        if b:
            return b[0]["l"]["value"]
    return qid

# Graph setup
def build_graph() -> Graph:
    g = Graph()
    for prefix, ns in [
        ("sappho", sappho),
        ("ecrm", ecrm),
        ("crm", crm),
        ("frbroo", frbroo),
        ("efrbroo", efrbroo),
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
    g.add((ontology_uri, OWL.imports, ecrm_uri))
    g.add((ontology_uri, OWL.imports, lrmoo_uri))
    g.add((ontology_uri, OWL.imports, intro_uri))

    # ID-Type
    ID_TYPE = URIRef(sappho + "id_type/wikidata")
    g.add((ID_TYPE, RDF.type, ecrm.E55_Type))
    g.add((ID_TYPE, RDFS.label, Literal("Wikidata ID", lang="en")))
    g.add((ID_TYPE, OWL.sameAs, URIRef(WD_ENTITY + "Q43649390")))
    return g

# Helper functions
def add_identifier(g: Graph, entity: URIRef, qid: str):
    uri = URIRef(f"{sappho}identifier/{qid}")
    pure = qid.split("_")[-1]
    g.add((uri, RDF.type, ecrm.E42_Identifier))
    g.add((uri, RDFS.label, Literal(pure, lang="en")))
    g.add((uri, ecrm.P2_has_type, URIRef(sappho + "id_type/wikidata")))
    g.add((URIRef(sappho + "id_type/wikidata"), ecrm.P2i_is_type_of, uri))
    g.add((uri, prov.wasDerivedFrom, URIRef(f"{WD_ENTITY}{pure}")))
    g.add((entity, ecrm.P1_is_identified_by, uri))
    g.add((uri, ecrm.P1i_identifies, entity))

def ensure_expression(g: Graph, qid: str, label: str = None) -> URIRef:
    uri = URIRef(f"{sappho}expression/{qid}")
    if (uri, RDF.type, lrmoo.F2_Expression) in g:
        return uri
    g.add((uri, RDF.type, lrmoo.F2_Expression))
    g.add((uri, RDFS.label, Literal(f"Expression of {label or qid}", lang="en")))
    g.add((uri, OWL.sameAs, URIRef(WD_ENTITY + qid)))
    return uri

def ensure_feature(
    g: Graph,
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
         add_identifier(g, uri, qid)
     return uri

def add_interpretation(
    g: Graph,
    target: URIRef,
    label: str,
    derived_from: Union[URIRef, Iterable[URIRef]]
) -> Tuple[URIRef, URIRef]:

    tid      = str(target).split("/")[-1]
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
            qid = str(src).split("/")[-1]
            g.add((act_uri, prov.wasDerivedFrom, URIRef(WD_ENTITY + qid)))

        g.add((feat_uri, intro.R17i_featureIsActualizedIn, act_uri))
        g.add((act_uri, intro.R17_actualizesFeature, feat_uri))

    g.add((act_uri, intro.R21_identifies, target))
    g.add((target, intro.R21i_isIdentifiedBy, act_uri))

    return feat_uri, act_uri

def add_actualization(g: Graph, feature: URIRef, expression: URIRef, label: str, relation: URIRef):
    parts = str(feature).rstrip("/").split("/")
    parts = [p for p in parts if p != "feature"]
    typ = parts[-2]
    qid = parts[-1]
    fid = f"{typ}/{qid}"
    eid = str(expression).split("/")[-1]
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
    g.add((expression, intro.R24i_isRelatedEntity, relation))
    g.add((relation, intro.R24_hasRelatedEntity, expression))
    feat_intp, act_intp = add_interpretation(
        g,
        act,
        f"Interpretation of {label}",
        URIRef(WD_ENTITY + eid)
    )
    return act

def get_or_create_int31_relation(g: Graph, expr1: URIRef, expr2: URIRef) -> Optional[URIRef]:
    if expr1 == expr2:
        return None
    w1, w2 = str(expr1).split("/")[-1], str(expr2).split("/")[-1]

    if w1 < w2:
        rel_uri = URIRef(f"{sappho}relation/{w1}_{w2}")
    else:
        rel_uri = URIRef(f"{sappho}relation/{w2}_{w1}")

    if (rel_uri, RDF.type, intro.INT31_IntertextualRelation) not in g:
        g.add((rel_uri, RDF.type, intro.INT31_IntertextualRelation))
        g.add((rel_uri, RDFS.label,
               Literal(f"Intertextual relation between {get_label(w1)} and {get_label(w2)}", lang="en")))

        feat_intp, act_intp = add_interpretation(
            g,
            rel_uri,
            f"Interpretation of intertextual relation between {get_label(w1)} and {get_label(w2)}",
            [expr1, expr2]
        )
        
    return rel_uri

# Processors
def process_int31(g: Graph, qids: List[str]):
    vals = " ".join(f"wd:{q}" for q in qids)

    sparql_fwd = f"""
PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX wd:   <http://www.wikidata.org/entity/>
PREFIX wikibase: <http://wikiba.se/ontology#>
SELECT DISTINCT ?w1 ?w2 ?p WHERE {{
  VALUES ?w1 {{ {vals} }}
  VALUES ?w2 {{ {vals} }}
  ?prop wdt:P1647* wd:P4969 ;
        wikibase:directClaim ?p .
  ?w1 ?p ?w2 .
}}
"""

    sparql_bwd = f"""
PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX wd:   <http://www.wikidata.org/entity/>
PREFIX wikibase: <http://wikiba.se/ontology#>
SELECT DISTINCT ?w1 ?w2 ?p WHERE {{
  VALUES ?w1 {{ {vals} }}
  VALUES ?w2 {{ {vals} }}
  VALUES ?base {{ wd:P144 wd:P5059 wd:P941 }}
  ?prop wdt:P1647* ?base ;
        wikibase:directClaim ?p .
  ?w2 ?p ?w1 .
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

def process_plots(g: Graph, qids: List[str]):
    vals = " ".join(f"wd:{q}" for q in qids)

    query = f"""
PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX wd:   <http://www.wikidata.org/entity/>
PREFIX wikibase: <http://wikiba.se/ontology#>
SELECT ?wrk ?tgt WHERE {{
  VALUES ?wrk {{ {vals} }}
  {{
    SELECT ?tgt WHERE {{
      VALUES ?wrk {{ {vals} }}
      ?prop wdt:P1647* wd:P921 ;
            wikibase:directClaim ?p .
      ?wrk ?p ?tgt .
      ?tgt wdt:P31/wdt:P279* wd:Q42109240 .
    }}
    GROUP BY ?tgt
    HAVING(COUNT(DISTINCT ?wrk) > 1)
  }}
  ?prop wdt:P1647* wd:P921 ;
        wikibase:directClaim ?p .
  ?wrk ?p ?tgt .
  ?tgt wdt:P31/wdt:P279* wd:Q42109240 .
}}
"""
    res = run_sparql(query)["results"]["bindings"]

    mp: Dict[str, List[str]] = {}
    for b in res:
        w   = b["wrk"]["value"].rsplit("/",1)[-1]
        tgt = b["tgt"]["value"].rsplit("/",1)[-1]
        mp.setdefault(tgt, []).append(w)

    for tgt, works in mp.items():
        raw_lbl = get_label(tgt)
        feat_lbl = f"{raw_lbl} (plot)"
        feat = ensure_feature(g, tgt, intro.INT_Plot, feat_lbl, path="feature/plot")

        for w1, w2 in combinations(works, 2):
            expr1 = ensure_expression(g, w1, get_label(w1))
            expr2 = ensure_expression(g, w2, get_label(w2))
            rel   = get_or_create_int31_relation(g, expr1, expr2)
            if rel is None:
                continue

            if (feat, intro.R22_providesSimilarityForRelation, rel) not in g:
                g.add((feat, intro.R22_providesSimilarityForRelation, rel))
                g.add((rel, intro.R22i_relationIsBasedOnSimilarity, feat))

            add_actualization(g, feat, expr1, f"{raw_lbl} in {get_label(w1)}", rel)
            add_actualization(g, feat, expr2, f"{raw_lbl} in {get_label(w2)}", rel)

def process_topics(g: Graph, qids: List[str]):
    vals = " ".join(f"wd:{q}" for q in qids)

    query = f"""
PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX wd:   <http://www.wikidata.org/entity/>
PREFIX wikibase: <http://wikiba.se/ontology#>
SELECT ?wrk ?tgt WHERE {{
  VALUES ?wrk {{ {vals} }}
  {{
    SELECT ?tgt WHERE {{
      VALUES ?wrk {{ {vals} }}
      ?prop wdt:P1647* wd:P921 ;
            wikibase:directClaim ?p .
      ?wrk ?p ?tgt .
      ?tgt wdt:P31/wdt:P279* wd:Q26256810 .
    }}
    GROUP BY ?tgt
    HAVING(COUNT(DISTINCT ?wrk) > 1)
  }}
  ?prop wdt:P1647* wd:P921 ;
        wikibase:directClaim ?p .
  ?wrk ?p ?tgt .
}}
"""
    res = run_sparql(query)["results"]["bindings"]

    mp: Dict[str, List[str]] = {}
    for b in res:
        w = b["wrk"]["value"].rsplit("/",1)[-1]
        t = b["tgt"]["value"].rsplit("/",1)[-1]
        mp.setdefault(t, []).append(w)

    for tgt, works in mp.items():
            raw_lbl = get_label(tgt)
            feat_lbl = f"{raw_lbl} (topic)"
            feat = ensure_feature(g, tgt, intro.INT_Topic, feat_lbl, path="feature/topic")

            for w1, w2 in combinations(works, 2):
                expr1 = ensure_expression(g, w1, get_label(w1))
                expr2 = ensure_expression(g, w2, get_label(w2))

                rel = get_or_create_int31_relation(g, expr1, expr2)
                if rel is None:
                    continue

                if (feat, intro.R22_providesSimilarityForRelation, rel) not in g:
                    g.add((feat, intro.R22_providesSimilarityForRelation, rel))
                    g.add((rel, intro.R22i_relationIsBasedOnSimilarity, feat))

                add_actualization(g, feat, expr1, f"{raw_lbl} in {get_label(w1)}", rel)
                add_actualization(g, feat, expr2, f"{raw_lbl} in {get_label(w2)}", rel)

def process_motifs(g: Graph, qids: List[str]):
    vals = " ".join(f"wd:{q}" for q in qids)
    query = f"""
PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX wd:   <http://www.wikidata.org/entity/>
PREFIX wikibase: <http://wikiba.se/ontology#>
SELECT ?wrk ?motif WHERE {{
  VALUES ?wrk {{ {vals} }}
  {{
    SELECT ?motif WHERE {{
      VALUES ?wrk {{ {vals} }}
      ?prop wdt:P1647* wd:P6962 ;
            wikibase:directClaim ?p .
      ?wrk ?p ?motif .
    }}
    GROUP BY ?motif
    HAVING(COUNT(DISTINCT ?wrk) > 1)
  }}
  ?prop wdt:P1647* wd:P6962 ;
        wikibase:directClaim ?p .
  ?wrk ?p ?motif .
}}
"""
    res = run_sparql(query)["results"]["bindings"]

    mp: Dict[str, List[str]] = {}
    for b in res:
        w = b["wrk"]["value"].rsplit("/",1)[-1]
        m = b["motif"]["value"].rsplit("/",1)[-1]
        mp.setdefault(m, []).append(w)

    for motif, works in mp.items():
        raw_lbl = get_label(motif)
        feat_lbl = f"{raw_lbl} (motif)"
        feat = ensure_feature(g, motif, intro.INT_Motif, feat_lbl, path="feature/motif")

        for w1, w2 in combinations(works, 2):
            expr1 = ensure_expression(g, w1, get_label(w1))
            expr2 = ensure_expression(g, w2, get_label(w2))

            rel = get_or_create_int31_relation(g, expr1, expr2)
            if rel is None:
                continue

            if (feat, intro.R22_providesSimilarityForRelation, rel) not in g:
                g.add((feat, intro.R22_providesSimilarityForRelation, rel))
                g.add((rel, intro.R22i_relationIsBasedOnSimilarity, feat))

            add_actualization(g, feat, expr1, f"{raw_lbl} in {get_label(w1)}", rel)
            add_actualization(g, feat, expr2, f"{raw_lbl} in {get_label(w2)}", rel)

def process_person(g: Graph, qids: List[str]):
    vals = " ".join(f"wd:{q}" for q in qids)
    q = f"""
PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX wd:   <http://www.wikidata.org/entity/>
PREFIX wikibase: <http://wikiba.se/ontology#>
SELECT DISTINCT ?wrk ?pers WHERE {{
  VALUES ?wrk {{ {vals} }}
  VALUES ?base {{ wd:P180 wd:P921 wd:P527 }}
  ?prop wdt:P1647* ?base ;
        wikibase:directClaim ?p .
  ?wrk ?p ?pers .
  ?pers wdt:P31/wdt:P279* wd:Q5 .
}}
"""
    mp: Dict[str, set] = {}
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
        add_identifier(g, p_uri, p)  

        feat = URIRef(f"{sappho}feature/person_ref/{p}")
        if (feat, None, None) not in g:
            g.add((feat, RDF.type, intro.INT18_Reference))
            g.add((feat, RDFS.label,
                   Literal(f"Reference to {name} (person)", lang="en")))

        for w1, w2 in combinations(sorted(works), 2):
            expr1 = ensure_expression(g, w1, get_label(w1))
            expr2 = ensure_expression(g, w2, get_label(w2))

            rel = get_or_create_int31_relation(g, expr1, expr2)
            if rel is None:
                continue

            if (feat, intro.R22_providesSimilarityForRelation, rel) not in g:
                g.add((feat, intro.R22_providesSimilarityForRelation, rel))
                g.add((rel, intro.R22i_relationIsBasedOnSimilarity, feat))

            add_actualization(g, feat, expr1, f"{name} in {get_label(w1)}", rel)
            act1 = add_actualization(g, feat, expr1, f"Reference to {name} in {get_label(w1)}", rel)
            g.add((act1, ecrm.P67_refers_to, p_uri))
            g.add((p_uri,  ecrm.P67i_is_referred_to_by, act1))

            add_actualization(g, feat, expr2, f"{name} in {get_label(w2)}", rel)
            act2 = add_actualization(g, feat, expr2, f"Reference to {name} in {get_label(w2)}", rel)
            g.add((act2, ecrm.P67_refers_to, p_uri))
            g.add((p_uri,  ecrm.P67i_is_referred_to_by, act2))

def process_place(g: Graph, qids: List[str]):
    vals = " ".join(f"wd:{q}" for q in qids)
    q = f"""
PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX wd:   <http://www.wikidata.org/entity/>
PREFIX wikibase: <http://wikiba.se/ontology#>
SELECT DISTINCT ?wrk ?place WHERE {{
  VALUES ?wrk {{ {vals} }}
  ?prop wdt:P1647* wd:P921 ;
        wikibase:directClaim ?p .
  ?wrk ?p ?place .
  ?place wdt:P31/wdt:P279* wd:Q2221906 .
}}
"""
    mp: Dict[str, set] = {}
    for row in run_sparql(q)["results"]["bindings"]:
        w = row["wrk"]["value"].split("/")[-1]
        p = row["place"]["value"].split("/")[-1]
        mp.setdefault(p, set()).add(w)

    for pl, works in mp.items():
        if len(works) < 2:
            continue

        name  = get_label(pl)
        p_uri = URIRef(f"{sappho}place/{pl}")
        g.add((p_uri, RDF.type, ecrm.E53_Place))
        g.add((p_uri, RDFS.label, Literal(name, lang="en")))
        g.add((p_uri, OWL.sameAs, URIRef(WD_ENTITY + pl)))
        add_identifier(g, p_uri, pl) 

        feat = URIRef(f"{sappho}feature/place_ref/{pl}")
        if (feat, None, None) not in g:
            g.add((feat, RDF.type, intro.INT18_Reference))
            g.add((feat, RDFS.label,
                   Literal(f"Reference to {name} (place)", lang="en")))

        for w1, w2 in combinations(sorted(works), 2):
            expr1 = ensure_expression(g, w1, get_label(w1))
            expr2 = ensure_expression(g, w2, get_label(w2))
            rel   = get_or_create_int31_relation(g, expr1, expr2)
            if rel is None:
                continue
            
            if (feat, intro.R22_providesSimilarityForRelation, rel) not in g:
                g.add((feat, intro.R22_providesSimilarityForRelation, rel))
                g.add((rel, intro.R22i_relationIsBasedOnSimilarity, feat))

            add_actualization(g, feat, expr1, f"{name} in {get_label(w1)}", rel)
            fid = str(feat).split("/")[-1]
            eid = str(expr1).split("/")[-1]
            act1 = URIRef(f"{sappho}actualization/place_ref/{fid}_{eid}")
            g.add((act1, ecrm.P67_refers_to, p_uri))
            g.add((p_uri,  ecrm.P67i_is_referred_to_by, act1))

            add_actualization(g, feat, expr2, f"{name} in {get_label(w2)}", rel)
            eid = str(expr2).split("/")[-1]
            act2 = URIRef(f"{sappho}actualization/place_ref/{fid}_{eid}")
            g.add((act2, ecrm.P67_refers_to, p_uri))
            g.add((p_uri,  ecrm.P67i_is_referred_to_by, act2))

def process_work_references(g: Graph, qids: List[str]):
    vals = " ".join(f"wd:{q}" for q in qids)

    sparql = f"""
PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX wd:   <http://www.wikidata.org/entity/>
PREFIX wikibase: <http://wikiba.se/ontology#>
SELECT DISTINCT ?src ?tgt WHERE {{
  VALUES ?src {{ {vals} }}
  ?prop wdt:P1647* wd:P921 ;
        wikibase:directClaim ?p .
  ?src ?p ?tgt .
  FILTER(STRSTARTS(STR(?tgt), "http://www.wikidata.org/entity/Q"))
}}
"""
    binds = run_sparql(sparql)["results"]["bindings"]

    all_srcs = {
        row["src"]["value"].rsplit("/", 1)[-1]
        for row in binds
        if row["src"]["value"].rsplit("/", 1)[-1] in qids
    }

    ref_map: Dict[str, set] = {}
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

        expr_src = ensure_expression(g, src, src_lbl)

        for tgt in sorted(tgts):
            tgt_lbl  = get_label(tgt)
            expr_tgt = ensure_expression(g, tgt, tgt_lbl)
            rel      = get_or_create_int31_relation(g, expr_src, expr_tgt)
            if rel is None:
                continue

            if (feat, intro.R22_providesSimilarityForRelation, rel) not in g:
                g.add((feat, intro.R22_providesSimilarityForRelation, rel))
                g.add((rel, intro.R22i_relationIsBasedOnSimilarity, feat))

            add_actualization(
                g,
                feat,
                expr_tgt,
                f"{src_lbl} in {tgt_lbl}",
                rel
            )
            
            fid = str(feat).split("/")[-1]
            eid = str(expr_tgt).split("/")[-1]
            act = URIRef(f"{sappho}actualization/work_ref/{fid}_{eid}")
            g.add((act, ecrm.P67_refers_to, expr_src))
            g.add((expr_src, ecrm.P67i_is_referred_to_by, act))

def ensure_person_reference(g: Graph, char_qid: str):
    p_uri  = URIRef(f"{sappho}person/{char_qid}")
    feat   = URIRef(f"{sappho}feature/person_ref/{char_qid}")
    name   = get_label(char_qid)

    if (p_uri, RDF.type, ecrm.E21_Person) not in g:
        g.add((p_uri, RDF.type, ecrm.E21_Person))
        g.add((p_uri, RDFS.label, Literal(name, lang="en")))
        g.add((p_uri, OWL.sameAs, URIRef(WD_ENTITY + char_qid)))
        add_identifier(g, p_uri, char_qid)

    if (feat, RDF.type, intro.INT18_Reference) not in g:
        g.add((feat, RDF.type, intro.INT18_Reference))
        g.add((feat, RDFS.label,
               Literal(f"Reference to {name} (person)", lang="en")))

    return p_uri, feat

def process_characters(g: Graph, qids: List[str]):
    vals = " ".join(f"wd:{q}" for q in qids)
    sparql = f"""
PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX wd:   <http://www.wikidata.org/entity/>
PREFIX wikibase: <http://wikiba.se/ontology#>
SELECT DISTINCT ?wrk ?char WHERE {{
  VALUES ?wrk {{ {vals} }}
  {{ 
    ?prop674 wdt:P1647* wd:P674 ;
             wikibase:directClaim ?p674 .
    ?wrk ?p674 ?char .
    }}
  UNION
  {{
    VALUES ?base {{ wd:P180 wd:P921 }}
    ?prop wdt:P1647* ?base ;
          wikibase:directClaim ?p .
    ?wrk ?p ?char .
    VALUES ?cls {{ wd:Q3658341 wd:Q15632617 }}
    ?char wdt:P31/wdt:P279* ?cls .
  }}
}}
"""
    res = run_sparql(sparql)["results"]["bindings"]

    char_map: Dict[str, set] = {}
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
            p_node, p_ref = ensure_person_reference(g, char)
        else:
            p_node = p_ref = None

        feat = URIRef(f"{sappho}feature/character/{char}")
        if (feat, None, None) not in g:
            g.add((feat, RDF.type, intro.INT_Character))
            g.add((feat, RDFS.label, Literal(lbl, lang="en")))
            g.add((feat, OWL.sameAs, URIRef(f"{WD_ENTITY}{char}")))
            add_identifier(g, feat, char)

        for w1, w2 in combinations(sorted(works), 2):
            expr1 = ensure_expression(g, w1, get_label(w1))
            expr2 = ensure_expression(g, w2, get_label(w2))

            rel = get_or_create_int31_relation(g, expr1, expr2)
            if rel is None:
                continue

            if (feat, intro.R22_providesSimilarityForRelation, rel) not in g:
                g.add((feat, intro.R22_providesSimilarityForRelation, rel))
                g.add((rel, intro.R22i_relationIsBasedOnSimilarity, feat))

            act1 = add_actualization(g, feat, expr1, f"{lbl} in {get_label(w1)}", rel)
            act2 = add_actualization(g, feat, expr2, f"{lbl} in {get_label(w2)}", rel)

            if p_node is not None:
                for act in (act1, act2):
                    g.add((act, ecrm.P67_refers_to, p_node))
                    g.add((p_node, ecrm.P67i_is_referred_to_by, act))
            
            for act, expr, work in ((act1, expr1, w1), (act2, expr2, w2)):
                feat_intp, act_intp = add_interpretation(
                    g,
                    act,
                    f"Interpretation of {lbl} in {get_label(work)}",
                    URIRef(WD_ENTITY + str(expr).split('/')[-1])
                )

def process_citations(g: Graph, qids: List[str]):
    vals = " ".join(f"wd:{q}" for q in qids)

    q1 = f"""
PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX wd:   <http://www.wikidata.org/entity/>
PREFIX wikibase: <http://wikiba.se/ontology#>
SELECT DISTINCT ?src ?tgt WHERE {{
  VALUES ?src {{ {vals} }}
  VALUES ?tgt {{ {vals} }}
  VALUES ?base {{ wd:P2860 wd:P6166 }}
  ?prop wdt:P1647* ?base ;
        wikibase:directClaim ?p .
  ?tgt ?p ?src .
}}
""" 
    binds = run_sparql(q1)["results"]["bindings"]

    pair_set = set()
    for row in binds:
        s = row["src"]["value"].rsplit("/",1)[-1]
        t = row["tgt"]["value"].rsplit("/",1)[-1]
        pair_set.add(tuple(sorted((s, t))))

    for w1, w2 in pair_set:
        expr1 = ensure_expression(g, w1, get_label(w1))
        expr2 = ensure_expression(g, w2, get_label(w2))
        rel   = get_or_create_int31_relation(g, expr1, expr2)
        if rel is None:
            continue

        for X, expr in ((w1, expr1), (w2, expr2)):
            tp_qid  = f"{X}_{(w2 if X==w1 else w1)}"
            tp_uri  = URIRef(f"{sappho}textpassage/{tp_qid}")
            tp_label = f"Text passage in {get_label(X)}"

            if (tp_uri, None, None) not in g:
                g.add((tp_uri, RDF.type, intro.INT21_TextPassage))
                g.add((tp_uri, RDFS.label, Literal(tp_label, lang="en")))
                
                other_qid = w2 if X == w1 else w1
                wd_uri    = URIRef(WD_ENTITY + other_qid)
                g.add((tp_uri, prov.wasDerivedFrom, wd_uri))

            g.add((expr, intro.R30_hasTextPassage, tp_uri))
            g.add((tp_uri, intro.R30i_isTextPassageOf, expr))

            g.add((rel, intro.R24_hasRelatedEntity, tp_uri))
            g.add((tp_uri, intro.R24i_isRelatedEntity, rel))

# CLI / Entry
def parse_args(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--input", default=INPUT_CSV_DEFAULT, help="CSV file with QIDs (default: work-qids.csv)")
    p.add_argument("--output", default=OUTPUT_TTL_DEFAULT, help="Output TTL file (default: relations.ttl)")
    return p.parse_args(argv)

def main(argv=None) -> int:
    args = parse_args(argv)

    # Load QIDs
    with open(args.input, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        qids = [row[0] for row in reader if row and row[0].startswith("Q")]

    # Build graph
    g = build_graph()

    # Processors
    processors = [
        process_int31,
        process_plots,
        process_citations,
        process_topics,
        process_motifs,
        process_place,
        process_characters,
        process_work_references
    ]

    for fn in tqdm(processors, unit="task"):
        fn(g, qids)
    
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
    g.add((lrmoo.F2_Expression, OWL.equivalentClass, efrbroo.F2_Expression))

    # Serialize
    g.serialize(destination=args.output, format="turtle")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
