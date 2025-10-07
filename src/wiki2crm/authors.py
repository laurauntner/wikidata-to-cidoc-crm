"""
This script retrieves person data from Wikidata based on a list of QIDs (from a CSV file)
and transforms it into CIDOC CRM (OWL/eCRM) RDF triples.

The output is serialized as Turtle and written to 'authors.ttl'.
"""

import csv
import time
import logging
import rdflib
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, RDFS, OWL, XSD
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Iterable, List
from pathlib import Path
from tqdm import tqdm
import argparse
from pyshacl import validate
from wiki2crm import resources

# Settings
SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"
USER_AGENT = "SapphoDataIntegrationBot/1.0 (laura.untner@fu-berlin.de)"
HTTP_TIMEOUT = 90
MAX_RETRIES = 5

# Namespaces
CRM = Namespace("http://www.cidoc-crm.org/cidoc-crm/") # CIDOC CRM
ECRM = Namespace("http://erlangen-crm.org/current/")  # eCRM - CIDOC CRM (OWL version)
ECRM_URI = URIRef("http://erlangen-crm.org/current/")
PROV = Namespace("http://www.w3.org/ns/prov#")  # PROV-O - Provenance Ontology
WD = "http://www.wikidata.org/entity/"  # Base URI for Wikidata entities
SAPPHO_BASE_URI = "https://sappho-digital.com/"  # Base URI for Sappho
SAPPHO = Namespace("https://sappho-digital.com/")

# HTTP helpers
def _parse_retry_after(header_val: str) -> Optional[float]:
    """
    Parse 'Retry-After' per RFC 7231. It may be either a delay in seconds
    or an HTTP-date. Returns seconds as float, or None if not parseable.
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
    Build a pooled Session. We keep manual control over retries to fully respect Retry-After.
    """
    sess = requests.Session()
    sess.headers.update({"User-Agent": USER_AGENT})
    retry = Retry(
        total=0,  # manual control below
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
    data: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    ok_statuses: Iterable[int] = (200,),
    max_retries: int = MAX_RETRIES,
    timeout: int = HTTP_TIMEOUT,
) -> requests.Response:
    """
    Perform an HTTP request and retry on 429/5xx.
    Uses Retry-After if present; otherwise applies a gentle backoff.
    """
    tries = 0
    while True:
        tries += 1
        resp = SESSION.request(method, url, params=params, data=data, headers=headers, timeout=timeout)

        if resp.status_code in ok_statuses:
            return resp

        if resp.status_code == 429:
            retry_after = _parse_retry_after(resp.headers.get("Retry-After", ""))
            wait_s = retry_after if retry_after is not None else 5.0
            logging.warning("429 Too Many Requests – waiting %.2fs (try %d/%d)", wait_s, tries, max_retries)
            if tries >= max_retries:
                resp.raise_for_status()
            time.sleep(wait_s)
            continue

        if 500 <= resp.status_code < 600:
            retry_after = _parse_retry_after(resp.headers.get("Retry-After", "")) or min(10.0, 1.5 ** (tries - 1))
            logging.warning("%s Server error – waiting %.2fs (try %d/%d)", resp.status_code, retry_after, tries, max_retries)
            if tries >= max_retries:
                resp.raise_for_status()
            time.sleep(retry_after)
            continue

        # non-retriable error
        resp.raise_for_status()

def query_wikidata_sparql(query: str, accept: str = "application/sparql-results+json") -> dict:
    """
    Execute a SPARQL query against Wikidata using the retry-aware HTTP routine.
    """
    headers = {"Accept": accept}
    resp = http_request_with_retry(
        "GET",
        SPARQL_ENDPOINT,
        params={"query": query},
        headers=headers,
    )
    return resp.json()

