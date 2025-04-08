# Wikidata to CIDOC CRM

This repository contains Python scripts that transform structured data from Wikidata into RDF using CIDOC CRM (OWL version, [eCRM](https://erlangen-crm.org/docs/ecrm/current/)) and related models. To improve inference capabilities, all ECRM classes and properties have been mapped to CIDOC CRM using `owl:sameAs`.

The scripts are developed in the context of the project [Sappho Digital](https://sappho-digital.com/) by [Laura Untner](https://orcid.org/0000-0002-9649-0870).

The repository is under active development. Currently, only the `authors` module is available. Future modules will also model:

- Works using [LRMoo](https://repository.ifla.org/handle/20.500.14598/3677)
- Textual relations using [INTRO](https://github.com/BOberreither/INTRO)
- Extended ontology alignments

The goal is to enable CIDOC CRM-based semantic enrichment from Wikidata and other linked data sources.

> ⚠️ **Note:** All URIs currently use the `https://sappho.com/` base. Please adapt this to your own environment as needed.  
> 💡 **Reuse is encouraged**. The scripts are open for reuse. If you use or build on them, a reference to the Sappho Digital project would be appreciated.

---

## Authors Module

The `authors.py` script reads a list of Wikidata QIDs from a CSV file and creates RDF triples using CIDOC CRM (eCRM). It models:

- `E21_Person` with:
  - `E82_Actor_Appellation` (names)
  - `E42_Identifier` (Wikidata QIDs)
  - `E67_Birth` and `E69_Death` events, linked to:
    - `E53_Place` (birth/death places)
    - `E52_Time-Span` (birth/death dates)
  - `E55_Type` (gender)
  - `E36_Visual_Item` (visual representation)
  - `E38_Image` (image reference with Wikimedia `seeAlso`)

As you can see, the script currently models only basic information but can be dynamically extended.

The script also uses `PROV-O` (`prov:wasDerivedFrom`) to link data back to Wikidata.

📎 A [visual documentation](https://github.com/laurauntner/wikidata-to-cidoc-crm/blob/main/authors/authors.png) of the authors data model is included in the `authors` folder.

### Requirements

Install dependencies with:

```
pip install rdflib requests tqdm
```

### Example Input
```
qid
Q469571
```
(This is [Anna Louisa Karsch](https://www.wikidata.org/wiki/Q469571).)

### Example Output

```
@prefix crm: <http://www.cidoc-crm.org/cidoc-crm/> .
@prefix ecrm: <http://erlangen-crm.org/current/> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix prov: <http://www.w3.org/ns/prov#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

<https://sappho.com/person/Q469571> a ecrm:E21_Person ;
    rdfs:label "Anna Louisa Karsch"@en ;
    ecrm:P131_is_identified_by <https://sappho.com/appellation/Q469571> ;
    ecrm:P1_is_identified_by <https://sappho.com/identifier/Q469571> ;
    ecrm:P98i_was_born <https://sappho.com/birth/Q469571> ;
    ecrm:P100i_died_in <https://sappho.com/death/Q469571> ;
    ecrm:P2_has_type <https://sappho.com/gender/Q6581072> ;
    owl:sameAs <http://www.wikidata.org/entity/Q469571> .

<https://sappho.com/appellation/Q469571> a ecrm:E82_Actor_Appellation ;
    rdfs:label "Anna Louisa Karsch"@en ;
    prov:wasDerivedFrom <http://www.wikidata.org/entity/Q469571> .

<https://sappho.com/identifier/Q469571> a ecrm:E42_Identifier ;
    rdfs:label "Q469571" ;
    ecrm:P2_has_type <https://sappho.com/id_type/wikidata> .

<https://sappho.com/id_type/wikidata> a ecrm:E55_Type ;
    rdfs:label "Wikidata ID"@en .

<https://sappho.com/birth/Q469571> a ecrm:E67_Birth ;
    rdfs:label "Birth of Anna Louisa Karsch"@en ;
    ecrm:P4_has_time-span <https://sappho.com/timespan/17221201> ;
    ecrm:P7_took_place_at <https://sappho.com/place/Q659063> ;
    prov:wasDerivedFrom <http://www.wikidata.org/entity/Q469571> .

<https://sappho.com/death/Q469571> a ecrm:E69_Death ;
    rdfs:label "Death of Anna Louisa Karsch"@en ;
    ecrm:P4_has_time-span <https://sappho.com/timespan/17911012> ;
    ecrm:P7_took_place_at <https://sappho.com/place/Q64> ;
    prov:wasDerivedFrom <http://www.wikidata.org/entity/Q469571> .

<https://sappho.com/place/Q64> a ecrm:E53_Place ;
    rdfs:label "Berlin"@en ;
    owl:sameAs <http://www.wikidata.org/entity/Q64> .

<https://sappho.com/place/Q659063> a ecrm:E53_Place ;
    rdfs:label "Skąpe"@en ;
    owl:sameAs <http://www.wikidata.org/entity/Q659063> .

<https://sappho.com/timespan/17221201> a ecrm:E52_Time-Span ;
    rdfs:label "1722-12-01"^^xsd:date .

<https://sappho.com/timespan/17911012> a ecrm:E52_Time-Span ;
    rdfs:label "1791-10-12"^^xsd:date .

<https://sappho.com/gender/Q6581072> a ecrm:E55_Type ;
    rdfs:label "female"@en ;
    ecrm:P2_has_type <https://sappho.com/gender_type/wikidata> ;
    owl:sameAs <http://www.wikidata.org/entity/Q6581072> .

<https://sappho.com/gender_type/wikidata> a ecrm:E55_Type ;
    rdfs:label "Wikidata Gender"@en .

<https://sappho.com/image/Q469571> a ecrm:E38_Image ;
    ecrm:P65_shows_visual_item <https://sappho.com/visual_item/Q469571> ;
    rdfs:seeAlso <http://commons.wikimedia.org/wiki/Special:FilePath/Karschin%20bild.JPG> ;
    prov:wasDerivedFrom <http://www.wikidata.org/entity/Q469571> .

<https://sappho.com/visual_item/Q469571> a ecrm:E36_Visual_Item ;
    rdfs:label "Visual representation of Anna Louisa Karsch"@en ;
    ecrm:P138_represents <https://sappho.com/person/Q469571> .

ecrm:E21_Person owl:sameAs crm:E21_Person .
ecrm:E67_Birth owl:sameAs crm:E67_Birth .
ecrm:E69_Death owl:sameAs crm:E69_Death .
ecrm:E52_Time-Span owl:sameAs crm:E52_Time-Span .
ecrm:E53_Place owl:sameAs crm:E53_Place .
ecrm:E36_Visual_Item owl:sameAs crm:E36_Visual_Item .
ecrm:E38_Image owl:sameAs crm:E38_Image .
ecrm:E55_Type owl:sameAs crm:E55_Type .
ecrm:E42_Identifier owl:sameAs crm:E42_Identifier .
ecrm:E82_Actor_Appellation owl:sameAs crm:E82_Actor_Appellation .

ecrm:P1_is_identified_by owl:inverseOf ecrm:P1i_identifies ;
    owl:sameAs crm:P1_is_identified_by .
ecrm:P2_has_type owl:inverseOf ecrm:P2i_is_type_of ;
    owl:sameAs crm:P2_has_type .
ecrm:P4_has_time-span owl:inverseOf ecrm:P4i_is_time-span_of ;
    owl:sameAs crm:P4_has_time-span .
ecrm:P7_took_place_at owl:inverseOf ecrm:P7i witnessed ;
    owl:sameAs crm:P7_took_place_at .
ecrm:P65_shows_visual_item owl:inverseOf ecrm:P65i_is_shown_by ;
    owl:sameAs crm:P65_shows_visual_item .
ecrm:P65i_is_shown_by owl:inverseOf ecrm:P65_shows_visual_item ;
    owl:sameAs crm:P65i_is_shown_by .
ecrm:P98_brought_into_life owl:inverseOf ecrm:P98i_was_born ;
    owl:sameAs crm:P98_brought_into_life .
ecrm:P100_was_death_of owl:inverseOf ecrm:P100i_died_in ;
    owl:sameAs crm:P100_was_death_of .
ecrm:P131_is_identified_by owl:inverseOf ecrm:P131i_identifies ;
    owl:sameAs crm:P131_is_identified_by .
ecrm:P138_represents owl:inverseOf ecrm:P138i_has_representation ;
    owl:sameAs crm:P138_represents .

```
