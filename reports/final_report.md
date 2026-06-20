# Final Report

## Dataset Summary

- Source workbook: `/Users/austin/Desktop/2Slimey/data/raw/2026-05-13_donnees-ouvertes_divulgation-octrois-subventions-et-contributions.xlsx`
- Primary sheet: `Extraction rev-003`
- Data rows analyzed: 224,000
- Columns analyzed: 42
- Cleaned dataset output: `/Users/austin/Desktop/2Slimey/data/processed/fichier_nettoye.csv`

## Missing Values Summary

| recommendation            |   column_count |
|---------------------------|----------------|
| Nothing                   |             14 |
| Possible Removal          |             12 |
| Imputation + Missing Flag |              9 |
| Evaluate Utility          |              6 |
| Simple Imputation         |              1 |

Top missing columns:

| column_name                | inferred_type   |   total_rows |   missing_count |   missing_percentage | recommendation   |
|----------------------------|-----------------|--------------|-----------------|----------------------|------------------|
| coverage                   | text            |       224000 |          223998 |               100    | Possible Removal |
| federal_riding_name_en     | text            |       224000 |          223993 |               100    | Possible Removal |
| federal_riding_name_fr     | text            |       224000 |          223994 |               100    | Possible Removal |
| federal_riding_number      | text            |       224000 |          223995 |               100    | Possible Removal |
| amendment_date             | date            |       224000 |          214478 |                95.75 | Possible Removal |
| recipient_operating_name   | text            |       224000 |          213036 |                95.11 | Possible Removal |
| foreign_currency_type      | text            |       224000 |          208126 |                92.91 | Possible Removal |
| foreign_currency_value     | numeric         |       224000 |          208126 |                92.91 | Possible Removal |
| research_organization_name | text            |       224000 |          207362 |                92.57 | Possible Removal |
| naics_identifier           | numeric         |       224000 |          200998 |                89.73 | Possible Removal |

## Duplicate Summary

| duplicate_type       |   group_count |
|----------------------|---------------|
| identifier_duplicate |         26627 |
| probable_duplicate   |          2189 |

Top duplicate groups:

| duplicate_type       | rule_name                 | duplicate_key   |   occurrences | example_ref_number      | example_organization                                                                                                                            | review_recommendation                                                                   |
|----------------------|---------------------------|-----------------|---------------|-------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------|
| identifier_duplicate | recipient_business_number | 0               |          1053 | 235-2021-2022-Q2-00098  | 1)Saputo Foods Limited 2)Saputo Dairy Products Canada G.P                                                                                       | Review whether repeated identifiers represent true duplicates or legitimate amendments. |
| identifier_duplicate | recipient_business_number | -               |           885 | 093-2021-2022-Q4-00410  | 10039365 Canada inc. - Chalets Baie des Plongeurs|10039365 Canada inc. - Chalets Baie des Plongeurs                                             | Review whether repeated identifiers represent true duplicates or legitimate amendments. |
| identifier_duplicate | recipient_business_number | 108162025       |            61 | 276-2019-2020-Q3-00071  | The University of New Brunswick|The University of New Brunswick                                                                                 | Review whether repeated identifiers represent true duplicates or legitimate amendments. |
| identifier_duplicate | recipient_business_number | 107690273       |            58 | 235-2024-2025-Q3-00507  | Memorial University of Newfoundland                                                                                                             | Review whether repeated identifiers represent true duplicates or legitimate amendments. |
| identifier_duplicate | recipient_business_number | 107951618       |            51 | 235-2020-2021-Q1-00188  | Conseil de Direction de l'Armée du Salut du Canada                                                                                              | Review whether repeated identifiers represent true duplicates or legitimate amendments. |
| identifier_duplicate | recipient_business_number | 107863888       |            51 | 276-2020-2021-Q3-00055  | Department of Education and Early Childhood Development|Department of Education and Early Childhood Development                                 | Review whether repeated identifiers represent true duplicates or legitimate amendments. |
| identifier_duplicate | recipient_business_number | 858650955       |            47 | 235-2022-2023-Q2-00099  | Battleford Agency Tribal Chiefs Inc.                                                                                                            | Review whether repeated identifiers represent true duplicates or legitimate amendments. |
| identifier_duplicate | recipient_business_number | 831174362       |            45 | 5235-2021-2022-Q4-00866 | Impres Inc.                                                                                                                                     | Review whether repeated identifiers represent true duplicates or legitimate amendments. |
| identifier_duplicate | recipient_business_number | 141039081       |            42 | 276-2019-2020-Q4-00065  | Newfoundland and Labrador Association of Technology and Innovation Inc.|Newfoundland and Labrador Association of Technology and Innovation Inc. | Review whether repeated identifiers represent true duplicates or legitimate amendments. |
| identifier_duplicate | recipient_business_number | 875471468       |            38 | 276-2019-2020-Q4-00144  | Atlantic Association of Community Business Development Corporations|Atlantic Association of Community Business Development Corporations         | Review whether repeated identifiers represent true duplicates or legitimate amendments. |

