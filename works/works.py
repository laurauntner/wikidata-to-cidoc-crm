"""
This script retrieves bibliographic data from Wikidata based on a list of QIDs (from a CSV file)
and transforms it into RDF triples according to LRMoo/FRBRoo and CIDOC CRM (OWL/eCRM).

The output is serialized as Turtle and written to 'works.ttl'.

"""

import csv
import time
import requests
from rdflib import Graph, Literal, RDF, RDFS, Namespace, URIRef
from rdflib.namespace import RDF, RDFS, OWL, XSD
from tqdm import tqdm

# Namespaces
CRM = Namespace("http://www.cidoc-crm.org/cidoc-crm/") # CIDOC CRM
CRM_URI = URIRef("http://www.cidoc-crm.org/cidoc-crm/")
ECRM = Namespace("http://erlangen-crm.org/current/") #eCRM – CIDOC CRM (OWL version)
ECRM_URI = URIRef("http://erlangen-crm.org/current/")
LRMOO = Namespace("http://iflastandards.info/ns/lrm/lrmoo/") # LRMoo
LRMOO_URI = URIRef("http://iflastandards.info/ns/lrm/lrmoo/")
FRBROO = Namespace("http://iflastandards.info/ns/fr/frbr/frbroo/") # FRBRoo
FRBROO_URI = URIRef("http://iflastandards.info/ns/fr/frbr/frbroo/")
EFRBROO = Namespace("http://erlangen-crm.org/efrbroo/") # eFRBRoo
EFRBROO_URI = URIRef("http://erlangen-crm.org/efrbroo/")
PROV = Namespace("http://www.w3.org/ns/prov#") # PROV-O - Provenance Ontology
PROV_URI = URIRef("http://www.w3.org/ns/prov#")
WD = "http://www.wikidata.org/entity/" # Base URI for Wikidata entities
SAPPHO_BASE_URI = Namespace("https://sappho-digital.com/")

# Create the RDF Graph
g = Graph()
g.bind("crm", CRM)
g.bind("ecrm", ECRM)
g.bind("lrmoo", LRMOO)
g.bind("frbroo", FRBROO)
g.bind("efrbroo", EFRBROO)
g.bind("prov", PROV)
g.bind("owl", OWL)
g.bind("rdfs", RDFS)
g.bind("sappho", SAPPHO_BASE_URI)

# Ontology

ontology_uri = URIRef("https://sappho-digital.com/ontology/works")

g.add((ontology_uri, RDF.type, OWL.Ontology))

g.add((ontology_uri, OWL.imports, CRM_URI))
g.add((ontology_uri, OWL.imports, ECRM_URI))
g.add((ontology_uri, OWL.imports, LRMOO_URI))
g.add((ontology_uri, OWL.imports, FRBROO_URI))
g.add((ontology_uri, OWL.imports, EFRBROO_URI))
g.add((ontology_uri, OWL.imports, PROV_URI))

# Ontology Alignments (ECRM - CRM, LRMoo - FRBRoo/eFRBRoo) and property inverses

ecrm_to_crm = [
    # Classes
    ("E21_Person",),
    ("E35_Title",),
    ("E42_Identifier",),
    ("E52_Time-Span",),
    ("E53_Place",),
    ("E55_Type",),
    ("E62_String",),
    ("E73_Information_Object",),
    ("E82_Actor_Appellation",),
    ("E40_Legal_Body",),
]

for cls in ecrm_to_crm:
    g.add((ECRM.term(cls[0]), OWL.equivalentClass, CRM.term(cls[0])))

# Properties
ecrm_properties = [
    ("P1_is_identified_by", "P1i_identifies"),
    ("P2_has_type", "P2i_is_type_of"),
    ("P4_has_time-span", "P4i_is_time-span_of"),
    ("P7_took_place_at", "P7i_witnessed"),
    ("P14_carried_out_by", "P14i_performed"),
    ("P102_has_title", "P102i_is_title_of"),
    ("P131_is_identified_by", "P131i_identifies"),
    ("P138_represents", "P138i_has_representation"),
    ("P190_has_symbolic_content", "P190i_is_content_of")
]

