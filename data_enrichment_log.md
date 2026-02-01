# Data Enrichment Log (Task 1)

Date: 2026-02-01
Collected by: weldesilassie

## Summary
- Added new ACCESS indicators from World Bank WDI to strengthen forecasting inputs tied to digital access and financial service reach.
- Added impact links connecting key events to relevant indicators (usage and access).
- Updated schema in the unified dataset to include `parent_id` for impact links.

## Files Updated
- [data/raw/ethiopia_fi_unified_data.csv](data/raw/ethiopia_fi_unified_data.csv)

## New Observations Added
| record_id | indicator_code | observation_date | value_numeric | source_url | confidence | original_text | notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| REC_0034 | ACC_INTERNET_USERS | 2021-12-31 | 16.698 | https://api.worldbank.org/v2/country/ETH/indicator/IT.NET.USER.ZS?format=json | medium | Individuals using the Internet (% of population) - 2021: 16.698 | Proxy for digital access readiness |
| REC_0035 | ACC_MOBILE_SUBS_P100 | 2022-12-31 | 56.9643 | https://api.worldbank.org/v2/country/ETH/indicator/IT.CEL.SETS.P2?format=json | medium | Mobile cellular subscriptions (per 100 people) - 2022: 56.9643 | Network reach for mobile money adoption |
| REC_0036 | ACC_ATM_P100K | 2023-12-31 | 10.2308601802058 | https://api.worldbank.org/v2/country/ETH/indicator/FB.ATM.TOTL.P5?format=json | medium | Automated teller machines (ATMs) (per 100,000 adults) - 2023: 10.2308601802058 | Access infrastructure benchmark |
| REC_0037 | ACC_BANK_BRANCH_P100K | 2023-12-31 | 14.4895956917168 | https://api.worldbank.org/v2/country/ETH/indicator/FB.CBK.BRCH.P5?format=json | medium | Commercial bank branches (per 100,000 adults) - 2023: 14.4895956917168 | Physical access complements digital services |

## New Impact Links Added
| record_id | parent_id | pillar | related_indicator | impact_direction | impact_magnitude | lag_months | evidence_basis | source_url | confidence | original_text | notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| LNK_0001 | EVT_0001 | USAGE | USG_TELEBIRR_USERS | increase | high | 6 | empirical |  | medium | Telebirr launch expected to drive registered user growth | Links launch to observed telebirr user expansion |
| LNK_0002 | EVT_0003 | USAGE | USG_MPESA_USERS | increase | medium | 6 | empirical |  | medium | M-Pesa launch expected to increase registered users | Links product launch to user adoption |
| LNK_0003 | EVT_0004 | ACCESS | ACC_FAYDA | increase | high | 12 | empirical |  | medium | Fayda rollout enables ID enrollment growth | Digital ID coverage underpins account access |
| LNK_0004 | EVT_0008 | USAGE | USG_P2P_COUNT | increase | medium | 6 | theoretical |  | medium | Real-time payments increase transaction volumes | Instant payments reduce friction for P2P use |
| LNK_0005 | EVT_0002 | ACCESS | ACC_MOBILE_PEN | increase | low | 12 | literature |  | medium | New market entrant expands coverage and subscriptions | Competition tends to raise penetration over time |

## Schema Note
- Added `parent_id` column to support impact link relationships.

## Validation Checklist
- Loaded [data/raw/ethiopia_fi_unified_data.csv](data/raw/ethiopia_fi_unified_data.csv) and [data/raw/reference_codes.csv](data/raw/reference_codes.csv).
- Updated unified dataset with additions and impact links.
- Logged all new records with sources, original text, confidence, and notes.