# Ontology, graph creation, and bindings
def create_graph() -> Graph:
    # Create the RDF graph
    g = Graph()
    g.bind("crm", CRM)
    g.bind("ecrm", ECRM)
    g.bind("prov", PROV)
    g.bind("owl", OWL)
    g.bind("rdfs", RDFS)
    g.bind("sappho", SAPPHO)

    # Ontology
    ontology_uri = URIRef("https://sappho-digital.com/ontology/authors")
    g.add((ontology_uri, RDF.type, OWL.Ontology))
    g.add((ontology_uri, OWL.imports, ECRM_URI))

    # CIDOC CRM alignment and property inverses
    ecrm_to_crm = [
        # Classes
        "E21_Person", "E67_Birth", "E69_Death", "E52_Time-Span", "E53_Place",
        "E36_Visual_Item", "E38_Image", "E55_Type", "E42_Identifier", "E82_Actor_Appellation"
    ]

    for cls in ecrm_to_crm:
        g.add((ECRM.term(cls), OWL.equivalentClass, CRM.term(cls)))

    # Properties
    ecrm_properties = [
        ("P1_is_identified_by", "P1i_identifies"),
        ("P2_has_type", "P2i_is_type_of"),
        ("P4_has_time-span", "P4i_is_time-span_of"),
        ("P7_took_place_at", "P7i_witnessed"),
        ("P65_shows_visual_item", "P65i_is_shown_by"),
        ("P98_brought_into_life", "P98i_was_born"),
        ("P100_was_death_of", "P100i_died_in"),
        ("P131_is_identified_by", "P131i_identifies"),
        ("P138_represents", "P138i_has_representation")
    ]

    for direct, inverse in ecrm_properties:
        g.add((ECRM.term(direct), OWL.inverseOf, ECRM.term(inverse)))
        g.add((ECRM.term(direct), OWL.equivalentProperty, CRM.term(direct)))
        g.add((ECRM.term(inverse), OWL.inverseOf, ECRM.term(direct)))
        g.add((ECRM.term(inverse), OWL.equivalentProperty, CRM.term(inverse)))

    return g

# Function to get Wikidata data in batches
def get_wikidata_batch(qids: List[str], max_retries: int = MAX_RETRIES) -> Dict[str, List[dict]]:
    values = " ".join(f"wd:{qid}" for qid in qids)
    endpoint = SPARQL_ENDPOINT
    query = f"""
    SELECT ?item ?itemLabel ?gender ?genderLabel ?birthPlace ?birthPlaceLabel ?birthDate ?deathPlace ?deathPlaceLabel ?deathDate ?image WHERE {{
      VALUES ?item {{ {values} }}
      OPTIONAL {{ ?item wdt:P21 ?gender . }}
      OPTIONAL {{ ?item wdt:P569 ?birthDate . }}
      OPTIONAL {{ ?item wdt:P19 ?birthPlace . }}
      OPTIONAL {{ ?item wdt:P570 ?deathDate . }}
      OPTIONAL {{ ?item wdt:P20 ?deathPlace . }}
      OPTIONAL {{ ?item wdt:P18 ?image . }}
      SERVICE wikibase:label {{
        bd:serviceParam wikibase:language "en" .
      }}
    }}
    """
    headers = {
        "Accept": "application/sparql-results+json",
        "User-Agent": USER_AGENT
    }

    tries = 0
    while True:
        tries += 1
        try:
            resp = http_request_with_retry(
                "GET",
                endpoint,
                params={"query": query},
                headers=headers,
                ok_statuses=(200,),
                max_retries=max_retries,
                timeout=HTTP_TIMEOUT,
            )
            results = resp.json()["results"]["bindings"]
            grouped: Dict[str, List[dict]] = {}
            for b in results:
                uri = b["item"]["value"]
                qid = uri.split("/")[-1]
                grouped.setdefault(qid, []).append(b)
            return grouped
        except requests.exceptions.RequestException as e:
            # The underlying http_request_with_retry already waited per Retry-After.
            # If we still get here, we apply a small extra linear wait before next outer try.
            wait = min(5.0 * tries, 20.0)
            print(f"[RETRY {tries}] Batch request failed: {e} – retrying in {wait:.1f}s...")
            if tries >= max_retries:
                print("[ERROR] Maximum retries reached. Skipping batch.")
                return {}
            time.sleep(wait)

def load_qids(path: Path) -> List[str]:
    """
    Load QIDs from the given CSV (expects one QID per row, keep original semantics).
    """
    all_qids: List[str] = []
    with path.open(newline="", encoding="utf-8") as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            if not row:
                continue
            qid = row[0].strip()
            if qid.startswith("Q"):
                all_qids.append(qid)
    return all_qids

def format_date(iso_string: str) -> str:
    return iso_string.split("T")[0]

