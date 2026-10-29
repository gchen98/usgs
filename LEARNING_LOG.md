# Learning log

## Time used
| Milestone | Budget | Actual | Notes |
|---|---|---|---|
| M0 | 1 h | ~0.5 h (est.) | Done Thu Oct 29 |
| M1 | 2 h | | |
| M2 | 3 h | | |
| M3 | 3 h | | |
| M4 (opt.) | 2 h | | |
| M5 | 1.5 h | | |

## Explain-back answers (my words)
### M0
- FAIR, one example of each letter:
  - Findable: presence of a unique id like the DOI
  - Accessible: Finding the DOI, hitting the ScienceBase page, and fetching a JSON object over HTTPS
  - Interoperable: Adherence to a common standard like JSON format or XML that include fields from a controlled vocabulary
  - Reusable: Including information on the license, provenance, and the community standards.
- What is a ScienceBase item / data release?
  - Items are easily created on Science Base and may not have a DOI. The releases include items, but the dataset and its metadata must be scrutinized and reviewed in order to earn a permanent DOI.
- Why does metadata quality affect reuse?
  - Good metadata will allow users to use the data correctly and be less error prone for reproducing experiments.
- Observation (ScienceBase web UI, query "water use"): only ~3% of results were in the Data Release category. To re-check via API in M1.
### M1
- How did I avoid hammering the API? What would break if the schema changed?
### M2
- Which metadata fields did I score and why? What counts as an anomaly here?
- What is a false positive in my checks?
### M3
- What are embeddings, in plain words? Why chunk? What did recall@k tell me?
- Where does retrieval fail? Examples:
### M4
- Why show citations? How would I evaluate answer quality?

## Interview talk track
- What I built (30 sec):
- What I learned / one thing that surprised me:
- What I have NOT done (be direct):
- How it connects to the role's duties (metadata, discovery tools, FAIR, anomaly detection):
