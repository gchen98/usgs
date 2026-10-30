# M2 findings: metadata completeness and anomalies

Sample: 500 public ScienceBase items from the search "water use" (top 500 by relevance,
harvested Oct 29 2026), of which 197 are data releases. Scores are a heuristic inspired by
the FAIR principles, **not** a USGS assessment or compliance audit.

Reproduce: `python scripts/harvest.py && python scripts/score.py && python scripts/anomalies.py`

| Finding | Number | Caveat |
|---|---|---|
| Mean completeness, data releases vs. others | 0.90 (n=197) vs. 0.48 (n=303) | 5 heuristic rules; `has_doi` favors releases by definition |
| Gap holds on rules unrelated to the release process | bbox 0.81 vs. 0.48; keywords 1.00 vs. 0.73 | Pass rates; one sample of 500 items |
| Data releases with no DOI identifier | 4 of 197 | Might be recorded elsewhere, e.g. in the citation text; not checked |
| Summaries under 20 words | 4 | Items with *no* summary aren't counted here |
| Duplicate-title flags | 18 (12 groups, 30 items) | 4 groups are a folder plus its own child, likely false positives |
| License info in JSON | not a top-level field; 284 of 500 have an attached metadata file | XML files not parsed (option A) |

Outputs: `data/derived/scores.csv`, `data/derived/anomalies.csv`.