## Organization Analysis

| status   |   pair_count |
|----------|--------------|
| accepted |         8628 |
| review   |         6252 |

Top organization variant candidates:

| source_column        | variant_value                                                                                                 | canonical_value                                                                                               | normalized_variant                                                                                          | normalized_canonical                                                                                        |   variant_count |   canonical_count |   similarity_score | status   | match_basis            | justification                                                   |
|----------------------|---------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------|-----------------|-------------------|--------------------|----------|------------------------|-----------------------------------------------------------------|
| recipient_legal_name | Province of Ontario                                                                                           | PROVINCE OF ONTARIO                                                                                           | PROVINCE OF ONTARIO                                                                                         | PROVINCE OF ONTARIO                                                                                         |               1 |               185 |                100 | accepted | exact_normalized_match | Values become identical after deterministic text normalization. |
| recipient_legal_name | Literary and Historical Society of Quebec                                                                     | LITERARY AND HISTORICAL SOCIETY OF QUEBEC                                                                     | LITERARY AND HISTORICAL SOCIETY OF QUEBEC                                                                   | LITERARY AND HISTORICAL SOCIETY OF QUEBEC                                                                   |               1 |                80 |                100 | accepted | exact_normalized_match | Values become identical after deterministic text normalization. |
| recipient_legal_name | TVA PUBLICATIONS INC.                                                                                         | TVA PUBLICATIONS INC                                                                                          | TVA PUBLICATIONS INC                                                                                        | TVA PUBLICATIONS INC                                                                                        |              29 |                76 |                100 | accepted | exact_normalized_match | Values become identical after deterministic text normalization. |
| recipient_legal_name | Conseil Communautaire du Grand Havre                                                                          | CONSEIL COMMUNAUTAIRE DU GRAND-HAVRE                                                                          | CONSEIL COMMUNAUTAIRE DU GRAND HAVRE                                                                        | CONSEIL COMMUNAUTAIRE DU GRAND HAVRE                                                                        |               1 |                62 |                100 | accepted | exact_normalized_match | Values become identical after deterministic text normalization. |
| recipient_legal_name | Atlantic Food and Beverage Processors Association Inc.|Atlantic Food and Beverage Processors Association Inc. | Atlantic Food And Beverage Processors Association Inc.|Atlantic Food And Beverage Processors Association Inc. | ATLANTIC FOOD AND BEVERAGE PROCESSORS ASSOCIATION INC ATLANTIC FOOD AND BEVERAGE PROCESSORS ASSOCIATION INC | ATLANTIC FOOD AND BEVERAGE PROCESSORS ASSOCIATION INC ATLANTIC FOOD AND BEVERAGE PROCESSORS ASSOCIATION INC |               1 |                59 |                100 | accepted | exact_normalized_match | Values become identical after deterministic text normalization. |
| recipient_legal_name | RESEAU ONTARIO DES ARTS DE LA SCENE INC.                                                                      | RÉSEAU ONTARIO DES ARTS DE LA SCÈNE INC.                                                                      | RESEAU ONTARIO DES ARTS DE LA SCENE INC                                                                     | RESEAU ONTARIO DES ARTS DE LA SCENE INC                                                                     |               5 |                54 |                100 | accepted | exact_normalized_match | Values become identical after deterministic text normalization. |
| recipient_legal_name | Youth Employment Services Foundation                                                                          | YOUTH EMPLOYMENT SERVICES FOUNDATION                                                                          | YOUTH EMPLOYMENT SERVICES FOUNDATION                                                                        | YOUTH EMPLOYMENT SERVICES FOUNDATION                                                                        |               8 |                49 |                100 | accepted | exact_normalized_match | Values become identical after deterministic text normalization. |
| recipient_legal_name | CROSS-COUNTRY SKI DE FOND CANADA                                                                              | CROSS COUNTRY SKI DE FOND CANADA                                                                              | CROSS COUNTRY SKI DE FOND CANADA                                                                            | CROSS COUNTRY SKI DE FOND CANADA                                                                            |               4 |                49 |                100 | accepted | exact_normalized_match | Values become identical after deterministic text normalization. |
| recipient_legal_name | ASSEMBLEE DE LA FRANCOPHONIE DE L'ONTARIO                                                                     | ASSEMBLÉE DE LA FRANCOPHONIE DE L'ONTARIO                                                                     | ASSEMBLEE DE LA FRANCOPHONIE DE L ONTARIO                                                                   | ASSEMBLEE DE LA FRANCOPHONIE DE L ONTARIO                                                                   |               1 |                48 |                100 | accepted | exact_normalized_match | Values become identical after deterministic text normalization. |
| recipient_legal_name | BATTLEFORDS AGENCY TRIBAL CHIEFS INC.                                                                         | Battlefords Agency Tribal Chiefs Inc.                                                                         | BATTLEFORDS AGENCY TRIBAL CHIEFS INC                                                                        | BATTLEFORDS AGENCY TRIBAL CHIEFS INC                                                                        |               1 |                45 |                100 | accepted | exact_normalized_match | Values become identical after deterministic text normalization. |