def process_authors(g: Graph, all_qids: List[str]) -> None:
    """
    Process QIDs in batches and populate the graph (unchanged triple logic).
    """
    batch_size = 20
    gender_cache: Dict[str, URIRef] = {}
    place_cache: Dict[str, URIRef] = {}  # kept for parity, though not used for memo here
    time_span_cache: Dict[URIRef, URIRef] = {}

    for i in tqdm(range(0, len(all_qids), batch_size)):
        batch = all_qids[i:i+batch_size]
        batch_data = get_wikidata_batch(batch)
        for qid in batch:
            uri = f"http://www.wikidata.org/entity/{qid}"
            bindings = batch_data.get(qid, [])
            if not bindings:
                continue

            b = bindings[0]
            label = b.get("itemLabel", {}).get("value", "").strip()
            if not label:
                label = f"Unknown ({qid})"

            person_uri = URIRef(f"{SAPPHO_BASE_URI}person/{qid}")
            name_uri = URIRef(f"{SAPPHO_BASE_URI}appellation/{qid}")
            identifier_uri = URIRef(f"{SAPPHO_BASE_URI}identifier/{qid}")

            # Person core data
            g.add((person_uri, RDF.type, ECRM.E21_Person))
            g.add((person_uri, OWL.sameAs, URIRef(uri)))
            g.add((person_uri, ECRM.P131_is_identified_by, name_uri))
            g.add((name_uri, ECRM.P131i_identifies, person_uri))
            g.add((name_uri, RDF.type, ECRM.E82_Actor_Appellation))
            g.add((name_uri, RDFS.label, Literal(label, lang="en")))
            g.add((name_uri, PROV.wasDerivedFrom, URIRef(uri)))
            g.add((person_uri, RDFS.label, Literal(label, lang="en")))

            g.add((person_uri, ECRM.P1_is_identified_by, identifier_uri))
            g.add((identifier_uri, ECRM.P1i_identifies, person_uri))
            g.add((identifier_uri, RDF.type, ECRM.E42_Identifier))
            g.add((identifier_uri, RDFS.label, Literal(qid)))
            g.add((identifier_uri, ECRM.P2_has_type, URIRef(f"{SAPPHO_BASE_URI}id_type/wikidata")))
            g.add((URIRef(f"{SAPPHO_BASE_URI}id_type/wikidata"), ECRM.P2i_is_type_of, identifier_uri))
            g.add((URIRef(f"{SAPPHO_BASE_URI}id_type/wikidata"), RDF.type, ECRM.E55_Type))
            g.add((URIRef(f"{SAPPHO_BASE_URI}id_type/wikidata"), RDFS.label, Literal("Wikidata ID", lang="en")))

            def create_timespan_uri(date_value: str) -> URIRef:
                return URIRef(f"{SAPPHO_BASE_URI}timespan/{date_value.replace('-', '')}")

            for event_type, date_key, place_key, class_uri, inverse_prop, direct_prop in [
                ("birth", "birthDate", "birthPlace", ECRM.E67_Birth, ECRM.P98i_was_born, ECRM.P98_brought_into_life),
                ("death", "deathDate", "deathPlace", ECRM.E69_Death, ECRM.P100i_died_in, ECRM.P100_was_death_of)
            ]:
                has_date = date_key in b
                has_place = place_key in b
                if has_date or has_place:
                    event_uri = URIRef(f"{SAPPHO_BASE_URI}{event_type}/{qid}")
                    g.add((person_uri, inverse_prop, event_uri))
                    g.add((event_uri, direct_prop, person_uri))
                    g.add((event_uri, RDF.type, class_uri))
                    g.add((event_uri, RDFS.label, Literal(f"{event_type.capitalize()} of {label}", lang="en")))
                    g.add((event_uri, PROV.wasDerivedFrom, URIRef(uri)))

                    if has_date:
                        date_value = format_date(b[date_key]["value"])
                        date_uri = create_timespan_uri(date_value)
                        if date_uri not in time_span_cache:
                            g.add((date_uri, RDF.type, ECRM.term("E52_Time-Span")))
                            g.add((date_uri, RDFS.label, Literal(date_value, datatype=XSD.date)))
                            time_span_cache[date_uri] = date_uri
                        g.add((event_uri, ECRM["P4_has_time-span"], date_uri))
                        g.add((date_uri, ECRM["P4i_is_time-span_of"], event_uri))

                    if has_place:
                        wikidata_place_uri = b[place_key]["value"]
                        place_id = wikidata_place_uri.split("/")[-1]
                        place_uri = URIRef(f"{SAPPHO_BASE_URI}place/{place_id}")
                        place_label = b.get(f"{place_key}Label", {}).get("value")
                        g.add((event_uri, ECRM.P7_took_place_at, place_uri))
                        g.add((place_uri, ECRM.P7i_witnessed, event_uri))
                        g.add((place_uri, RDF.type, ECRM.E53_Place))
                        g.add((place_uri, OWL.sameAs, URIRef(wikidata_place_uri)))
                        if place_label:
                            g.add((place_uri, RDFS.label, Literal(place_label, lang="en")))

            gender_uri_raw = b.get("gender", {}).get("value")
            gender_label = b.get("genderLabel", {}).get("value")
            if gender_uri_raw and gender_label:
                if gender_uri_raw not in gender_cache:
                    sappho_gender_uri = URIRef(f"{SAPPHO_BASE_URI}gender/{gender_uri_raw.split('/')[-1]}")
                    g.add((sappho_gender_uri, RDF.type, ECRM.E55_Type))
                    g.add((sappho_gender_uri, RDFS.label, Literal(gender_label, lang="en")))
                    g.add((sappho_gender_uri, OWL.sameAs, URIRef(gender_uri_raw)))
                    g.add((sappho_gender_uri, ECRM.P2_has_type, URIRef(f"{SAPPHO_BASE_URI}gender_type/wikidata")))
                    g.add((
                        URIRef(f"{SAPPHO_BASE_URI}gender_type/wikidata"),
                        ECRM.P2i_is_type_of,
                        sappho_gender_uri
                    ))
                    g.add((URIRef(f"{SAPPHO_BASE_URI}gender_type/wikidata"), RDF.type, ECRM.E55_Type))
                    g.add((URIRef(f"{SAPPHO_BASE_URI}gender_type/wikidata"), RDFS.label, Literal("Wikidata Gender", lang="en")))
                    gender_cache[gender_uri_raw] = sappho_gender_uri
                g.add((person_uri, ECRM.P2_has_type, gender_cache[gender_uri_raw]))
                g.add((gender_cache[gender_uri_raw], ECRM.P2i_is_type_of, person_uri))

            image_url = b.get("image", {}).get("value")
            if image_url:
                image_instance_uri = URIRef(f"{SAPPHO_BASE_URI}image/{qid}")
                visual_item_uri = URIRef(f"{SAPPHO_BASE_URI}visual_item/{qid}")
                g.add((visual_item_uri, RDF.type, ECRM.E36_Visual_Item))
                g.add((visual_item_uri, RDFS.label, Literal(f"Visual representation of {label}", lang="en")))
                g.add((visual_item_uri, ECRM.P138_represents, person_uri))
                g.add((person_uri, ECRM.P138i_has_representation, visual_item_uri))
                g.add((image_instance_uri, RDF.type, ECRM.E38_Image))
                g.add((image_instance_uri, ECRM.P65_shows_visual_item, visual_item_uri))
                g.add((visual_item_uri, ECRM.P65i_is_shown_by, image_instance_uri))
                g.add((image_instance_uri, RDFS.seeAlso, URIRef(image_url)))
                g.add((image_instance_uri, PROV.wasDerivedFrom, URIRef(uri)))

