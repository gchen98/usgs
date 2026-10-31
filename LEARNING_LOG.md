# Learning log

## Time used
| Milestone | Budget | Actual | Notes |
|---|---|---|---|
| M0 | 1 h | ~0.5 h (est.) | Done Thu Oct 29 |
| M1 | 2 h | ~0.5 h (est.) | Done Thu Oct 29; 500 items, 197 data releases |
| M2 | 3 h | ~2+ h so far (est.) | Scores + 3 anomaly checks done, 11 tests pass; left: findings table, explain-back |
| M3 | 3 h | | Done Fri Oct 30: 20 queries, recall@1/5/10 = 0.35/0.85/0.95 |
| M4 (opt.) | 2 h | | Done Sat Oct 31: cite.py, evidence passages + links; no generation (by choice) |
| M5 | 1.5 h | | |

## Explain-back answers (my words)
Plain text = my words. *Italic "Feedback (Claude)"* lines = review notes to rehearse against.
### M0
- FAIR, one example of each letter:
  - Findable: presence of a unique id like the DOI
  - *Feedback (Claude): Good. A DOI is the persistent identifier (F1). Also mention rich, searchable metadata (title, abstract, keywords). The ScienceBase internal `id` is not a persistent identifier in the FAIR sense.*
  - Accessible: Finding the DOI, hitting the ScienceBase page, and fetching a JSON object over HTTPS
  - *Feedback (Claude): Strong revision. A is about getting data/metadata by its identifier over a standard open protocol, with auth only where needed, and the metadata staying available even if the data is removed. A nice UI is not what A means.*
  - Interoperable: Adherence to a common standard like JSON format or XML that include fields from a controlled vocabulary
  - *Feedback (Claude): Better. Lead with the vocabulary/standard, not the file format: FGDC/CSDGM or ISO 19115 metadata, keywords from the USGS Thesaurus. Likely follow-up: "Two records are both JSON; why aren't they interoperable?"*
  - Reusable: Including information on the license, provenance, and the community standards.
  - *Feedback (Claude): Correct: these are the three R sub-principles. A data dictionary (attribute definitions, units) is a concrete example of reuse support.*
- What is a ScienceBase item / data release?
  - Items are easily created on Science Base and may not have a DOI. The releases include items, but the dataset and its metadata must be scrutinized and reviewed in order to earn a permanent DOI.
  - *Feedback (Claude): Correct. Say "data review and metadata review" (USGS policy for data releases) rather than "data cleaning". A plain item can be just a project page or folder.*
- Why does metadata quality affect reuse?
  - Good metadata will allow users to use the data correctly and be less error prone for reproducing experiments.
  - *Feedback (Claude): Good. Add that metadata is also how people find the data and decide whether it fits their purpose (units, coverage, methods, limits).*
- Observation (ScienceBase web UI, query "water use"): only ~3% of results were in the Data Release category. To re-check via API in M1.
  - *Feedback (Claude): API check: 1,017 of 10,693 "water use" results are data releases (~9.5%); 197 of our top-500 sample. Different from the 3% UI figure; likely different filters/sorting, not verified.*
### M1
- How did I avoid hammering the API? What would break if the schema changed?
  - If the request object is not a HTTPError or there is a response message and response code are certain values, then it's considered retryable, which then wait exponentially longer times between retries. To recover it checks if the target path has a JSON. if so it doesn't retry the API for that page.
  - *Feedback (Claude): Retry and resume logic correct. Missing the politeness part: 100 items/page (5 requests, not 500), 1 s pause, descriptive User-Agent, back off on 429/5xx, fail fast on other 4xx. One-liner: "few requests, spaced out, clearly labeled, backs off when the server struggles, caches so nothing is fetched twice."*
  - (If `nextlink` were renamed) it would break by only fetching page 1.
  - *Feedback (Claude): Correct, and it fails silently: prints "Done: 100 items" with no error. Fix: warn if items < min(target, total). Not yet added (exercise).*
- Where does license info live? (my guess before checking): Not sure, maybe under Contacts?
  - Checked: not a top-level JSON field; 284/500 items have an attached XML/original metadata file, which is where use constraints likely live.
  - *Feedback (Claude): Interview point: a JSON-only check would wrongly report "no license"; the info likely sits in the attached FGDC record (Use Constraints). We chose to score JSON only and state this as a limitation (option A).*
### M2
- Which metadata fields did I score and why? What counts as an anomaly here?
- What is a false positive in my checks?
- (Oct 29) Fields scored and why:
  - identifiers field for "F" (has a DOI), files field for "A" so non image files are accessible, spatial field for "I" so proper coordinates can make the data interoperable, tags field has keywords for "I" again to support a vocabulary, and weblinks field for "R" so that the data is reusable
  - *Feedback (Claude): Add the why-not: `id`/`link` are on 500/500 items because ScienceBase generates them, so they can't separate good records from bad. "weblinks so the data is reusable" is circular; say related publications give the context and provenance needed for correct reuse.*