## Cleaning Summary

| status   |   mapping_count |
|----------|-----------------|
| accepted |            8628 |
| review   |            6252 |

- Automatic corrections applied: 8628
- Manual review mappings retained without auto-correction: 6252

## Limitations

- Excel workbooks do not support native pandas chunk streaming, so chunk processing is implemented through `openpyxl` row iteration before conversion into pandas DataFrames.
- Probable duplicates are review-oriented heuristics, not proof of redundant records.
- Organization similarity scores can suggest likely matches, but ambiguous names still require human validation.
- The source workbook already contains revision and intermediate cleaning columns, so downstream analysis may reflect prior upstream transformations.

## Readiness for Unsupervised Learning

The dataset is more suitable for unsupervised learning after cleaning because missingness patterns, duplicate risks, and organization-name inconsistencies have been surfaced in auditable reports. It is not fully analysis-ready until review-status organization mappings and probable duplicate groups are manually validated.

## Required Questions

1. Why clean data before unsupervised learning?
   Cleaning reduces noise, inconsistent scales, and naming fragmentation that would otherwise distort distance-based grouping and cluster interpretation.
2. Why can multiple organization names represent the same entity?
   Administrative datasets often mix punctuation changes, abbreviations, accent differences, legal suffix variations, upstream exports, and manual entry inconsistencies for the same recipient.
3. Why must ambiguous values be reviewed?
   Similar names can belong to different entities, so forcing a correction can merge unrelated organizations and corrupt downstream analysis.
4. Why preserve original columns?
   Original columns maintain auditability, let reviewers trace each change, and protect the source evidence if a cleaning rule needs to be reversed.
5. Why create cleaned columns?
   Separate cleaned columns make modeling easier without destroying source fidelity, and they allow side-by-side validation of automated transformations.
6. How do missing values affect clustering?
   Missing values can bias imputation, reduce comparable features, and create artificial similarity or dissimilarity between records.
7. How do duplicates affect clustering?
   Duplicates overweight repeated entities, inflate cluster density, and can mislead algorithms into treating repeated records as stronger patterns than they really are.
8. Why use chunk processing?
   Chunk processing limits memory pressure on large Excel-derived datasets and allows full-dataset profiling without loading every row into one in-memory DataFrame.
9. Which corrections were automatic?
   Automatic corrections were limited to the 8628 accepted mappings whose normalized or fuzzy similarity scores met the project acceptance threshold.
10. Which require manual review?
   Manual review is still required for the 6252 review-status organization mappings and for probable duplicate groups flagged in the duplicates report.