for direct, inverse in ecrm_properties:
    g.add((ECRM.term(direct), OWL.inverseOf, ECRM.term(inverse)))
    g.add((ECRM.term(direct), OWL.equivalentProperty, CRM.term(direct)))
    g.add((ECRM.term(inverse), OWL.inverseOf, ECRM.term(direct)))
    g.add((ECRM.term(inverse), OWL.equivalentProperty, CRM.term(inverse)))

lrmoo_to_frbroo = {
    "F1_Work": "F1_Work",
    "F2_Expression": "F2_Expression",
    "F3_Manifestation": "F3_Manifestation_Product_Type",
    "F5_Item": "F5_Item",
    "F27_Work_Creation": "F27_Work_Conception",
    "F28_Expression_Creation": "F28_Expression_Creation",
    "F30_Manifestation_Creation": "F30_Publication_Event",
    "F32_Item_Production_Event": "F32_Carrier_Production_Event"
}
for lr, fr in lrmoo_to_frbroo.items():
    g.add((LRMOO.term(lr), OWL.equivalentClass, FRBROO.term(fr)))
    g.add((LRMOO.term(lr), OWL.equivalentClass, EFRBROO.term(fr)))

lrmoo_properties = [
    ("R3_is_realised_in", "R3i_realises", "R3_is_realised_in", "R3i_realises"),
    ("R4_embodies", "R4i_is_embodied_in", "R4i_comprises_carriers_of", "R4_carriers_provided_by"),
    ("R7_exemplifies", "R7i_is_exemplified_by", "R7_is_example_of", "R7i_has_example"),
    ("R16_created", "R16i_was_created_by", "R16_initiated", "R16i_was_initiated_by"),
    ("R17_created", "R17i_was_created_by", "R17_created", "R17i_was_created_by"),
    ("R19_created_a_realisation_of", "R19i_was_realised_through", "R19_created_a_realisation_of", "R19i_was_realised_through"),
    ("R24_created", "R24i_was_created_through", "R24_created", "R24i_was_created_through"),
    ("R27_materialized", "R27i_was_materialized_by", "R27_used_as_source_material", "R27i_was_used_by"),
    ("R28_produced", "R28i_was_produced_by", "R28_produced", "R28i_was_produced_by"),
]

for lr_direct, lr_inverse, fr_direct, fr_inverse in lrmoo_properties:
    g.add((LRMOO.term(lr_direct), OWL.inverseOf, LRMOO.term(lr_inverse)))
    g.add((LRMOO.term(lr_inverse), OWL.inverseOf, LRMOO.term(lr_direct)))
    g.add((LRMOO.term(lr_direct), OWL.equivalentProperty, FRBROO.term(fr_direct)))
    g.add((LRMOO.term(lr_direct), OWL.equivalentProperty, EFRBROO.term(fr_direct)))
    g.add((LRMOO.term(lr_inverse), OWL.equivalentProperty, FRBROO.term(fr_inverse)))
    g.add((LRMOO.term(lr_inverse), OWL.equivalentProperty, EFRBROO.term(fr_inverse)))

# Caches for deduplication
genre_cache = {}
date_cache = {}
publisher_cache = {}
place_cache = {}

# Load QIDs
qids = []
with open("work-qids.csv") as f:
    for row in csv.reader(f):
        qid = row[0].strip()
        if qid.startswith("Q"):
            qids.append(qid)