- (Oct 29) Anomalies and a false positive:
  - anomalies, very short summaries, duplicate titles, missing DOIs. False positive: "Archive of water use.." I saw the parent ID pointing to an archive that encompasses multiple years.
  - *Feedback (Claude): Good instinct to inspect parents. Add the general pattern: a ScienceBase folder often shares the title of the item inside it (4 of 12 duplicate groups were folder + own child), so exact-title matching picks up structure, not only true duplicates.*
- (Oct 29) What does 0.90 vs 0.48 mean?
  - these are a comparison of two averages (non vs data releases) where we average over all the rules and each data point is the proportion of items that pass a given rule.
  - *Feedback (Claude): Math correct: mean of item scores equals mean of per-rule pass rates (same items, equal weights). Still to answer: the honest framing. Caveats: my heuristic rules; one query, 500 items; `has_doi` partly circular; shows a difference, not that review caused it. Draft: "In my 500-item sample, data releases passed 90% of my completeness checks vs 48% for other items. Part of that is built in, since releases get DOIs by definition, but the gap holds on unrelated checks like bounding boxes."*
### M3
- (Oct 30) Explain-back:
  - embeddings are a method to encode a vocabulary term in as a numerical vector such that terms that more semantically similar will be closer based on a distance measure like cosine similarity
  - *Feedback (Claude): Right idea. Here we embed whole passages (title + summary), not single terms: a sentence-embedding model maps a passage to one 384-number vector. Cosine similarity is a similarity (higher = closer), not a distance.*
  - you would chunk if the number of tokens exceeds the size of your LLM's context window we were within the window here
  - *Feedback (Claude): It is the embedding model's input limit (all-MiniLM-L6-v2: 256 tokens), not an LLM context window; no LLM is involved yet. Two more reasons to chunk: past the limit text is silently cut off, and one vector for a long multi-topic document blurs its meaning. Small chunks also let you cite the exact passage. Evidence: title + summary median 177 tokens, 1 of 500 over the limit; the longer `body` field is where chunking would matter.*
  - recall @ different k tells you how deep you have to go (k) before recovering one of the relevant (true) documents. but if the documents labels (e.g. summaries) don't accurately convey the semantics of your query, retrieval can be poor.
  - *Feedback (Claude): Close. Recall@k is the share of ALL relevant items found in the top k; with one relevant id per query it equals "was it found by rank k". Your failure reason is real (sparse summaries, e.g. the empty-summary "Water Use" item). Add the second kind you found: evaluation failure, where the search returned arguably better items than the single label ("water usage in the US").*
- (Oct 30) Predictions before building:
  - Rank of the right item: I think it would rank around the top 5 but a vague search may rank around 50.
  - *Feedback (Claude): Reasonable; we'll measure. First real run (title-only index): "irrigation water use in Kansas" put the 2014, 2015 and 2016 Kansas irrigation releases at ranks 1-3 (cosine 0.98/0.97/0.97). Note the query names no year, so three items are equally right: queries need a list of relevant ids, and recall can be partial.*
  - Title only vs title + summary: I would embed the summary provided the context length is long enough.
  - *Feedback (Claude): Good instinct on context length. all-MiniLM-L6-v2 cuts input at 256 tokens; title + summary has median 177 and 90th percentile 200 tokens, and only 1 of 500 items goes over, so truncation is not a problem for summary. `body` (the full abstract) is longer; that is where chunking would matter. Keep the title too: short queries often match title words, and the summary alone can miss them.*
  - Judging search without labels: From my experience, we can use proxies like user reactions such as click through rate by mining logs.
  - *Feedback (Claude): Right for a live system (online evaluation). We have no users or logs, so we use offline evaluation: hand-write ~20 queries, each with the item id(s) that should come back (known-item search), and measure recall@k. Say plainly in the interview that the set is small and hand-made.*
- What are embeddings, in plain words? Why chunk? What did recall@k tell me?
- Where does retrieval fail? Examples:
- (Oct 30) Review of my first 10 eval queries and code:
  - *Feedback (Claude): (1) Two rows in queries.csv were missing the opening quote on the id, so the id never matched and those queries scored 0 (a data bug, not a search failure). Validate that every relevant id exists in the data. (2) Some targets have empty or near-empty summaries, so a vague query can only match the title; is that a fair test? (3) One relevant id per query undercounts: "Kansas Water Use" could fairly also accept the Kansas yearly releases. Decide relevance before searching. (4) Exact queries copied from titles are easy by construction; that's fine as a baseline, but label it. (5) All 5 targets are overview folders/pages; add data releases and specific topics (irrigation, thermoelectric, public supply, groundwater withdrawals, crop ET), synonyms ("withdrawals" vs "use"), and place-only queries. (6) build_text joins title and summary without a space; add ". ". (7) recall_at_k divides by zero if relevant_ids is empty; guard or assert.*
