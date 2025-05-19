"""
This script merges ../authors/authors.ttl, ../works/works.ttl and ../relations/relations.ttl 
without duplications.

The output is serialized as Turtle and written to 'all.ttl'.

"""

from rdflib import Graph, Namespace, RDF, RDFS, OWL, URIRef
from collections import defaultdict

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
prov_uri = URIRef("http://www.w3.org/ns/prov#")

# Load Graphs
g_authors = Graph().parse("../authors/authors.ttl", format="turtle")
g_works = Graph().parse("../works/works.ttl", format="turtle")
g_relations = Graph().parse("../relations/relations.ttl", format="turtle")

# Merge Graphs
g_all = Graph()
for g in [g_authors, g_works, g_relations]:
    g_all += g

# Cleanup duplicate rdfs:label
label_map = defaultdict(list)
for s, p, o in g_all.triples((None, RDFS.label, None)):
    label_map[s].append(o)

multi_label_subjects = {s for s, labels in label_map.items() if len(labels) > 1}

cleaned_graph = Graph()
for s, p, o in g_all:
    if p == RDFS.label and s in multi_label_subjects:
        labels = label_map[s]
        with_lang = [lbl for lbl in labels if lbl.language]
        keep = with_lang[0] if with_lang else labels[0]
        if o == keep:
            cleaned_graph.add((s, p, o))
    else:
        cleaned_graph.add((s, p, o))

# Cleanup owl:Ontology
for s, p, o in list(cleaned_graph.triples((None, RDF.type, OWL.Ontology))):
    cleaned_graph.remove((s, None, None))

ontology_uri = URIRef("https://sappho-digital.com/ontology/all")
cleaned_graph.add((ontology_uri, RDF.type, OWL.Ontology))
cleaned_graph.add((ontology_uri, OWL.imports, ecrm_uri))
cleaned_graph.add((ontology_uri, OWL.imports, lrmoo_uri))
cleaned_graph.add((ontology_uri, OWL.imports, intro_uri))
cleaned_graph.add((ontology_uri, OWL.imports, prov_uri))

# Bind Namespaces
cleaned_graph.bind("sappho", sappho)
cleaned_graph.bind("ecrm", ecrm)
cleaned_graph.bind("crm", crm)
cleaned_graph.bind("lrmoo", lrmoo)
cleaned_graph.bind("frbroo", frbroo)
cleaned_graph.bind("efrbroo", efrbroo)
cleaned_graph.bind("intro", intro)
cleaned_graph.bind("prov", prov)

# Serialize
cleaned_graph.serialize(destination="all.ttl", format="turtle")