def parse_args(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Retrieve person data from Wikidata and emit CIDOC CRM TTL"
    )
    p.add_argument("--input",  type=Path, help="CSV with QIDs (e.g. examples/inputs/author-qids.csv)")
    p.add_argument("--output", type=Path, help="Output Turtle (e.g. examples/outputs/authors.ttl)")
    p.add_argument(
        "--shapes",
        type=Path,
        default=resources.shapes_path("author-shapes.ttl"),
        help="Path to SHACL shapes (default: package-installed author-shapes.ttl)",
    )
    p.add_argument("--log-level", default="INFO", help="Logging level (default: INFO)")
    return p.parse_args(argv)

def main(argv=None) -> int:
    args = parse_args(argv)

    logging.basicConfig(level=getattr(logging, args.log_level.upper(), logging.INFO),
                        format="%(levelname)s:%(name)s:%(message)s")

    if args.input is None:
        repo_input = Path("examples/inputs/author-qids.csv")
        if repo_input.exists():
            args.input = repo_input
        else:
            raise SystemExit("--input is required (no examples/inputs/author-qids.csv found)")

    if args.output is None:
        repo_outdir = Path("examples/outputs")
        args.output = (repo_outdir / "authors.ttl") if repo_outdir.exists() else Path("authors.ttl")

    args.output.parent.mkdir(parents=True, exist_ok=True)

    # Create graph
    g = create_graph()

    # Load QIDs
    all_qids = load_qids(args.input)

    # Process and enrich graph
    process_authors(g, all_qids)

    # Serialize to Turtle
    g.serialize(destination=str(args.output), format="turtle")
    print(f"✅ RDF graph written to {args.output}")

    # Validate the output graph using pySHACL
    shapes_graph = Graph().parse(str(args.shapes), format="turtle")

    conforms, report_graph, report_text = validate(
        g,
        shacl_graph=shapes_graph,
        inference="rdfs",
        meta_shacl=True,
        advanced=True,
        abort_on_first=False,
        debug=False,
    )

    print("\n🔎 SHACL Validation Report:")
    print(report_text)

    if not conforms:
        print("❌ Validation failed.")
    else:
        print("✅ Data conforms to SHACL shapes.")

    return 0

if __name__ == "__main__":
    raise SystemExit(main())