- (Oct 30) Review of 20-query eval:
  - *Feedback (Claude): Overall recall@1/5/10 = 0.35/0.85/0.95 (exact 0.5/0.9/1.0, vague 0.2/0.8/0.9). The one miss, "water usage in the US", still has the stray quote on its id, and even with the id fixed in memory it misses at k=10. Its top results (e.g. "Estimated Use of Water in the United States County-Level Data for 2015") are arguably MORE relevant than the target "National Water Use Projects": a labeling problem, not only a retrieval failure. Single-id labels penalize good answers. A/B with typo fixed in memory: title only exact 1.00/1.00/1.00, vague 0.20/0.40/0.60; title + summary exact 0.50/0.90/1.00, vague 0.20/0.80/0.90. Adding the summary trades exact-title precision at rank 1 for much better vague recall at 5-10. No query has more than one relevant id yet.*
### M4
- Why show citations? How would I evaluate answer quality?
- (Oct 31) Predictions before building:
  - Passage choice: I think returning the sentence closest in meaning is more satisfactory but in some cases the user may be looking for more of an "answer" in respond to a "question" and the whole summary could answer it better.
  - *Feedback (Claude): Good trade-off: precision vs. context. Middle ground: the best-matching sentence plus its neighbor(s) as a small window. Note that embedding each sentence separately IS chunking (sentence-level chunks), which connects M4 back to the M3 chunking question.*
  - Why citations: I'd like citations to easily link to for further information. it also shows more authenticity.
  - *Feedback (Claude): Yes. Sharper interview words: citations let the user VERIFY the claim against the source, and REACH the data itself (the item page and files: the A in FAIR). Say 'verifiability' or 'trust' instead of 'authenticity'.*
  - LLM failure mode: it might hallucinate an intepretation that is not consistent with the retrieved result.
  - *Feedback (Claude): Right: an unfaithful or ungrounded answer. The 'how to check' half is missing: require a citation on each sentence; check every cited id is among the retrieved items; hand-check a small set of answers, claim by claim, against the cited passages (faithfulness). Also: the answer can be faithful but wrong if retrieval picked the wrong items.*

- (Oct 31) First cite.py run, "how much water do farms in Kansas use":
  - *Feedback (Claude): All 22 tests pass; nltk handles "U.S." correctly. Findings from the output: (1) Results 1, 2 and 5 say "This USGS Data Release provides..." but are not tagged Data Release and show no DOI. They are child items of the 2014 Kansas irrigation data release; the DOI and release flag live on the PARENT. So M2's item-level `is_data_release` and `has_doi` undercount children of releases; scoring ignores the hierarchy. Strong interview point and a 'next step'. (2) Item rank and passage similarity disagree: results 3-4 have the best passages (0.71, 0.70) but rank below 1-2 (passages 0.59, 0.58); reranking by passage would reorder. (3) The best passages are boilerplate ("This dataset describes irrigation water use in Kansas in 2016.") and do not answer "how much": the numbers live in the data files, not the metadata. Metadata search tells you WHERE the answer is, not the answer. (4) The 2015 item has no DOI and no release tag; its parent is outside the sample, so its status is unknown.*

## Interview talk track
- What I built (30 sec):
In the past week, I built a small pipeline that runs a sample query "water use" on the sciencebase API to return a set of "items" that I could ask a series of questions. 1) is the quality of the metadata any different between items that are Data Releases vs non Data Releases and 2) How well can a search based on embedding vectors do compared to an exact string search?
  - *Feedback (Claude): Fix before the interview: no exact-string or keyword search was ever run. "Exact" and "vague" are two kinds of QUERY, both run through the same embedding search. Accurate version: "...and 2) how well does embedding search find the right item for title-like queries vs. vague, plain-language ones?" Also "past week" -> "past few days". Comparing against a keyword baseline is a good "next step".*
- What I learned / one thing that surprised me:
I discovered that Data Releases can have substantially higher quality of metadata based on 5 quantitative heuristics I came up with. I also was surprised that a semantic search using embeddings could perform almost as well as exact search for a more permissive window (e.g. top 10 results)
  - *Feedback (Claude): Reword to match what was measured: vague queries found the right item in the top 10 for 9 of 10 (recall@10 0.90 vs 1.00 for exact), but only 2 of 10 at rank 1. Adding the summary to the index doubled vague recall@5 (0.40 -> 0.80). For data releases, add the caveat that has_doi favors them by definition, and the gap holds on unrelated rules. Strong candidate for the 'surprise': the one miss was arguably a labeling failure, since search returned better items than my label.*
- What I have NOT done (be direct):
I haven't explored other metadata properties like license information, which would entail retrieving associated XML records for the SB items. It could be interesting to mine the information in each item deeper which may entail chunking during indexing.
  - *Feedback (Claude): Be more direct and list the not-done items plainly: not USGS work, no production repository or data-release workflow, no Globus or large-file transfer, no FGDC/XML parsing, no keyword baseline, no real users or query logs, evaluation is 20 queries written by me.*
- How it connects to the role's duties (metadata, discovery tools, FAIR, anomaly detection):
I think this training exercise aligns well with the role duties in that I practiced hands tasks of accessing real SB data, derived heuristics based on FAIR principles, and discovered actual anomalies in live data.
  - *Feedback (Claude): Good. Make it concrete with one example each: 4 data releases with no DOI identifier; duplicate-title flags where a folder and its child share a title (a false positive that taught me about ScienceBase structure). Say "public ScienceBase data" rather than implying internal access.*
