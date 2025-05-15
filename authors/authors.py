"""
This script retrieves person data from Wikidata based on a list of QIDs (from a CSV file)
and transforms it into CIDOC CRM (OWL/eCRM) RDF triples.

The output is serialized as Turtle and written to 'authors.ttl'.
"""

import csv
import time
import rdflib
from rdflib import Graph, Literal, RDF, RDFS, Namespace, URIRef
from rdflib.namespace import RDF, RDFS, OWL, XSD
import requests
from tqdm import tqdm

# Namespaces
CRM = Namespace("http://www.cidoc-crm.org/cidoc-crm/") # CIDOC CRM
CRM_URI = URIRef("http://www.cidoc-crm.org/cidoc-crm/")
ECRM = Namespace("http://erlangen-crm.org/current/")  # eCRM - CIDOC CRM (OWL version)
ECRM_URI = URIRef("http://erlangen-crm.org/current/")
PROV = Namespace("http://www.w3.org/ns/prov#")  # PROV-O - Provenance Ontology
PROV_URI = URIRef("http://www.w3.org/ns/prov#")
WD = "http://www.wikidata.org/entity/"  # Base URI for Wikidata entities
SAPPHO_BASE_URI = "https://sappho-digital.com/"  # Base URI for Sappho
SAPPHO = Namespace("https://sappho-digital.com/")

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

g.add((ontology_uri, OWL.imports, CRM_URI))
g.add((ontology_uri, OWL.imports, ECRM_URI))
g.add((ontology_uri, OWL.imports, PROV_URI))

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

# Function to get Wikidata data in batches
def get_wikidata_batch(qids, max_retries=5):
    values = " ".join(f"wd:{qid}" for qid in qids)
    endpoint = "https://query.wikidata.org/sparql"
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
        "User-Agent": "SapphoDataIntegrationBot/1.0 (laura.untner@fu-berlin.de)"
    }
    for attempt in range(1, max_retries + 1):
        try:
            r = requests.get(endpoint, params={"query": query}, headers=headers, timeout=90)
            r.raise_for_status()
            results = r.json()["results"]["bindings"]
            grouped = {}
            for b in results:
                uri = b["item"]["value"]
                qid = uri.split("/")[-1]
                if qid not in grouped:
                    grouped[qid] = []
                grouped[qid].append(b)
            return grouped
        except requests.exceptions.RequestException as e:
            wait = 5 * attempt
            print(f"[RETRY {attempt}] Batch request failed: {e} – retrying in {wait}s...")
            time.sleep(wait)
    print("[ERROR] Maximum retries reached. Skipping batch.")
    return {}

# Load QIDs
all_qids = []
with open("author-qids.csv", newline="") as csvfile:
    reader = csv.reader(csvfile)
    for row in reader:
        qid = row[0].strip()
        if qid.startswith("Q"):
            all_qids.append(qid)

# Processing
batch_size = 20
gender_cache = {}
place_cache = {}
time_span_cache = {}

def format_date(iso_string):
    return iso_string.split("T")[0]

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

        def create_timespan_uri(date_value):
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

# Serialize
g.serialize(destination="authors.ttl", format="turtle")