# SPARQL Query Function
def query_wikidata(qids, max_retries=5):
    values = " ".join(f"wd:{qid}" for qid in qids)
    query = f"""
    SELECT ?work ?workLabel ?title_de ?title_en ?genre ?genreLabel ?author ?authorLabel ?creation_date (MIN(?raw_pub_date) AS ?pub_date) ?pub_place ?pub_placeLabel ?publisher ?publisherLabel ?digitalCopy ?editor ?editorLabel ?publishedIn ?partOf WHERE {{
    VALUES ?work {{ {values} }}
    OPTIONAL {{ ?work wdt:P1476 ?title_de . FILTER(LANG(?title_de) = 'de') }}
    OPTIONAL {{ ?work wdt:P1476 ?title_en . FILTER(LANG(?title_en) = 'en') }}
    OPTIONAL {{ ?work wdt:P136 ?genre . }}
    OPTIONAL {{ ?work wdt:P50 ?author . }}
    OPTIONAL {{ ?work wdt:P577 ?raw_pub_date . }}
    OPTIONAL {{ ?work wdt:P291 ?pub_place . }}
    OPTIONAL {{ ?work wdt:P123 ?publisher . }}
    OPTIONAL {{ ?work wdt:P953 ?digitalCopy . }}
    OPTIONAL {{ ?work wdt:P98 ?editor . }}
    OPTIONAL {{ ?work wdt:P1433 ?publishedIn . }}
    OPTIONAL {{ ?work wdt:P361 ?partOf . }}
    OPTIONAL {{ {{ ?work wdt:P571 ?creation_date . }} UNION {{ ?work wdt:P2754 ?creation_date . }} }}
    SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en,de" }}
    }}
    GROUP BY ?work ?workLabel ?title_de ?title_en ?genre ?genreLabel ?author ?authorLabel ?creation_date ?pub_place ?pub_placeLabel ?publisher ?publisherLabel ?digitalCopy ?editor ?editorLabel ?publishedIn ?partOf
    """
    headers = {
        "Accept": "application/sparql-results+json",
        "User-Agent": "SapphoWorkIntegrationBot/1.0 (laura.untner@fu-berlin.de)"
    }

    for attempt in range(1, max_retries + 1):
        try:
            r = requests.get("https://query.wikidata.org/sparql", params={"query": query}, headers=headers, timeout=90)
            r.raise_for_status()
            return r.json()["results"]["bindings"]
        except requests.exceptions.RequestException as e:
            wait = 5 * attempt
            print(f"[RETRY {attempt}] SPARQL request failed: {e} – retrying in {wait}s...")
            time.sleep(wait)

    print("[ERROR] Maximum retries reached. Skipping batch.")
    return []

# Helper Functions for titles and years
def label_for(title_de, title_en, work_label):
    if title_de:
        return title_de, "de"
    elif title_en:
        return title_en, "en"
    elif work_label:
        return work_label, "de"
    else:
        return "Untitled", "en"

def manifestation_label_for(r):
    if "publishedInLabel" in r:
        return r["publishedInLabel"]["value"], "de"
    elif "partOfLabel" in r:
        return r["partOfLabel"]["value"], "de"
    elif "publishedIn" in r:
        parent_qid = r["publishedIn"]["value"].split("/")[-1]
        return fetch_label(parent_qid)
    elif "partOf" in r:
        parent_qid = r["partOf"]["value"].split("/")[-1]
        return fetch_label(parent_qid)
    else:
        return None, None

def extract_year(date_str):
    return date_str[:4] if date_str else None

def fetch_label(qid):
    query = f"""
    SELECT ?label_de ?label_en WHERE {{
      wd:{qid} rdfs:label ?label_de . FILTER(LANG(?label_de) = "de")
      OPTIONAL {{ wd:{qid} rdfs:label ?label_en . FILTER(LANG(?label_en) = "en") }}
    }}
    """
    headers = {
        "Accept": "application/sparql-results+json",
        "User-Agent": "SapphoWorkIntegrationBot/1.0 (contact@example.com)"
    }
    try:
        r = requests.get("https://query.wikidata.org/sparql", params={"query": query}, headers=headers, timeout=30)
        r.raise_for_status()
        results = r.json()["results"]["bindings"]
        if results:
            label_de = results[0].get("label_de", {}).get("value")
            label_en = results[0].get("label_en", {}).get("value")
            if label_de:
                return label_de, "de"
            elif label_en:
                return label_en, "en"
    except Exception as e:
        print(f"[WARN] Could not fetch label for {qid}: {e}")
    return "Untitled", "en"

