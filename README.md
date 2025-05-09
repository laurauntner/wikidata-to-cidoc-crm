# Wikidata to CIDOC CRM

This repository contains Python scripts that transform structured data from [Wikidata](https://www.wikidata.org/) into RDF using [CIDOC CRM](https://cidoc-crm.org/) (OWL version, [eCRM](https://erlangen-crm.org/docs/ecrm/current/)) and models based on CIDOC CRM: [LRMoo](https://repository.ifla.org/handle/20.500.14598/3677) and [INTRO](https://github.com/BOberreither/INTRO). To improve inference capabilities, all ECRM classes and properties have been mapped to CIDOC CRM using `owl:sameAs`. Also, all LRMoo classes and properties have been mapped to [FRBRoo](https://www.iflastandards.info/fr/frbr/frbroo).

The scripts are developed in the context of the project [Sappho Digital](https://sappho-digital.com/) by [Laura Untner](https://orcid.org/0000-0002-9649-0870).

The repository is under active development. Currently, the `authors`, `works` and `relations` modules are available. They model basic biographical, bibliographical and intertextual information based on data from Wikidata and can be dynamically extended. The modules can be used independently of each other, but a unification is planned.

Still to do:
- Implementation of `owl:imports`
- Extended ontology alignments
- Module that combines all modules
- SHACL Shapes
- Python package for better reuse

The goal is to enable CIDOC CRM-based semantic enrichment from Wikidata and other linked data sources. The scripts also use [PROV-O](https://www.w3.org/TR/prov-o/) (`prov:wasDerivedFrom`) to link data back to Wikidata.

Please note that these scripts are not magical. Data that is not available in Wikidata cannot appear in the triples.

> ⚠️ **Note:** All URIs currently use the `https://sappho.com/` base. Please adapt this to your own environment as needed.  
> 💡 **Reuse is encouraged**. The scripts are open for reuse. A reference to the Sappho Digital project would be appreciated if you use or build on them.

## Requirements

Install dependencies with:

```
pip install rdflib requests tqdm
```

---

<details>

<summary><h2>✍️ Authors Module</h2></summary>
  
The [authors.py](https://github.com/laurauntner/wikidata-to-cidoc-crm/blob/main/authors/authors.py) script reads a list of Wikidata QIDs from a CSV file and creates RDF triples using CIDOC CRM (eCRM, mapped to CRM). It models:

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
<pre>
  <code class="language-turtle">
    qid
    Q469571
  </code>
</pre>

This is [Anna Louisa Karsch](https://www.wikidata.org/wiki/Q469571).

<h3>Example Output</h3>
<pre>
  <code class="language-turtle">
    # Namespace declarations and mappings to CRM are applied but not shown in this exemplary output.
    
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
  </code>
</pre>
</details>

---

## Works Module

The [works.py](https://github.com/laurauntner/wikidata-to-cidoc-crm/blob/main/works/works.py) script reads a list of Wikidata QIDs from a CSV file and creates RDF triples using CIDOC CRM (eCRM, mapped to CRM) and LRMoo (mapped to FRBRoo). It models:

- `F1_Work` (abstract works) and `F27_Work_Creation` with:
  - `E21_Person` (authors, derived from `wdt:P50`)
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

### Example Input

```
qid
Q1242002
```
(This is the tragedy [Sappho](https://www.wikidata.org/wiki/Q469571) written by Franz Grillparzer.)

### Example Output

```
# Namespace declarations and mappings to CRM are applied but not shown in this exemplary output.

<https://sappho-digital.com/work_creation/Q1242002> a lrmoo:F27_Work_Creation ;
    rdfs:label "Work creation of Sappho"@en ;
    ecrm:P14_carried_out_by <https://sappho-digital.com/person/Q154438> ;
    lrmoo:R16_created <https://sappho-digital.com/work/Q1242002> ;
    prov:wasDerivedFrom <http://www.wikidata.org/entity/Q1242002> .

<https://sappho-digital.com/work/Q1242002> a lrmoo:F1_Work ;
    rdfs:label "Work of Sappho"@en ;
    ecrm:P14_carried_out_by <https://sappho-digital.com/person/Q154438> ;
    lrmoo:R3_is_realised_in <https://sappho-digital.com/expression/Q1242002> .

<https://sappho-digital.com/person/Q154438> a ecrm:E21_Person ;
    rdfs:label "Franz Grillparzer" ;
    owl:sameAs <http://www.wikidata.org/entity/Q154438> .

<https://sappho-digital.com/expression_creation/Q1242002> a lrmoo:F28_Expression_Creation ;
    rdfs:label "Expression creation of Sappho"@en ;
    ecrm:P14_carried_out_by <https://sappho-digital.com/person/Q154438> ;
    ecrm:P4_has_time-span <https://sappho-digital.com/timespan/1817> ;
    lrmoo:R17_created <https://sappho-digital.com/expression/Q1242002> ;
    lrmoo:R19_created_a_realisation_of <https://sappho-digital.com/work/Q1242002> ;
    prov:wasDerivedFrom <http://www.wikidata.org/entity/Q1242002> .

<https://sappho-digital.com/timespan/1817> a ecrm:E52_Time-Span ;
    rdfs:label "1817"^^xsd:gYear .

<https://sappho-digital.com/expression/Q1242002> a lrmoo:F2_Expression ;
    rdfs:label "Expression of Sappho"@en ;
    ecrm:P102_has_title <https://sappho-digital.com/title/expression/Q1242002> ;
    ecrm:P1_is_identified_by <https://sappho-digital.com/identifier/Q1242002> ;
    ecrm:P2_has_type <https://sappho-digital.com/genre/Q80930> ;
    owl:sameAs <http://www.wikidata.org/entity/Q1242002> ;
    prov:wasDerivedFrom <http://www.wikidata.org/entity/Q1242002> .

<https://sappho-digital.com/title/expression/Q1242002> a ecrm:E35_Title ;
    ecrm:P190_has_symbolic_content <https://sappho-digital.com/title_string/Q1242002> .

<https://sappho-digital.com/title_string/expression/Q1242002> a ecrm:E62_String ;
    rdfs:label "Sappho"@de .

<https://sappho-digital.com/identifier/Q1242002> a ecrm:E42_Identifier ;
    rdfs:label "Q1242002" ;
    ecrm:P2_has_type <https://sappho.com/id_type/wikidata> .

<https://sappho.com/id_type/wikidata> a ecrm:E55_Type ;
    rdfs:label "Wikidata ID"@en ;
    owl:sameAs <https://www.wikidata.org/wiki/Q43649390> .

<https://sappho-digital.com/genre/Q80930> a ecrm:E55_Type ;
    rdfs:label "tragedy"@en ;
    ecrm:P2_has_type <https://sappho-digital.com/genre_type/wikidata> ;
    owl:sameAs <http://www.wikidata.org/entity/Q80930> .

<https://sappho-digital.com/genre_type/wikidata> a ecrm:E55_Type ;
    rdfs:label "Wikidata Genre"@en .

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
    owl:sameAs <http://www.wikidata.org/entity/Q133849481> .

<https://sappho-digital.com/timespan/1819> a ecrm:E52_Time-Span ;
    rdfs:label "1819"^^xsd:gYear .

<https://sappho-digital.com/place/Q1741> a ecrm:E53_Place ;
    rdfs:label "Vienna"@en ;
    owl:sameAs <http://www.wikidata.org/entity/Q1741> .

<https://sappho-digital.com/manifestation/Q1242002> a lrmoo:F3_Manifestation ;
    rdfs:label "Manifestation of Sappho"@en ;
    ecrm:P102_has_title <https://sappho-digital.com/title/manifestation/Q1242002> ;
    lrmoo:R4_embodies <https://sappho-digital.com/expression/Q1242002> .

<https://sappho-digital.com/title/manifestation/Q1242002> a ecrm:E35_Title ;
    ecrm:P190_has_symbolic_content <https://sappho-digital.com/title_string/manifestation/Q1242002> .

<https://sappho-digital.com/title_string/manifestation/Q1242002> a ecrm:E62_String ;
    rdfs:label "Sappho"@de .

<https://sappho-digital.com/item_production/Q1242002> a lrmoo:F32_Item_Production_Event ;
    rdfs:label "Item production event of Sappho"@en ;
    lrmoo:R27_materialized <https://sappho-digital.com/manifestation/Q1242002> ;
    lrmoo:R28_produced <https://sappho-digital.com/item/Q1242002> .

<https://sappho-digital.com/item/Q1242002> a lrmoo:F5_Item ;
    rdfs:label "Item of Sappho"@en ;
    lrmoo:R7_exemplifies <https://sappho-digital.com/manifestation/Q1242002> .
```
