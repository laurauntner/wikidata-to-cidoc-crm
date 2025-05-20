# Wikidata to CIDOC CRM

This repository contains Python scripts that transform structured data from [Wikidata](https://www.wikidata.org/) into RDF using [CIDOC CRM](https://cidoc-crm.org/) (OWL version, [eCRM](https://erlangen-crm.org/docs/ecrm/current/)) and models based on CIDOC CRM: [LRMoo](https://repository.ifla.org/handle/20.500.14598/3677) and [INTRO](https://github.com/BOberreither/INTRO). The scripts generate—depending on the module—an ontology (`owl:Ontology`) for authors, works, or intertexts.

The goal is to enable CIDOC CRM-based semantic enrichment from Wikidata and other linked data sources. The scripts also use [PROV-O](https://www.w3.org/TR/prov-o/) (`prov:wasDerivedFrom`) to link data back to Wikidata.

To improve inference capabilities, all ECRM classes and properties have been mapped to CIDOC CRM using `owl:equivalentClass` and `owl:equivalentProperty`. Also, all LRMoo classes and properties have been mapped to [FRBRoo](https://www.iflastandards.info/fr/frbr/frbroo) and [eFRBRoo](https://erlangen-crm.org/efrbroo).

---

🚧 The repository is under active development. Currently, the `authors`, `works`, `relations`, `merge` and `map-and-align` modules are available. The first three modules model basic biographical, bibliographical, and intertextual information based on data from Wikidata and can be dynamically extended. 

The `merge` module can be used to merge the outputted Turtle files. 

The `map-and-align` module looks for more identifiers from [Schema.org](https://schema.org/), [DBpedia](https://www.dbpedia.org/), [GND](https://www.dnb.de/DE/Professionell/Standardisierung/GND/gnd_node.html), [VIAF](https://viaf.org/), [GeoNames](http://www.geonames.org/) and [Goodreads](https://www.goodreads.com/) and adds more ontology alignments mainly using [SKOS](http://www.w3.org/2004/02/skos/core#). 

The aligned ontologies are: [BIBO](http://purl.org/ontology/bibo/), [CiTO](http://purl.org/spar/cito/), [DC](http://purl.org/dc/terms/), [DoCo](http://purl.org/spar/doco/), [DraCor](http://dracor.org/ontology#), [FaBiO](http://purl.org/spar/fabio/), [FOAF](http://xmlns.com/foaf/0.1/), [FRBRoo](https://www.iflastandards.info/fr/frbr/frbroo), [GOLEM](https://ontology.golemlab.eu/), [Intertextuality Ontology](https://github.com/intertextor/intertextuality-ontology), [MiMoText](https://data.mimotext.uni-trier.de/wiki/Main_Page) and [POSTDATA / OntoPoetry](https://postdata.linhd.uned.es/results/ontopoetry-v2-0/)). 

The mapping and alignment are done separately so that the script can hopefully be more easily updated. It focuses specifically on those classes and properties that are important for the relations module.

📌 **Still to do:**
- SHACL Shapes
- Python package for better reuse

---

- 🪄 **Reality check**: These scripts are not magical. Data that is not available in Wikidata cannot appear in the triples.
- ⚠️ **Base URI:** All URIs currently use the `https://sappho-digital.com/` base. Please adapt this to your own environment as needed.
- 💡 **Reuse is encouraged**. The scripts are open for reuse. They are developed in the context of the project [Sappho Digital](https://sappho-digital.com/) by [Laura Untner](https://orcid.org/0000-0002-9649-0870). A reference to the project would be appreciated if you use or build on the scripts.

---

## Requirements

Install dependencies with:

```
pip install rdflib requests tqdm
```

---

<details>
<summary><h2>✍️ Authors Module (e/CRM)</h2></summary>
  
The [authors.py](https://github.com/laurauntner/wikidata-to-cidoc-crm/blob/main/authors/authors.py) script reads a list of Wikidata QIDs for authors from a CSV file and creates RDF triples using CIDOC CRM (eCRM, mapped to CRM). It models:

- `E21_Person` with:
  - `E82_Actor_Appellation` (names, derived from labels)
  - `E42_Identifier` (Wikidata QIDs, derived from given QIDs)
  - `E67_Birth` and `E69_Death` events, linked to:
    - `E53_Place` (birth places, derived from `wdt:P19`, and death places, derived from `wdt:P20`)
    - `E52_Time-Span` (birth dates, derived from `wdt:P569`, and death dates, derived from `wdt:P570`)
  - `E55_Type` (genders, derived from `wdt:P21`)
  - `E36_Visual_Item` (visual representations) and `E38_Image` (image reference with Wikimedia `seeAlso`, derived from `wdt:P18`)

📎 A [visual documentation](https://github.com/laurauntner/wikidata-to-cidoc-crm/blob/main/authors/authors.png) of the authors data model is included in the `authors` folder.
    
<h3>Example Input</h3>

```csv
qid
Q469571
```

This is [Anna Louisa Karsch](https://www.wikidata.org/wiki/Q469571).

<h3>Example Output</h3>

Namespace declarations and mappings to CRM are applied but not shown in this exemplary output.

```turtle
<https://sappho-digital.com/person/Q469571> a ecrm:E21_Person ;
    rdfs:label "Anna Louisa Karsch"@en ;
    ecrm:P100i_died_in <https://sappho-digital.com/death/Q469571> ;
    ecrm:P131_is_identified_by <https://sappho-digital.com/appellation/Q469571> ;
    ecrm:P138i_has_representation <https://sappho-digital.com/visual_item/Q469571> ;
    ecrm:P1_is_identified_by <https://sappho-digital.com/identifier/Q469571> ;
    ecrm:P2_has_type <https://sappho-digital.com/gender/Q6581072> ;
    ecrm:P98i_was_born <https://sappho-digital.com/birth/Q469571> ;
    owl:sameAs <http://www.wikidata.org/entity/Q469571> .

<https://sappho-digital.com/appellation/Q469571> a ecrm:E82_Actor_Appellation ;
    rdfs:label "Anna Louisa Karsch"@en ;
    ecrm:P131i_identifies <https://sappho-digital.com/person/Q469571> ;
    prov:wasDerivedFrom <http://www.wikidata.org/entity/Q469571> .

<https://sappho-digital.com/identifier/Q469571> a ecrm:E42_Identifier ;
    rdfs:label "Q469571" ;
    ecrm:P1i_identifies <https://sappho-digital.com/person/Q469571> ;
    ecrm:P2_has_type <https://sappho-digital.com/id_type/wikidata> .

<https://sappho-digital.com/id_type/wikidata> a ecrm:E55_Type ;
    rdfs:label "Wikidata ID"@en ;
    ecrm:P2i_is_type_of <https://sappho-digital.com/identifier/Q469571> .

<https://sappho-digital.com/birth/Q469571> a ecrm:E67_Birth ;
    rdfs:label "Birth of Anna Louisa Karsch"@en ;
    ecrm:P4_has_time-span <https://sappho-digital.com/timespan/17221201> ;
    ecrm:P7_took_place_at <https://sappho-digital.com/place/Q659063> ;
    ecrm:P98_brought_into_life <https://sappho-digital.com/person/Q469571> ;
    prov:wasDerivedFrom <http://www.wikidata.org/entity/Q469571> .

<https://sappho-digital.com/death/Q469571> a ecrm:E69_Death ;
    rdfs:label "Death of Anna Louisa Karsch"@en ;
    ecrm:P100_was_death_of <https://sappho-digital.com/person/Q469571> ;
    ecrm:P4_has_time-span <https://sappho-digital.com/timespan/17911012> ;
    ecrm:P7_took_place_at <https://sappho-digital.com/place/Q64> ;
    prov:wasDerivedFrom <http://www.wikidata.org/entity/Q469571> .

<https://sappho-digital.com/place/Q64> a ecrm:E53_Place ;
    rdfs:label "Berlin"@en ;
    ecrm:P7i_witnessed <https://sappho-digital.com/birth/Q469571> ;
    owl:sameAs <http://www.wikidata.org/entity/Q64> .

<https://sappho-digital.com/place/Q659063> a ecrm:E53_Place ;
    rdfs:label "Gmina Skąpe"@en ;
    ecrm:P7i_witnessed <https://sappho-digital.com/death/Q469571> ;
    owl:sameAs <http://www.wikidata.org/entity/Q659063> .

<https://sappho-digital.com/timespan/17221201> a ecrm:E52_Time-Span ;
    rdfs:label "1722-12-01"^^xsd:date ;
    ecrm:P4i_is_time-span_of <https://sappho-digital.com/birth/Q469571> .

<https://sappho-digital.com/timespan/17911012> a ecrm:E52_Time-Span ;
    rdfs:label "1791-10-12"^^xsd:date ;
    ecrm:P4i_is_time-span_of <https://sappho-digital.com/death/Q469571> .

<https://sappho-digital.com/gender/Q6581072> a ecrm:E55_Type ;
    rdfs:label "female"@en ;
    ecrm:P2_has_type <https://sappho-digital.com/gender_type/wikidata> ;
    ecrm:P2i_is_type_of <https://sappho-digital.com/person/Q469571> ;
    owl:sameAs <http://www.wikidata.org/entity/Q6581072> .

<https://sappho-digital.com/gender_type/wikidata> a ecrm:E55_Type ;
    rdfs:label "Wikidata Gender"@en ;
    ecrm:P2i_is_type_of <https://sappho-digital.com/gender/Q6581072> .

<https://sappho-digital.com/image/Q469571> a ecrm:E38_Image ;
    ecrm:P65_shows_visual_item <https://sappho-digital.com/visual_item/Q469571> ;
    rdfs:seeAlso <http://commons.wikimedia.org/wiki/Special:FilePath/Karschin%20bild.JPG> ;
    prov:wasDerivedFrom <http://www.wikidata.org/entity/Q469571> .

<https://sappho-digital.com/visual_item/Q469571> a ecrm:E36_Visual_Item ;
    rdfs:label "Visual representation of Anna Louisa Karsch"@en ;
    ecrm:P138_represents <https://sappho-digital.com/person/Q469571> ;
    ecrm:P65i_is_shown_by <https://sappho-digital.com/image/Q469571> .
```
</details>

---

<details>
<summary><h2>📚 Works Module (LRMoo/FRBRoo)</h2></summary>

The [works.py](https://github.com/laurauntner/wikidata-to-cidoc-crm/blob/main/works/works.py) script reads a list of Wikidata QIDs for works from a CSV file and creates RDF triples using CIDOC CRM (eCRM, mapped to CRM) and LRMoo (mapped to FRBRoo). It models:

- `F1_Work` (abstract works) and `F27_Work_Creation` with:
  - `E21_Person` (authors, derived from `wdt:P50`, see authors module)
- `F2_Expression` (realizations of abstract works) and `F28_Expression_Creation` with:
  - `E52_Time-Span` (creation years, derived from `wdt:P571` or `wdt:P2754`)
  - `E35_Title` and `E62_String` (titles, derived from `wdt:P1476` or labels)
  - `E42_Identifier` (Wikidata QIDs, derived from given QIDs)
  - `E55_Type` (genres, derived from `wdt:P136`)
  - `E73_Information_Object` (digital surrogates, derived from `wdt:P953`)
- `F3_Manifestation` (publications of expressions) and `F30_Manifestation_Creation` with:
  - `E21_Person` (editors, derived from `wdt:P98`) with `E82_Actor_Appellation` (names, derived from labels)
  - `E35_Title` and `E62_String` (titles, only different if the text is part of another text (`wdt:P1433` or `wdt:P361`))
  - `E40_Legal_Body` (publishers, derived from `wdt:P123`)
  - `E52_Time-Span` (publication years, derived from `wdt:P577`)
  - `E53_Place` (publication places, derived from `wdt:P291`)
- `F5_Item` (specific copies of manifestations) and `F32_Item_Production_Event`

Translators are not modeled per default, but the data model can, of course, be extended or adapted accordingly.

📎 A [visual documentation](https://github.com/laurauntner/wikidata-to-cidoc-crm/blob/main/works/works.png) of the works data model is included in the `works` folder.

<h3>Example Input</h3>

```csv
qid
Q1242002
```

(This is the tragedy [Sappho](https://www.wikidata.org/wiki/Q469571) written by Franz Grillparzer.)

<h3>Example Output</h3>

Namespace declarations and mappings to CRM and FRBRoo are applied but not shown in this exemplary output.

```turtle
<https://sappho-digital.com/work_creation/Q1242002> a lrmoo:F27_Work_Creation ;
    rdfs:label "Work creation of Sappho"@en ;
    ecrm:P14_carried_out_by <https://sappho-digital.com/person/Q154438> ;
    lrmoo:R16_created <https://sappho-digital.com/work/Q1242002> ;
    prov:wasDerivedFrom <http://www.wikidata.org/entity/Q1242002> .

<https://sappho-digital.com/work/Q1242002> a lrmoo:F1_Work ;
    rdfs:label "Work of Sappho"@en ;
    ecrm:P14_carried_out_by <https://sappho-digital.com/person/Q154438> ;
    lrmoo:R16i_was_created_by <https://sappho-digital.com/work_creation/Q1242002> ;
    lrmoo:R19i_was_realised_through <https://sappho-digital.com/expression_creation/Q1242002> ;
    lrmoo:R3_is_realised_in <https://sappho-digital.com/expression/Q1242002> .

<https://sappho-digital.com/person/Q154438> a ecrm:E21_Person ;
    rdfs:label "Franz Grillparzer" ;
    ecrm:P14i_performed <https://sappho-digital.com/manifestation_creation/Q1242002>,
        <https://sappho-digital.com/work/Q1242002>,
        <https://sappho-digital.com/work_creation/Q1242002> ;
    owl:sameAs <http://www.wikidata.org/entity/Q154438> .

<https://sappho-digital.com/expression_creation/Q1242002> a lrmoo:F28_Expression_Creation ;
    rdfs:label "Expression creation of Sappho"@en ;
    ecrm:P14_carried_out_by <https://sappho-digital.com/person/Q154438> ;
    ecrm:P4_has_time-span <https://sappho-digital.com/timespan/1817> ;
    lrmoo:R17_created <https://sappho-digital.com/expression/Q1242002> ;
    lrmoo:R19_created_a_realisation_of <https://sappho-digital.com/work/Q1242002> ;
    prov:wasDerivedFrom <http://www.wikidata.org/entity/Q1242002> .

<https://sappho-digital.com/timespan/1817> a ecrm:E52_Time-Span ;
    rdfs:label "1817"^^xsd:gYear ;
    ecrm:P4i_is_time-span_of <https://sappho-digital.com/expression_creation/Q1242002> .

<https://sappho-digital.com/expression/Q1242002> a lrmoo:F2_Expression ;
    rdfs:label "Expression of Sappho"@en ;
    ecrm:P102_has_title <https://sappho-digital.com/title/expression/Q1242002> ;
    ecrm:P138i_has_representation <https://sappho-digital.com/digital/Q1242002> ;
    ecrm:P1_is_identified_by <https://sappho-digital.com/identifier/Q1242002> ;
    ecrm:P2_has_type <https://sappho-digital.com/genre/Q80930> ;
    lrmoo:R17i_was_created_by <https://sappho-digital.com/expression_creation/Q1242002> ;
    lrmoo:R3i_realises <https://sappho-digital.com/work/Q1242002> ;
    lrmoo:R4i_is_embodied_in <https://sappho-digital.com/manifestation/Q1242002> ;
    owl:sameAs <http://www.wikidata.org/entity/Q1242002> ;
    prov:wasDerivedFrom <http://www.wikidata.org/entity/Q1242002> .

<https://sappho-digital.com/title/expression/Q1242002> a ecrm:E35_Title ;
    ecrm:P102i_is_title_of <https://sappho-digital.com/expression/Q1242002> ;
    ecrm:P190_has_symbolic_content <https://sappho-digital.com/title_string/expression/Q1242002> .

<https://sappho-digital.com/title_string/expression/Q1242002> a ecrm:E62_String ;
    rdfs:label "Sappho"@de ;
    ecrm:P190i_is_content_of <https://sappho-digital.com/title/expression/Q1242002> .

<https://sappho-digital.com/identifier/Q1242002> a ecrm:E42_Identifier ;
    rdfs:label "Q1242002" ;
    ecrm:P1i_identifies <https://sappho-digital.com/expression/Q1242002> ;
    ecrm:P2_has_type <https://sappho-digital.com/id_type/wikidata> .

<https://sappho-digital.com/id_type/wikidata> a ecrm:E55_Type ;
    rdfs:label "Wikidata ID"@en ;
    ecrm:P2_is_type_of <https://sappho-digital.com/identifier/Q1242002> ;
    owl:sameAs <http://www.wikidata.org/wiki/Q43649390> .

<https://sappho-digital.com/genre/Q80930> a ecrm:E55_Type ;
    rdfs:label "tragedy"@en ;
    ecrm:P2_has_type <https://sappho-digital.com/genre_type/wikidata> ;
    ecrm:P2_is_type_of <https://sappho-digital.com/expression/Q1242002> ;
    owl:sameAs <http://www.wikidata.org/entity/Q80930> .

<https://sappho-digital.com/genre_type/wikidata> a ecrm:E55_Type ;
    rdfs:label "Wikidata Genre"@en ;
    ecrm:P2_is_type_of <https://sappho-digital.com/genre/Q80930> .

<https://sappho-digital.com/digital/Q1242002> a ecrm:E73_Information_Object ;
    rdfs:label "Digital copy of Sappho"@en ;
    ecrm:P138_represents <https://sappho-digital.com/expression/Q1242002> ;
    rdfs:seeAlso <http://www.zeno.org/nid/20004898184> .

<https://sappho-digital.com/manifestation_creation/Q1242002> a lrmoo:F30_Manifestation_Creation ;
    rdfs:label "Manifestation creation of Sappho"@en ;
    ecrm:P14_carried_out_by <https://sappho-digital.com/person/Q154438>,
        <https://sappho-digital.com/publisher/Q133849481> ;
    ecrm:P4_has_time-span <https://sappho-digital.com/timespan/1819> ;
    ecrm:P7_took_place_at <https://sappho-digital.com/place/Q1741> ;
    lrmoo:R24_created <https://sappho-digital.com/manifestation/Q1242002> ;
    prov:wasDerivedFrom <http://www.wikidata.org/entity/Q1242002> .

<https://sappho-digital.com/publisher/Q133849481> a ecrm:E40_Legal_Body ;
    rdfs:label "Wallishausser’sche Buchhandlung"@en ;
    ecrm:P14i_performed <https://sappho-digital.com/manifestation_creation/Q1242002> ;
    owl:sameAs <http://www.wikidata.org/entity/Q133849481> .

<https://sappho-digital.com/timespan/1819> a ecrm:E52_Time-Span ;
    rdfs:label "1819"^^xsd:gYear ;
    ecrm:P4_is_time-span_of <https://sappho-digital.com/manifestation_creation/Q1242002> .

<https://sappho-digital.com/place/Q1741> a ecrm:E53_Place ;
    rdfs:label "Vienna"@en ;
    ecrm:P7i_witnessed <https://sappho-digital.com/manifestation_creation/Q1242002> ;
    owl:sameAs <http://www.wikidata.org/entity/Q1741> .

<https://sappho-digital.com/manifestation/Q1242002> a lrmoo:F3_Manifestation ;
    rdfs:label "Manifestation of Sappho"@en ;
    ecrm:P102_has_title <https://sappho-digital.com/title/manifestation/Q1242002> ;
    lrmoo:R24i_was_created_through <https://sappho-digital.com/manifestation_creation/Q1242002> ;
    lrmoo:R27i_was_materialized_by <https://sappho-digital.com/item_production/Q1242002> ;
    lrmoo:R4_embodies <https://sappho-digital.com/expression/Q1242002> ;
    lrmoo:R7i_is_exemplified_by <https://sappho-digital.com/item/Q1242002> .

<https://sappho-digital.com/title/manifestation/Q1242002> a ecrm:E35_Title ;
    ecrm:P102i_is_title_of <https://sappho-digital.com/manifestation/Q1242002> ;
    ecrm:P190_has_symbolic_content <https://sappho-digital.com/title_string/manifestation/Q1242002> .

<https://sappho-digital.com/title_string/manifestation/Q1242002> a ecrm:E62_String ;
    rdfs:label "Sappho"@de ;
    ecrm:P190i_is_content_of <https://sappho-digital.com/title/manifestation/Q1242002> .

<https://sappho-digital.com/item_production/Q1242002> a lrmoo:F32_Item_Production_Event ;
    rdfs:label "Item production event of Sappho"@en ;
    lrmoo:R27_materialized <https://sappho-digital.com/manifestation/Q1242002> ;
    lrmoo:R28_produced <https://sappho-digital.com/item/Q1242002> .

<https://sappho-digital.com/item/Q1242002> a lrmoo:F5_Item ;
    rdfs:label "Item of Sappho"@en ;
    lrmoo:R28i_was_produced_by <https://sappho-digital.com/item_production/Q1242002> ;
    lrmoo:R7_exemplifies <https://sappho-digital.com/manifestation/Q1242002> .
```
</details>

---

<details>

<summary><h2>🌐 Relations Module (INTRO)</h2></summary>

The [relations.py](https://github.com/laurauntner/wikidata-to-cidoc-crm/blob/main/relations/relations.py) script reads a list of Wikidata QIDs for works from a CSV file and creates RDF triples using INTRO, CIDOC CRM (eCRM, mapped to CRM) and LRMoo (mapped to FRBRoo). It models:

- Literary works (`F2_Expression`, see works module)
  - linked to the Wikidata item via `owl:sameAs`
- Intertextual relations (`INT31_IntertextualRelation`) between expressions
  - with `INT_Interpretation` instances linked to the Wikidata items of the expressions via `prov:wasDerivedFrom`
  - derived from actualizations, citations and optionally `wdt:P4969`, `wdt:P2512` and `wdt:P921`
- References (`INT18_Reference`) for …
  - persons: `E21_Person` with `E42_Identifier`, derived from `wdt:P180`, `wdt:P921` and `wdt:P9527` for `wdt:Q5`
  - places: `E53_Place` with `E42_Identifier`, derived from the same properties for `wdt:Q2221906`
  - expressions: derived from `wdt:P361` and `wdt:P1299` for given QIDs
  - with actualizations (`INT2_ActualizationOfFeature`) of these references in specific expressions
    - with `INT_Interpretation` linked to the Wikidata items of the expressions via `prov:wasDerivedFrom`
- Citations via `INT21_TextPassage` instances
  - linked to the expressions
  - derived from `wdt:P2860` and `wdt:P6166` for given QIDs
  - linked to the citing Wikidata item via `prov:wasDerivedFrom`
- Characters (`INT_Character`)
  - linked to the Wikidata item via `owl:sameAs` and identified by `E42_Identifier`
  - derived from `wdt:P674` or `wdt:P180`, `wdt:P921` and `wdt:P527` if the item is `wdt:Q95074`, `wdt:Q3658341`, `wdt:Q15632617`, `wdt:Q97498056`, `wdt:Q122192387` or `wdt:Q115537581`
  - optionally linked to a real Person (`E21_Person`)
  - always with actualizations (`INT2_ActualizationOfFeature`) of these characters in specific expressions
    - with `INT_Interpretation` linked to the Wikidata items of the expressions via `prov:wasDerivedFrom`
- Motifs, Plots and Topics
  - all linked to Wikidata items via `owl:sameAs` and identified by `E42_Identifier`
  - `INT_Motif`: derived from `wdt:P180` and `wdt:P9527` for `wdt:Q1229071`, `wdt:Q68614425` or `wdt:Q1697305`, otherwise the item has to be linked via `wdt:P6962`
  - `INT_Plot`: derived from `wdt:P180`, `wdt:P527` and `wdt:P921` for `wdt:Q42109240`
  - `INT_Topic`: derived from `wdt:P921`, `wdt:P180` and `wdt:P527` for `wdt:Q26256810`
  - with `INT2_ActualizationOfFeature` instances for specific expressions
    - with interpretations (`INT_Interpretation`) linked to the Wikidata items of the expressions via `prov:wasDerivedFrom`

The current data model focuses exclusively on textual works, but—based on INTRO—it could be extended to cover intermedial and interpictorial aspects as well. It also only models intertextual relationships among the texts listed in the CSV file, i.e. it assumes you’re seeking intertexts of known works rather than exploring every possible intertext. 
Please also note that all searches are strictly one-way: Work → Phenomenon. 

📎 A [visual documentation](https://github.com/laurauntner/wikidata-to-cidoc-crm/blob/main/relations/relations.png) of the relations data model is included in the `relations` folder.

<h3>Example Input</h3>

```turtle
qids
Q1242002 # Franz Grillparzer’s "Sappho"
Q119292643 # Therese Rak’s "Sappho"
Q19179765 # Amalie von Imhoff’s "Die Schwestern von Lesbos"
Q120199245 # Adolph von Schaden’s "Die moderne Sappho"
```

<h3>Example Output</h3>

Namespace declarations and mappings to CRM and FRBRoo are applied but not shown in this exemplary output.

Please also note that the output is currently sparse because the relevant data in Wikidata is simply too limited. The script also remains fairly slow and should be tested (and possibly optimized) on larger data sets.

Further, it’s highly recommended to manually refine the generated triples afterward: INTRO provides very detailed means for recording literary-scholarly analyses as Linked Data, whereas this module captures only the basics.

```turtle
# Expressions

<https://sappho-digital.com/expression/Q1242002> a lrmoo:F2_Expression ;
    rdfs:label "Expression of Sappho"@en ;
    ecrm:P67i_is_referred_to_by <https://sappho-digital.com/actualization/work_ref/Q1242002_Q119292643> ;
    owl:sameAs <http://www.wikidata.org/entity/Q1242002> ;
    intro:R18_showsActualization <https://sappho-digital.com/actualization/character/Q17892_Q1242002>,
        <https://sappho-digital.com/actualization/motif/Q165_Q1242002>,
        <https://sappho-digital.com/actualization/person_ref/Q17892_Q1242002>,
        <https://sappho-digital.com/actualization/place_ref/Q128087_Q1242002>,
        <https://sappho-digital.com/actualization/plot/Q134285870_Q1242002>,
        <https://sappho-digital.com/actualization/topic/Q10737_Q1242002> ;
    intro:R30_hasTextPassage <https://sappho-digital.com/textpassage/Q1242002_Q119292643> .

<https://sappho-digital.com/expression/Q119292643> a lrmoo:F2_Expression ;
    rdfs:label "Expression of Sappho. Eine Novelle"@en ;
    owl:sameAs <http://www.wikidata.org/entity/Q119292643> ;
    intro:R18_showsActualization <https://sappho-digital.com/actualization/motif/Q165_Q119292643>,
        <https://sappho-digital.com/actualization/person_ref/Q17892_Q119292643>,
        <https://sappho-digital.com/actualization/plot/Q134285870_Q119292643>,
        <https://sappho-digital.com/actualization/topic/Q10737_Q119292643>,
        <https://sappho-digital.com/actualization/work_ref/Q1242002_Q119292643> ;
    intro:R30_hasTextPassage <https://sappho-digital.com/textpassage/Q119292643_Q1242002> .

<https://sappho-digital.com/expression/Q19179765> a lrmoo:F2_Expression ;
    rdfs:label "Expression of Die Schwestern von Lesbos"@en ;
    owl:sameAs <http://www.wikidata.org/entity/Q19179765> ;
    intro:R18_showsActualization <https://sappho-digital.com/actualization/place_ref/Q128087_Q19179765> .

<https://sappho-digital.com/expression/Q120199245> a lrmoo:F2_Expression ;
    rdfs:label "Expression of Die moderne Sappho"@en ;
    owl:sameAs <http://www.wikidata.org/entity/Q120199245> ;
    intro:R18_showsActualization <https://sappho-digital.com/actualization/character/Q17892_Q120199245> .

# Intertextual Relations

<https://sappho-digital.com/relation/Q120199245_Q1242002> a intro:INT31_IntertextualRelation ;
    rdfs:label "Intertextual relation between Die moderne Sappho and Sappho"@en ;
    intro:R21i_isIdentifiedBy <https://sappho-digital.com/actualization/interpretation/Q120199245_Q1242002> ;
    intro:R22i_relationIsBasedOnSimilarity <https://sappho-digital.com/feature/character/Q17892> ;
    intro:R24_hasRelatedEntity <https://sappho-digital.com/actualization/character/Q17892_Q120199245>,
        <https://sappho-digital.com/actualization/character/Q17892_Q1242002> .

<https://sappho-digital.com/feature/interpretation/Q120199245_Q1242002> a intro:INT_Interpretation ;
    rdfs:label "Interpretation of intertextual relation between Die moderne Sappho and Sappho"@en ;
    intro:R17i_featureIsActualizedIn <https://sappho-digital.com/actualization/interpretation/Q120199245_Q1242002> .

<https://sappho-digital.com/actualization/interpretation/Q120199245_Q1242002> a intro:INT2_ActualizationOfFeature ;
    rdfs:label "Interpretation of intertextual relation between Die moderne Sappho and Sappho"@en ;
    prov:wasDerivedFrom <http://www.wikidata.org/entity/Q120199245>,
        <http://www.wikidata.org/entity/Q1242002> ;
    intro:R17_actualizesFeature <https://sappho-digital.com/feature/interpretation/Q120199245_Q1242002> ;
    intro:R21_identifies <https://sappho-digital.com/relation/Q120199245_Q1242002> .

<https://sappho-digital.com/relation/Q1242002_Q19179765> a intro:INT31_IntertextualRelation ;
    rdfs:label "Intertextual relation between Sappho and Die Schwestern von Lesbos"@en ;
    intro:R21i_isIdentifiedBy <https://sappho-digital.com/actualization/interpretation/Q1242002_Q19179765> ;
    intro:R22i_relationIsBasedOnSimilarity <https://sappho-digital.com/feature/place_ref/Q128087> ;
    intro:R24_hasRelatedEntity <https://sappho-digital.com/actualization/place_ref/Q128087_Q1242002>,
        <https://sappho-digital.com/actualization/place_ref/Q128087_Q19179765> .

<https://sappho-digital.com/feature/interpretation/Q1242002_Q19179765> a intro:INT_Interpretation ;
    rdfs:label "Interpretation of intertextual relation between Sappho and Die Schwestern von Lesbos"@en ;
    intro:R17i_featureIsActualizedIn <https://sappho-digital.com/actualization/interpretation/Q1242002_Q19179765> .

<https://sappho-digital.com/actualization/interpretation/Q1242002_Q19179765> a intro:INT2_ActualizationOfFeature ;
    rdfs:label "Interpretation of intertextual relation between Sappho and Die Schwestern von Lesbos"@en ;
    prov:wasDerivedFrom <http://www.wikidata.org/entity/Q1242002>,
        <http://www.wikidata.org/entity/Q19179765> ;
    intro:R17_actualizesFeature <https://sappho-digital.com/feature/interpretation/Q1242002_Q19179765> ;
    intro:R21_identifies <https://sappho-digital.com/relation/Q1242002_Q19179765> .

<https://sappho-digital.com/relation/Q119292643_Q1242002> a intro:INT31_IntertextualRelation ;
    rdfs:label "Intertextual relation between Sappho and Sappho. Eine Novelle"@en ;
    intro:R21i_isIdentifiedBy <https://sappho-digital.com/actualization/interpretation/Q119292643_Q1242002> ;
    intro:R22i_relationIsBasedOnSimilarity <https://sappho-digital.com/feature/motif/Q165>,
        <https://sappho-digital.com/feature/person_ref/Q17892>,
        <https://sappho-digital.com/feature/plot/Q134285870>,
        <https://sappho-digital.com/feature/topic/Q10737>,
        <https://sappho-digital.com/feature/work_ref/Q1242002> ;
    intro:R24_hasRelatedEntity <https://sappho-digital.com/actualization/motif/Q165_Q119292643>,
        <https://sappho-digital.com/actualization/motif/Q165_Q1242002>,
        <https://sappho-digital.com/actualization/person_ref/Q17892_Q119292643>,
        <https://sappho-digital.com/actualization/person_ref/Q17892_Q1242002>,
        <https://sappho-digital.com/actualization/plot/Q134285870_Q119292643>,
        <https://sappho-digital.com/actualization/plot/Q134285870_Q1242002>,
        <https://sappho-digital.com/actualization/topic/Q10737_Q119292643>,
        <https://sappho-digital.com/actualization/topic/Q10737_Q1242002>,
        <https://sappho-digital.com/actualization/work_ref/Q1242002_Q119292643>,
        <https://sappho-digital.com/textpassage/Q119292643_Q1242002>,
        <https://sappho-digital.com/textpassage/Q1242002_Q119292643> .

<https://sappho-digital.com/feature/interpretation/Q119292643_Q1242002> a intro:INT_Interpretation ;
    rdfs:label "Interpretation of intertextual relation between Sappho and Sappho. Eine Novelle"@en ;
    intro:R17i_featureIsActualizedIn <https://sappho-digital.com/actualization/interpretation/Q119292643_Q1242002> .

<https://sappho-digital.com/actualization/interpretation/Q119292643_Q1242002> a intro:INT2_ActualizationOfFeature ;
    rdfs:label "Interpretation of intertextual relation between Sappho and Sappho. Eine Novelle"@en ;
    prov:wasDerivedFrom <http://www.wikidata.org/entity/Q119292643>,
        <http://www.wikidata.org/entity/Q1242002> ;
    intro:R17_actualizesFeature <https://sappho-digital.com/feature/interpretation/Q119292643_Q1242002> ;
    intro:R21_identifies <https://sappho-digital.com/relation/Q119292643_Q1242002> .

# Features & Actualizations

# Person References

<https://sappho-digital.com/feature/person_ref/Q17892> a intro:INT18_Reference ;
    rdfs:label "Reference to Sappho (person)"@en ;
    intro:R17i_featureIsActualizedIn <https://sappho-digital.com/actualization/person_ref/Q17892_Q119292643>,
        <https://sappho-digital.com/actualization/person_ref/Q17892_Q1242002> ;
    intro:R22_providesSimilarityForRelation <https://sappho-digital.com/relation/Q119292643_Q1242002> .

<https://sappho-digital.com/person/Q17892> a ecrm:E21_Person ;
    rdfs:label "Sappho"@en ;
    ecrm:P1_is_identified_by <https://sappho-digital.com/identifier/Q17892> ;
    ecrm:P67i_is_referred_to_by <https://sappho-digital.com/actualization/character/Q17892_Q120199245>,
        <https://sappho-digital.com/actualization/character/Q17892_Q1242002>,
        <https://sappho-digital.com/actualization/person_ref/Q17892_Q119292643>,
        <https://sappho-digital.com/actualization/person_ref/Q17892_Q1242002> ;
    owl:sameAs <http://www.wikidata.org/entity/Q17892> .

<https://sappho-digital.com/identifier/Q17892> a ecrm:E42_Identifier ;
    rdfs:label "Q17892"@en ;
    ecrm:P1i_identifies <https://sappho-digital.com/feature/character/Q17892>,
        <https://sappho-digital.com/person/Q17892> ;
    ecrm:P2_has_type <https://sappho-digital.com/id_type/wikidata> ;
    prov:wasDerivedFrom <http://www.wikidata.org/entity/Q17892> .

<https://sappho-digital.com/actualization/person_ref/Q17892_Q119292643> a intro:INT2_ActualizationOfFeature ;
    rdfs:label "Sappho in Sappho. Eine Novelle"@en ;
    ecrm:P67_refers_to <https://sappho-digital.com/person/Q17892> ;
    intro:R17_actualizesFeature <https://sappho-digital.com/feature/person_ref/Q17892> ;
    intro:R18i_actualizationFoundOn <https://sappho-digital.com/expression/Q119292643> ;
    intro:R21i_isIdentifiedBy <https://sappho-digital.com/actualization/interpretation/Q17892_Q119292643> ;
    intro:R24i_isRelatedEntity <https://sappho-digital.com/relation/Q119292643_Q1242002> .

<https://sappho-digital.com/feature/interpretation/Q17892_Q119292643> a intro:INT_Interpretation ;
    rdfs:label "Interpretation of Sappho in Sappho. Eine Novelle"@en ;
    intro:R17i_featureIsActualizedIn <https://sappho-digital.com/actualization/interpretation/Q17892_Q119292643> .

<https://sappho-digital.com/actualization/interpretation/Q17892_Q119292643> a intro:INT2_ActualizationOfFeature ;
    rdfs:label "Interpretation of Sappho in Sappho. Eine Novelle"@en ;
    prov:wasDerivedFrom <http://www.wikidata.org/entity/Q119292643> ;
    intro:R17_actualizesFeature <https://sappho-digital.com/feature/interpretation/Q17892_Q119292643> ;
    intro:R21_identifies <https://sappho-digital.com/actualization/person_ref/Q17892_Q119292643> .

<https://sappho-digital.com/actualization/person_ref/Q17892_Q1242002> a intro:INT2_ActualizationOfFeature ;
    rdfs:label "Sappho in Sappho"@en ;
    ecrm:P67_refers_to <https://sappho-digital.com/person/Q17892> ;
    intro:R17_actualizesFeature <https://sappho-digital.com/feature/person_ref/Q17892> ;
    intro:R18i_actualizationFoundOn <https://sappho-digital.com/expression/Q1242002> ;
    intro:R21i_isIdentifiedBy <https://sappho-digital.com/actualization/interpretation/Q17892_Q1242002> ;
    intro:R24i_isRelatedEntity <https://sappho-digital.com/relation/Q119292643_Q1242002> .

<https://sappho-digital.com/feature/interpretation/Q17892_Q1242002> a intro:INT_Interpretation ;
    rdfs:label "Interpretation of Sappho in Sappho"@en ;
    intro:R17i_featureIsActualizedIn <https://sappho-digital.com/actualization/interpretation/Q17892_Q1242002> .

<https://sappho-digital.com/actualization/interpretation/Q17892_Q1242002> a intro:INT2_ActualizationOfFeature ;
    rdfs:label "Interpretation of Sappho in Sappho"@en ;
    prov:wasDerivedFrom <http://www.wikidata.org/entity/Q1242002> ;
    intro:R17_actualizesFeature <https://sappho-digital.com/feature/interpretation/Q17892_Q1242002> ;
    intro:R21_identifies <https://sappho-digital.com/actualization/character/Q17892_Q1242002>,
        <https://sappho-digital.com/actualization/person_ref/Q17892_Q1242002> .

# Place References

<https://sappho-digital.com/feature/place_ref/Q128087> a intro:INT18_Reference ;
    rdfs:label "Reference to Lesbos (place)"@en ;
    intro:R17i_featureIsActualizedIn <https://sappho-digital.com/actualization/place_ref/Q128087_Q1242002>,
        <https://sappho-digital.com/actualization/place_ref/Q128087_Q19179765> ;
    intro:R22_providesSimilarityForRelation <https://sappho-digital.com/relation/Q1242002_Q19179765> .

<https://sappho-digital.com/place/Q128087> a ecrm:E53_Place ;
    rdfs:label "Lesbos"@en ;
    ecrm:P1_is_identified_by <https://sappho-digital.com/identifier/Q128087> ;
    ecrm:P67i_is_referred_to_by <https://sappho-digital.com/actualization/place_ref/Q128087_Q1242002>,
        <https://sappho-digital.com/actualization/place_ref/Q128087_Q19179765> ;
    owl:sameAs <http://www.wikidata.org/entity/Q128087> .

<https://sappho-digital.com/identifier/Q128087> a ecrm:E42_Identifier ;
    rdfs:label "Q128087"@en ;
    ecrm:P1i_identifies <https://sappho-digital.com/place/Q128087> ;
    ecrm:P2_has_type <https://sappho-digital.com/id_type/wikidata> ;
    prov:wasDerivedFrom <http://www.wikidata.org/entity/Q128087> .

<https://sappho-digital.com/actualization/place_ref/Q128087_Q1242002> a intro:INT2_ActualizationOfFeature ;
    rdfs:label "Lesbos in Sappho"@en ;
    ecrm:P67_refers_to <https://sappho-digital.com/place/Q128087> ;
    intro:R17_actualizesFeature <https://sappho-digital.com/feature/place_ref/Q128087> ;
    intro:R18i_actualizationFoundOn <https://sappho-digital.com/expression/Q1242002> ;
    intro:R21i_isIdentifiedBy <https://sappho-digital.com/actualization/interpretation/Q128087_Q1242002> ;
    intro:R24i_isRelatedEntity <https://sappho-digital.com/relation/Q1242002_Q19179765> .

<https://sappho-digital.com/feature/interpretation/Q128087_Q1242002> a intro:INT_Interpretation ;
    rdfs:label "Interpretation of Lesbos in Sappho"@en ;
    intro:R17i_featureIsActualizedIn <https://sappho-digital.com/actualization/interpretation/Q128087_Q1242002> .

<https://sappho-digital.com/actualization/interpretation/Q128087_Q1242002> a intro:INT2_ActualizationOfFeature ;
    rdfs:label "Interpretation of Lesbos in Sappho"@en ;
    prov:wasDerivedFrom <http://www.wikidata.org/entity/Q1242002> ;
    intro:R17_actualizesFeature <https://sappho-digital.com/feature/interpretation/Q128087_Q1242002> ;
    intro:R21_identifies <https://sappho-digital.com/actualization/place_ref/Q128087_Q1242002> .

<https://sappho-digital.com/actualization/place_ref/Q128087_Q19179765> a intro:INT2_ActualizationOfFeature ;
    rdfs:label "Lesbos in Die Schwestern von Lesbos"@en ;
    ecrm:P67_refers_to <https://sappho-digital.com/place/Q128087> ;
    intro:R17_actualizesFeature <https://sappho-digital.com/feature/place_ref/Q128087> ;
    intro:R18i_actualizationFoundOn <https://sappho-digital.com/expression/Q19179765> ;
    intro:R21i_isIdentifiedBy <https://sappho-digital.com/actualization/interpretation/Q128087_Q19179765> ;
    intro:R24i_isRelatedEntity <https://sappho-digital.com/relation/Q1242002_Q19179765> .

<https://sappho-digital.com/feature/interpretation/Q128087_Q19179765> a intro:INT_Interpretation ;
    rdfs:label "Interpretation of Lesbos in Die Schwestern von Lesbos"@en ;
    intro:R17i_featureIsActualizedIn <https://sappho-digital.com/actualization/interpretation/Q128087_Q19179765> .

<https://sappho-digital.com/actualization/interpretation/Q128087_Q19179765> a intro:INT2_ActualizationOfFeature ;
    rdfs:label "Interpretation of Lesbos in Die Schwestern von Lesbos"@en ;
    prov:wasDerivedFrom <http://www.wikidata.org/entity/Q19179765> ;
    intro:R17_actualizesFeature <https://sappho-digital.com/feature/interpretation/Q128087_Q19179765> ;
    intro:R21_identifies <https://sappho-digital.com/actualization/place_ref/Q128087_Q19179765> .

# Expression References

<https://sappho-digital.com/feature/work_ref/Q1242002> a intro:INT18_Reference ;
    rdfs:label "Reference to Sappho (expression)"@en ;
    intro:R17i_featureIsActualizedIn <https://sappho-digital.com/actualization/work_ref/Q1242002_Q119292643> ;
    intro:R22_providesSimilarityForRelation <https://sappho-digital.com/relation/Q119292643_Q1242002> .

<https://sappho-digital.com/actualization/work_ref/Q1242002_Q119292643> a intro:INT2_ActualizationOfFeature ;
    rdfs:label "Reference to Sappho in Sappho. Eine Novelle"@en ;
    ecrm:P67_refers_to <https://sappho-digital.com/expression/Q1242002> ;
    intro:R17_actualizesFeature <https://sappho-digital.com/feature/work_ref/Q1242002> ;
    intro:R18i_actualizationFoundOn <https://sappho-digital.com/expression/Q119292643> ;
    intro:R21i_isIdentifiedBy <https://sappho-digital.com/actualization/interpretation/Q1242002_Q119292643> ;
    intro:R24i_isRelatedEntity <https://sappho-digital.com/relation/Q119292643_Q1242002> .

<https://sappho-digital.com/feature/interpretation/Q1242002_Q119292643> a intro:INT_Interpretation ;
    rdfs:label "Interpretation of Sappho in Sappho. Eine Novelle"@en ;
    intro:R17i_featureIsActualizedIn <https://sappho-digital.com/actualization/interpretation/Q1242002_Q119292643> .

<https://sappho-digital.com/actualization/interpretation/Q1242002_Q119292643> a intro:INT2_ActualizationOfFeature ;
    rdfs:label "Interpretation of Sappho in Sappho. Eine Novelle"@en ;
    prov:wasDerivedFrom <http://www.wikidata.org/entity/Q119292643> ;
    intro:R17_actualizesFeature <https://sappho-digital.com/feature/interpretation/Q1242002_Q119292643> ;
    intro:R21_identifies <https://sappho-digital.com/actualization/work_ref/Q1242002_Q119292643> .

# Citations

<https://sappho-digital.com/textpassage/Q119292643_Q1242002> a intro:INT21_TextPassage ;
    rdfs:label "Text passage in Sappho. Eine Novelle"@en ;
    prov:wasDerivedFrom <http://www.wikidata.org/entity/Q1242002> ;
    intro:R24i_isRelatedEntity <https://sappho-digital.com/relation/Q119292643_Q1242002> ;
    intro:R30i_isTextPassageOf <https://sappho-digital.com/expression/Q119292643> .

<https://sappho-digital.com/textpassage/Q1242002_Q119292643> a intro:INT21_TextPassage ;
    rdfs:label "Text passage in Sappho"@en ;
    prov:wasDerivedFrom <http://www.wikidata.org/entity/Q1242002> ;
    intro:R24i_isRelatedEntity <https://sappho-digital.com/relation/Q119292643_Q1242002> ;
    intro:R30i_isTextPassageOf <https://sappho-digital.com/expression/Q1242002> .

# Characters

<https://sappho-digital.com/feature/character/Q17892> a intro:INT_Character ;
    rdfs:label "Sappho"@en ;
    ecrm:P1_is_identified_by <https://sappho-digital.com/identifier/Q17892> ;
    owl:sameAs <http://www.wikidata.org/entity/Q17892> ;
    intro:R17i_featureIsActualizedIn <https://sappho-digital.com/actualization/character/Q17892_Q120199245>,
        <https://sappho-digital.com/actualization/character/Q17892_Q1242002> ;
    intro:R22_providesSimilarityForRelation <https://sappho-digital.com/relation/Q120199245_Q1242002> .

<https://sappho-digital.com/actualization/character/Q17892_Q120199245> a intro:INT2_ActualizationOfFeature ;
    rdfs:label "Sappho in Die moderne Sappho"@en ;
    ecrm:P67_refers_to <https://sappho-digital.com/person/Q17892> ;
    intro:R17_actualizesFeature <https://sappho-digital.com/feature/character/Q17892> ;
    intro:R18i_actualizationFoundOn <https://sappho-digital.com/expression/Q120199245> ;
    intro:R21i_isIdentifiedBy <https://sappho-digital.com/actualization/interpretation/Q17892_Q120199245> ;
    intro:R24i_isRelatedEntity <https://sappho-digital.com/relation/Q120199245_Q1242002> .

<https://sappho-digital.com/feature/interpretation/Q17892_Q120199245> a intro:INT_Interpretation ;
    rdfs:label "Interpretation of Sappho in Die moderne Sappho"@en ;
    intro:R17i_featureIsActualizedIn <https://sappho-digital.com/actualization/interpretation/Q17892_Q120199245> .

<https://sappho-digital.com/actualization/interpretation/Q17892_Q120199245> a intro:INT2_ActualizationOfFeature ;
    rdfs:label "Interpretation of Sappho in Die moderne Sappho"@en ;
    prov:wasDerivedFrom <http://www.wikidata.org/entity/Q120199245> ;
    intro:R17_actualizesFeature <https://sappho-digital.com/feature/interpretation/Q17892_Q120199245> ;
    intro:R21_identifies <https://sappho-digital.com/actualization/character/Q17892_Q120199245> .

<https://sappho-digital.com/actualization/character/Q17892_Q1242002> a intro:INT2_ActualizationOfFeature ;
    rdfs:label "Sappho in Sappho"@en ;
    ecrm:P67_refers_to <https://sappho-digital.com/person/Q17892> ;
    intro:R17_actualizesFeature <https://sappho-digital.com/feature/character/Q17892> ;
    intro:R18i_actualizationFoundOn <https://sappho-digital.com/expression/Q1242002> ;
    intro:R21i_isIdentifiedBy <https://sappho-digital.com/actualization/interpretation/Q17892_Q1242002> ;
    intro:R24i_isRelatedEntity <https://sappho-digital.com/relation/Q120199245_Q1242002> .

# Motifs

<https://sappho-digital.com/feature/motif/Q165> a intro:INT_Motif ;
    rdfs:label "sea (motif)"@en ;
    ecrm:P1_is_identified_by <https://sappho-digital.com/identifier/Q165> ;
    owl:sameAs <http://www.wikidata.org/entity/Q165> ;
    intro:R17i_featureIsActualizedIn <https://sappho-digital.com/actualization/motif/Q165_Q119292643>,
        <https://sappho-digital.com/actualization/motif/Q165_Q1242002> ;
    intro:R22_providesSimilarityForRelation <https://sappho-digital.com/relation/Q119292643_Q1242002> .

<https://sappho-digital.com/identifier/Q165> a ecrm:E42_Identifier ;
    rdfs:label "Q165"@en ;
    ecrm:P1i_identifies <https://sappho-digital.com/feature/motif/Q165> ;
    ecrm:P2_has_type <https://sappho-digital.com/id_type/wikidata> ;
    prov:wasDerivedFrom <http://www.wikidata.org/entity/Q165> .

<https://sappho-digital.com/actualization/motif/Q165_Q119292643> a intro:INT2_ActualizationOfFeature ;
    rdfs:label "sea in Sappho. Eine Novelle"@en ;
    intro:R17_actualizesFeature <https://sappho-digital.com/feature/motif/Q165> ;
    intro:R18i_actualizationFoundOn <https://sappho-digital.com/expression/Q119292643> ;
    intro:R21i_isIdentifiedBy <https://sappho-digital.com/actualization/interpretation/Q165_Q119292643> ;
    intro:R24i_isRelatedEntity <https://sappho-digital.com/relation/Q119292643_Q1242002> .

<https://sappho-digital.com/feature/interpretation/Q165_Q119292643> a intro:INT_Interpretation ;
    rdfs:label "Interpretation of sea in Sappho. Eine Novelle"@en ;
    intro:R17i_featureIsActualizedIn <https://sappho-digital.com/actualization/interpretation/Q165_Q119292643> .

<https://sappho-digital.com/actualization/interpretation/Q165_Q119292643> a intro:INT2_ActualizationOfFeature ;
    rdfs:label "Interpretation of sea in Sappho. Eine Novelle"@en ;
    prov:wasDerivedFrom <http://www.wikidata.org/entity/Q119292643> ;
    intro:R17_actualizesFeature <https://sappho-digital.com/feature/interpretation/Q165_Q119292643> ;
    intro:R21_identifies <https://sappho-digital.com/actualization/motif/Q165_Q119292643> .

<https://sappho-digital.com/actualization/motif/Q165_Q1242002> a intro:INT2_ActualizationOfFeature ;
    rdfs:label "sea in Sappho"@en ;
    intro:R17_actualizesFeature <https://sappho-digital.com/feature/motif/Q165> ;
    intro:R18i_actualizationFoundOn <https://sappho-digital.com/expression/Q1242002> ;
    intro:R21i_isIdentifiedBy <https://sappho-digital.com/actualization/interpretation/Q165_Q1242002> ;
    intro:R24i_isRelatedEntity <https://sappho-digital.com/relation/Q119292643_Q1242002> .

<https://sappho-digital.com/feature/interpretation/Q165_Q1242002> a intro:INT_Interpretation ;
    rdfs:label "Interpretation of sea in Sappho"@en ;
    intro:R17i_featureIsActualizedIn <https://sappho-digital.com/actualization/interpretation/Q165_Q1242002> .

<https://sappho-digital.com/actualization/interpretation/Q165_Q1242002> a intro:INT2_ActualizationOfFeature ;
    rdfs:label "Interpretation of sea in Sappho"@en ;
    prov:wasDerivedFrom <http://www.wikidata.org/entity/Q1242002> ;
    intro:R17_actualizesFeature <https://sappho-digital.com/feature/interpretation/Q165_Q1242002> ;
    intro:R21_identifies <https://sappho-digital.com/actualization/motif/Q165_Q1242002> .

# Plots

<https://sappho-digital.com/feature/plot/Q134285870> a intro:INT_Plot ;
    rdfs:label "Sappho’s Leap (plot)"@en ;
    ecrm:P1_is_identified_by <https://sappho-digital.com/identifier/Q134285870> ;
    owl:sameAs <http://www.wikidata.org/entity/Q134285870> ;
    intro:R17i_featureIsActualizedIn <https://sappho-digital.com/actualization/plot/Q134285870_Q119292643>,
        <https://sappho-digital.com/actualization/plot/Q134285870_Q1242002> ;
    intro:R22_providesSimilarityForRelation <https://sappho-digital.com/relation/Q119292643_Q1242002> .

<https://sappho-digital.com/identifier/Q134285870> a ecrm:E42_Identifier ;
    rdfs:label "Q134285870"@en ;
    ecrm:P1i_identifies <https://sappho-digital.com/feature/plot/Q134285870> ;
    ecrm:P2_has_type <https://sappho-digital.com/id_type/wikidata> ;
    prov:wasDerivedFrom <http://www.wikidata.org/entity/Q134285870> .

<https://sappho-digital.com/actualization/plot/Q134285870_Q119292643> a intro:INT2_ActualizationOfFeature ;
    rdfs:label "Sappho’s Leap in Sappho. Eine Novelle"@en ;
    intro:R17_actualizesFeature <https://sappho-digital.com/feature/plot/Q134285870> ;
    intro:R18i_actualizationFoundOn <https://sappho-digital.com/expression/Q119292643> ;
    intro:R21i_isIdentifiedBy <https://sappho-digital.com/actualization/interpretation/Q134285870_Q119292643> ;
    intro:R24i_isRelatedEntity <https://sappho-digital.com/relation/Q119292643_Q1242002> .

<https://sappho-digital.com/feature/interpretation/Q134285870_Q119292643> a intro:INT_Interpretation ;
    rdfs:label "Interpretation of Sappho’s Leap in Sappho. Eine Novelle"@en ;
    intro:R17i_featureIsActualizedIn <https://sappho-digital.com/actualization/interpretation/Q134285870_Q119292643> .

<https://sappho-digital.com/actualization/interpretation/Q134285870_Q119292643> a intro:INT2_ActualizationOfFeature ;
    rdfs:label "Interpretation of Sappho’s Leap in Sappho. Eine Novelle"@en ;
    prov:wasDerivedFrom <http://www.wikidata.org/entity/Q119292643> ;
    intro:R17_actualizesFeature <https://sappho-digital.com/feature/interpretation/Q134285870_Q119292643> ;
    intro:R21_identifies <https://sappho-digital.com/actualization/plot/Q134285870_Q119292643> .

<https://sappho-digital.com/actualization/plot/Q134285870_Q1242002> a intro:INT2_ActualizationOfFeature ;
    rdfs:label "Sappho’s Leap in Sappho"@en ;
    intro:R17_actualizesFeature <https://sappho-digital.com/feature/plot/Q134285870> ;
    intro:R18i_actualizationFoundOn <https://sappho-digital.com/expression/Q1242002> ;
    intro:R21i_isIdentifiedBy <https://sappho-digital.com/actualization/interpretation/Q134285870_Q1242002> ;
    intro:R24i_isRelatedEntity <https://sappho-digital.com/relation/Q119292643_Q1242002> .

<https://sappho-digital.com/feature/interpretation/Q134285870_Q1242002> a intro:INT_Interpretation ;
    rdfs:label "Interpretation of Sappho’s Leap in Sappho"@en ;
    intro:R17i_featureIsActualizedIn <https://sappho-digital.com/actualization/interpretation/Q134285870_Q1242002> .

<https://sappho-digital.com/actualization/interpretation/Q134285870_Q1242002> a intro:INT2_ActualizationOfFeature ;
    rdfs:label "Interpretation of Sappho’s Leap in Sappho"@en ;
    prov:wasDerivedFrom <http://www.wikidata.org/entity/Q1242002> ;
    intro:R17_actualizesFeature <https://sappho-digital.com/feature/interpretation/Q134285870_Q1242002> ;
    intro:R21_identifies <https://sappho-digital.com/actualization/plot/Q134285870_Q1242002> .

# Topics

<https://sappho-digital.com/feature/topic/Q10737> a intro:INT_Topic ;
    rdfs:label "suicide (topic)"@en ;
    ecrm:P1_is_identified_by <https://sappho-digital.com/identifier/Q10737> ;
    owl:sameAs <http://www.wikidata.org/entity/Q10737> ;
    intro:R17i_featureIsActualizedIn <https://sappho-digital.com/actualization/topic/Q10737_Q119292643>,
        <https://sappho-digital.com/actualization/topic/Q10737_Q1242002> ;
    intro:R22_providesSimilarityForRelation <https://sappho-digital.com/relation/Q119292643_Q1242002> .

<https://sappho-digital.com/identifier/Q10737> a ecrm:E42_Identifier ;
    rdfs:label "Q10737"@en ;
    ecrm:P1i_identifies <https://sappho-digital.com/feature/topic/Q10737> ;
    ecrm:P2_has_type <https://sappho-digital.com/id_type/wikidata> ;
    prov:wasDerivedFrom <http://www.wikidata.org/entity/Q10737> .

<https://sappho-digital.com/actualization/topic/Q10737_Q119292643> a intro:INT2_ActualizationOfFeature ;
    rdfs:label "suicide in Sappho. Eine Novelle"@en ;
    intro:R17_actualizesFeature <https://sappho-digital.com/feature/topic/Q10737> ;
    intro:R18i_actualizationFoundOn <https://sappho-digital.com/expression/Q119292643> ;
    intro:R21i_isIdentifiedBy <https://sappho-digital.com/actualization/interpretation/Q10737_Q119292643> ;
    intro:R24i_isRelatedEntity <https://sappho-digital.com/relation/Q119292643_Q1242002> .

<https://sappho-digital.com/feature/interpretation/Q10737_Q119292643> a intro:INT_Interpretation ;
    rdfs:label "Interpretation of suicide in Sappho. Eine Novelle"@en ;
    intro:R17i_featureIsActualizedIn <https://sappho-digital.com/actualization/interpretation/Q10737_Q119292643> .

<https://sappho-digital.com/actualization/interpretation/Q10737_Q119292643> a intro:INT2_ActualizationOfFeature ;
    rdfs:label "Interpretation of suicide in Sappho. Eine Novelle"@en ;
    prov:wasDerivedFrom <http://www.wikidata.org/entity/Q119292643> ;
    intro:R17_actualizesFeature <https://sappho-digital.com/feature/interpretation/Q10737_Q119292643> ;
    intro:R21_identifies <https://sappho-digital.com/actualization/topic/Q10737_Q119292643> .

<https://sappho-digital.com/actualization/topic/Q10737_Q1242002> a intro:INT2_ActualizationOfFeature ;
    rdfs:label "suicide in Sappho"@en ;
    intro:R17_actualizesFeature <https://sappho-digital.com/feature/topic/Q10737> ;
    intro:R18i_actualizationFoundOn <https://sappho-digital.com/expression/Q1242002> ;
    intro:R21i_isIdentifiedBy <https://sappho-digital.com/actualization/interpretation/Q10737_Q1242002> ;
    intro:R24i_isRelatedEntity <https://sappho-digital.com/relation/Q119292643_Q1242002> .

<https://sappho-digital.com/feature/interpretation/Q10737_Q1242002> a intro:INT_Interpretation ;
    rdfs:label "Interpretation of suicide in Sappho"@en ;
    intro:R17i_featureIsActualizedIn <https://sappho-digital.com/actualization/interpretation/Q10737_Q1242002> .

<https://sappho-digital.com/actualization/interpretation/Q10737_Q1242002> a intro:INT2_ActualizationOfFeature ;
    rdfs:label "Interpretation of suicide in Sappho"@en ;
    prov:wasDerivedFrom <http://www.wikidata.org/entity/Q1242002> ;
    intro:R17_actualizesFeature <https://sappho-digital.com/feature/interpretation/Q10737_Q1242002> ;
    intro:R21_identifies <https://sappho-digital.com/actualization/topic/Q10737_Q1242002> .

# Wikidata ID

<https://sappho-digital.com/id_type/wikidata> a ecrm:E55_Type ;
    rdfs:label "Wikidata ID"@en ;
    ecrm:P2i_is_type_of <https://sappho-digital.com/identifier/Q10737>,
        <https://sappho-digital.com/identifier/Q128087>,
        <https://sappho-digital.com/identifier/Q134285870>,
        <https://sappho-digital.com/identifier/Q165>,
        <https://sappho-digital.com/identifier/Q17892> ;
    owl:sameAs <http://www.wikidata.org/entity/Q43649390> .
```
</details>

---

<details>

<summary><h2>🔩 Merge Module </h2></summary>

Use this module to merge the outputted Turtle files and get one ontology that includes all information for authors, works and relations.

The Python script assumes that the Turtle files to be merged already exist, so you first have to run the other scripts.

</details>

---

<details>

<summary><h2>🔍 Map and Align Module </h2></summary>

⚡ This module is still in development.

Use this module to map and align the outputted Turtle files.

The Python script assumes that the Turtle files to be mapped and aligned already exist, so you first have to run the other scripts.

Identifiers added from:
- [Schema.org](https://schema.org/)
- [DBpedia](https://www.dbpedia.org/)
- [GND](https://www.dnb.de/DE/Professionell/Standardisierung/GND/gnd_node.html)
- [VIAF](https://viaf.org/)
- [GeoNames](http://www.geonames.org/)
- [Goodreads](https://www.goodreads.com/)

Alignments with: 
- [BIBO](http://purl.org/ontology/bibo/)
- [CiTO](http://purl.org/spar/cito/)
- [DC](http://purl.org/dc/terms/)
- [DoCo](http://purl.org/spar/doco/)
- [DraCor](http://dracor.org/ontology#)
- [FaBiO](http://purl.org/spar/fabio/)
- [FOAF](http://xmlns.com/foaf/0.1/)
- [FRBRoo](https://www.iflastandards.info/fr/frbr/frbroo)
- [GOLEM](https://ontology.golemlab.eu/)
- [Intertextuality Ontology](https://github.com/intertextor/intertextuality-ontology)
- [MiMoText](https://data.mimotext.uni-trier.de/wiki/Main_Page)
- [POSTDATA / OntoPoetry](https://postdata.linhd.uned.es/results/ontopoetry-v2-0/)

Despite overlaps in content, various ontologies were not considered because they are hardly used, not publicly accessible, or outdated. These include: SAWS, DanteSources, Hypermedia Dante Network, HyperHamlet. Also, the alignments focus specifically on those classes and properties that are important for the relations module.

</details>