# Process in Batches
for i in tqdm(range(0, len(qids), 20)):
    batch = qids[i:i+20]
    results = query_wikidata(batch)
    for r in results:
        # Triple Creation
        qid = r["work"]["value"].split("/")[-1]
        work_uri = URIRef(f"{SAPPHO_BASE_URI}work/{qid}")
        expression_uri = URIRef(f"{SAPPHO_BASE_URI}expression/{qid}")
        label, lang = label_for(
            r.get("title_de", {}).get("value"),
            r.get("title_en", {}).get("value"),
            r.get("workLabel", {}).get("value")
        )
        title_uri = URIRef(f"{SAPPHO_BASE_URI}title/expression/{qid}")
        title_string_uri = URIRef(f"{SAPPHO_BASE_URI}title_string/expression/{qid}")

        g.add((work_uri, RDF.type, LRMOO.F1_Work))
        g.add((work_uri, RDFS.label, Literal(f"Work of {label}", lang="en")))
        g.add((work_uri, LRMOO.R3_is_realised_in, expression_uri))

        # Work Creation
        work_creation_uri = URIRef(f"{SAPPHO_BASE_URI}work_creation/{qid}")
        g.add((work_creation_uri, RDF.type, LRMOO.F27_Work_Creation))
        g.add((work_creation_uri, RDFS.label, Literal(f"Work creation of {label}", lang="en")))
        g.add((work_creation_uri, LRMOO.R16_created, work_uri))
        g.add((work_creation_uri, PROV.wasDerivedFrom, URIRef(f"{WD}{qid}")))

        if "author" in r:
            author_qid = r["author"]["value"].split("/")[-1]
            author_uri = URIRef(f"{SAPPHO_BASE_URI}person/{author_qid}")
            g.add((work_creation_uri, ECRM.P14_carried_out_by, author_uri))
            g.add((work_uri, ECRM.P14_carried_out_by, author_uri))
            
            g.add((author_uri, RDF.type, ECRM.E21_Person))
            g.add((author_uri, RDFS.label, Literal(r.get("authorLabel", {}).get("value", "Unknown"))))
            g.add((author_uri, OWL.sameAs, URIRef(r["author"]["value"])))

        # Expression
        g.add((expression_uri, RDF.type, LRMOO.F2_Expression))
        g.add((expression_uri, RDFS.label, Literal(f"Expression of {label}", lang="en")))                
        identifier_uri = URIRef(f"{SAPPHO_BASE_URI}identifier/{qid}")
        g.add((expression_uri, ECRM.P1_is_identified_by, identifier_uri))
        g.add((identifier_uri, RDF.type, ECRM.E42_Identifier))
        g.add((identifier_uri, RDFS.label, Literal(qid)))
        g.add((identifier_uri, ECRM.P2_has_type, URIRef("https://sappho-digital.com/id_type/wikidata")))
        
        wikidata_id_type_uri = URIRef("https://sappho-digital.com/id_type/wikidata")
        g.add((wikidata_id_type_uri, RDF.type, ECRM.E55_Type))
        g.add((wikidata_id_type_uri, RDFS.label, Literal("Wikidata ID", lang="en")))
        g.add((wikidata_id_type_uri, OWL.sameAs, URIRef("https://www.wikidata.org/wiki/Q43649390")))
        g.add((expression_uri, ECRM.P102_has_title, title_uri))
        g.add((title_uri, RDF.type, ECRM.E35_Title))
        g.add((title_uri, ECRM.P190_has_symbolic_content, title_string_uri))
        g.add((title_string_uri, RDF.type, ECRM.E62_String))
        g.add((title_string_uri, RDFS.label, Literal(label, lang=lang)))

        if "genre" in r:
            genre_qid = r["genre"]["value"].split("/")[-1]
            if genre_qid not in genre_cache:
                genre_uri = URIRef(f"{SAPPHO_BASE_URI}genre/{genre_qid}")
                genre_cache[genre_qid] = genre_uri
                g.add((genre_uri, RDF.type, ECRM.E55_Type))
                g.add((genre_uri, RDFS.label, Literal(r.get("genreLabel", {}).get("value", "Unknown"), lang="en")))
                g.add((genre_uri, OWL.sameAs, URIRef(r["genre"]["value"])))
                g.add((genre_uri, ECRM.P2_has_type, URIRef(f"{SAPPHO_BASE_URI}genre_type/wikidata")))
                g.add((URIRef(f"{SAPPHO_BASE_URI}genre_type/wikidata"), RDF.type, ECRM.E55_Type))
                g.add((URIRef(f"{SAPPHO_BASE_URI}genre_type/wikidata"), RDFS.label, Literal("Wikidata Genre", lang="en")))
            g.add((expression_uri, ECRM.P2_has_type, genre_cache[genre_qid]))

        g.add((expression_uri, OWL.sameAs, URIRef(f"{WD}{qid}")))
        g.add((expression_uri, PROV.wasDerivedFrom, URIRef(f"{WD}{qid}")))

        # Expression Creation
        expression_creation_uri = URIRef(f"{SAPPHO_BASE_URI}expression_creation/{qid}")
        g.add((expression_creation_uri, RDF.type, LRMOO.F28_Expression_Creation))
        g.add((expression_creation_uri, RDFS.label, Literal(f"Expression creation of {label}", lang="en")))
        g.add((expression_creation_uri, LRMOO.R17_created, expression_uri))
        g.add((expression_creation_uri, LRMOO.R19_created_a_realisation_of, work_uri))
        g.add((expression_creation_uri, PROV.wasDerivedFrom, URIRef(f"{WD}{qid}")))

        if "author" in r:
            g.add((expression_creation_uri, ECRM.P14_carried_out_by, author_uri))

        if "creation_date" in r:
            year = extract_year(r["creation_date"]["value"])
            if year:
                if year not in date_cache:
                    date_uri = URIRef(f"{SAPPHO_BASE_URI}timespan/{year}")
                    date_cache[year] = date_uri
                    g.add((date_uri, RDF.type, ECRM["E52_Time-Span"]))
                    g.add((date_uri, RDFS.label, Literal(year, datatype=XSD.gYear)))
                g.add((expression_creation_uri, ECRM["P4_has_time-span"], date_cache[year]))

        # Manifestation
        manifestation_uri = URIRef(f"{SAPPHO_BASE_URI}manifestation/{qid}")
        g.add((manifestation_uri, RDF.type, LRMOO.F3_Manifestation))
        g.add((manifestation_uri, RDFS.label, Literal(f"Manifestation of {label}", lang="en")))
        g.add((manifestation_uri, LRMOO.R4_embodies, expression_uri))
        
        manifestation_title_uri = URIRef(f"{SAPPHO_BASE_URI}title/manifestation/{qid}")
        manifestation_title_string_uri = URIRef(f"{SAPPHO_BASE_URI}title_string/manifestation/{qid}")
        
        manifestation_label, manifestation_lang = manifestation_label_for(r)
        if manifestation_label is None:
            manifestation_label = label
            manifestation_lang = lang
        
        if "publishedIn" in r:
            parent_qid = r["publishedIn"]["value"].split("/")[-1]
            manifestation_label, manifestation_lang = fetch_label(parent_qid)
        elif "partOf" in r:
            parent_qid = r["partOf"]["value"].split("/")[-1]
            manifestation_label, manifestation_lang = fetch_label(parent_qid)

        g.add((manifestation_uri, ECRM.P102_has_title, manifestation_title_uri))
        g.add((manifestation_title_uri, RDF.type, ECRM.E35_Title))
        g.add((manifestation_title_uri, ECRM.P190_has_symbolic_content, manifestation_title_string_uri))
        g.add((manifestation_title_string_uri, RDF.type, ECRM.E62_String))
        g.add((manifestation_title_string_uri, RDFS.label, Literal(manifestation_label, lang=manifestation_lang)))

        # Manifestation Creation
        manifestation_creation_uri = URIRef(f"{SAPPHO_BASE_URI}manifestation_creation/{qid}")
        g.add((manifestation_creation_uri, RDF.type, LRMOO.F30_Manifestation_Creation))
        g.add((manifestation_creation_uri, RDFS.label, Literal(f"Manifestation creation of {label}", lang="en")))
        g.add((manifestation_creation_uri, LRMOO.R24_created, manifestation_uri))
        g.add((manifestation_creation_uri, PROV.wasDerivedFrom, URIRef(f"{WD}{qid}")))
        if "author" in r:
            g.add((manifestation_creation_uri, ECRM.P14_carried_out_by, author_uri))

        if "publisher" in r:
            publisher_qid = r["publisher"]["value"].split("/")[-1]
            if publisher_qid not in publisher_cache:
                publisher_uri = URIRef(f"{SAPPHO_BASE_URI}publisher/{publisher_qid}")
                publisher_cache[publisher_qid] = publisher_uri
                g.add((publisher_uri, RDF.type, ECRM.E40_Legal_Body))
                g.add((publisher_uri, RDFS.label, Literal(r.get("publisherLabel", {}).get("value", "Unknown"), lang="en")))
                g.add((publisher_uri, OWL.sameAs, URIRef(r["publisher"]["value"])))
            g.add((manifestation_creation_uri, ECRM.P14_carried_out_by, publisher_cache[publisher_qid]))

        if "pub_date" in r:
            pub_year = extract_year(r["pub_date"]["value"])
            if pub_year:
                if pub_year not in date_cache:
                    pub_date_uri = URIRef(f"{SAPPHO_BASE_URI}timespan/{pub_year}")
                    date_cache[pub_year] = pub_date_uri
                    g.add((pub_date_uri, RDF.type, ECRM["E52_Time-Span"]))
                    g.add((pub_date_uri, RDFS.label, Literal(pub_year, datatype=XSD.gYear)))
                g.add((manifestation_creation_uri, ECRM["P4_has_time-span"], date_cache[pub_year]))

        if "pub_place" in r:
            place_qid = r["pub_place"]["value"].split("/")[-1]
            if place_qid not in place_cache:
                place_uri = URIRef(f"{SAPPHO_BASE_URI}place/{place_qid}")
                place_cache[place_qid] = place_uri
                g.add((place_uri, RDF.type, ECRM.E53_Place))
                g.add((place_uri, RDFS.label, Literal(r.get("pub_placeLabel", {}).get("value", "Unknown"), lang="en")))
                g.add((place_uri, OWL.sameAs, URIRef(r["pub_place"]["value"])))
            g.add((manifestation_creation_uri, ECRM.P7_took_place_at, place_cache[place_qid]))

        if "editor" in r:
            editor_qid = r["editor"]["value"].split("/")[-1]
            editor_uri = URIRef(f"{SAPPHO_BASE_URI}editor/{editor_qid}")
            g.add((editor_uri, RDF.type, ECRM.E21_Person))
            g.add((editor_uri, RDFS.label, Literal(r.get("editorLabel", {}).get("value", "Unknown"))))
            g.add((editor_uri, OWL.sameAs, URIRef(r["editor"]["value"])))

            app_uri = URIRef(f"{SAPPHO_BASE_URI}appellation/{editor_qid}")
            g.add((editor_uri, ECRM.P131_is_identified_by, app_uri))
            g.add((app_uri, RDF.type, ECRM.E82_Actor_Appellation))
            g.add((app_uri, RDFS.label, Literal(r.get("editorLabel", {}).get("value", "Unknown"))))
            g.add((app_uri, PROV.wasDerivedFrom, URIRef(r["editor"]["value"])))

            id_uri = URIRef(f"{SAPPHO_BASE_URI}identifier/{editor_qid}")
            g.add((editor_uri, ECRM.P1_is_identified_by, id_uri))
            g.add((id_uri, RDF.type, ECRM.E42_Identifier))
            g.add((id_uri, RDFS.label, Literal(editor_qid)))
            g.add((id_uri, ECRM.P2_has_type, URIRef("https://sappho-digital.com/id_type/wikidata")))
            g.add((manifestation_creation_uri, ECRM.P14_carried_out_by, editor_uri))

        item_production_uri = URIRef(f"{SAPPHO_BASE_URI}item_production/{qid}")
        item_uri = URIRef(f"{SAPPHO_BASE_URI}item/{qid}")

        g.add((item_production_uri, RDF.type, LRMOO.F32_Item_Production_Event))
        g.add((item_production_uri, RDFS.label, Literal(f"Item production event of {label}", lang="en")))
        g.add((item_production_uri, LRMOO.R27_materialized, manifestation_uri))
        g.add((item_production_uri, LRMOO.R28_produced, item_uri))

        g.add((item_uri, RDF.type, LRMOO.F5_Item))
        g.add((item_uri, RDFS.label, Literal(f"Item of {label}", lang="en")))
        g.add((item_uri, LRMOO.R7_exemplifies, manifestation_uri))

        if "digitalCopy" in r:
            digital_uri = URIRef(f"{SAPPHO_BASE_URI}digital/{qid}")
            g.add((digital_uri, RDF.type, ECRM.E73_Information_Object))
            g.add((digital_uri, RDFS.label, Literal(f"Digital copy of {label}", lang="en")))
            g.add((digital_uri, ECRM.P138_represents, expression_uri))
            g.add((digital_uri, RDFS.seeAlso, URIRef(r["digitalCopy"]["value"])))

# Serialize
g.serialize("works.ttl", format="turtle")
