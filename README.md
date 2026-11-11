# FAIR-inspired metadata quality and search over USGS ScienceBase

A small, time-boxed learning project (Oct 29–Nov 1, 2026) by Gary Chen. It uses **public**
ScienceBase metadata only. It is **not USGS work**, and the "FAIR checks" are my own
heuristics inspired by the FAIR principles, **not an official assessment or compliance audit**.

## Question

For one topic ("water use"), how complete is the public metadata on ScienceBase items, do
reviewed data releases look different from other items, and can a simple local embedding
search find the right item from a plain-language query?

## Data

- 500 public items from the ScienceBase catalog search `q=water use`, the first 500 by the
  API's default (relevance) order, harvested Oct 29, 2026. The full search has 10,693 results.
- 197 of the 500 are data releases (`systemTypes` contains "Data Release"). Across all 10,693
  results, the documented filter `filter=systemType=Data Release` returns 1,017.
- Raw JSON pages are cached in `data/raw/` (not committed); derived tables are in `data/derived/`.

## Reproduce

```bash
conda env create -f environment.yml && conda activate usgs
python scripts/harvest.py          # 5 API requests; rerun skips cached pages
python scripts/score.py            # -> data/derived/scores.csv
python scripts/anomalies.py        # -> data/derived/anomalies.csv
python scripts/search.py --eval    # recall@k on data/eval/queries.csv
python scripts/search.py "irrigation water use in Kansas"
python scripts/cite.py "how much water do farms in Kansas use"   # results with evidence + links
python -m pytest -q                # 22 tests
```

The embedding model (`all-MiniLM-L6-v2`) downloads on the first search run, and `cite.py`
needs the NLTK sentence tokenizer once (`python -c "import nltk; nltk.download('punkt_tab')"`);
after that everything runs offline.

## Method

**Harvest** (`scripts/harvest.py`). Pages of 100 via `max`/`offset`, following `nextlink`
until it is absent. Politeness: 1 s pause between requests, a descriptive User-Agent, retry
with backoff (5/10/20/40 s) only on timeouts, 429 and 5xx. Each page is written to disk as it
arrives, so a rerun resumes instead of refetching.

**Completeness score** (`scripts/score.py`). Each item gets the fraction of 5 rules it passes.
Rules only use fields a person has to fill in; system-generated fields such as `id` and `link`
are on 500/500 items and cannot tell records apart (a test enforces that no rule is constant).

| Rule | FAIR letter | Passes when |
|---|---|---|
| `has_doi` | F | an identifier of type DOI exists |
| `has_non_image_files` | A | at least one attached file is not an image |
| `has_good_boundingbox` | I | `spatial.boundingBox` has all four sides and min < max |
| `has_keywords_with_type` | I | at least one tag has a `type` |
| `has_weblinks_uri` | R | at least one web link (e.g. related publication) has a URI |

**Anomaly checks** (`scripts/anomalies.py`): data release with no valid DOI identifier;
summary under 20 words; exact duplicate titles.

**Search** (`scripts/search.py`). Each item is embedded as `title + ". " + summary` with a
local sentence-transformers model, and ranked by cosine similarity. Title + summary fits the
model's 256-token limit (median 177 tokens, 1 of 500 over), so no chunking was needed.

**Evaluation.** 20 hand-written queries, each with one relevant item id chosen before
searching: 10 "exact" (close to a title) and 10 "vague" (how a user might ask). Metric:
recall@k, the share of relevant items in the top k.

**Results with citations** (`scripts/cite.py`). For each top item, the summary is split into
sentences (NLTK, which keeps "U.S." intact), each sentence is embedded, and the sentence most
similar to the query is shown as evidence with the ScienceBase item link and DOI link when
present. No LLM generation: the tool shows sources, it does not write answers.

## Results

**Completeness** (5 rules, 500 items):

| | Items | Mean score | Median |
|---|---|---|---|
| Data releases | 197 | 0.90 | 1.0 |
| Other items | 303 | 0.48 | 0.4 |

| Rule pass rate | Other | Data release |
|---|---|---|
| `has_doi` | 0.15 | 0.98 |
| `has_non_image_files` | 0.44 | 0.97 |
| `has_good_boundingbox` | 0.48 | 0.81 |
| `has_keywords_with_type` | 0.73 | 1.00 |
| `has_weblinks_uri` | 0.60 | 0.74 |

Part of the gap is built in, since data releases receive DOIs by definition, but the gap also
appears on rules unrelated to the release process (bounding box, keywords).

**Anomalies** (26 flags): 4 data releases with no DOI identifier, 4 summaries under 20 words
(one is the single word "A"), 18 duplicate-title flags in 12 groups. At least 4 of the 12
groups are a ScienceBase folder and its own child item sharing a title, which is how content
is organized rather than an error (false positives). See `docs/findings.md`.

**Search** (20 queries):

| | recall@1 | recall@5 | recall@10 |
|---|---|---|---|
| exact (10) | 0.50 | 0.90 | 1.00 |
| vague (10) | 0.20 | 0.80 | 0.90 |
| all (20) | 0.35 | 0.85 | 0.95 |

Indexing title only instead of title + summary gave exact 1.00/1.00/1.00 and vague
0.20/0.40/0.60 (run with one query's id typo corrected in memory). Adding the summary costs
exact matches at rank 1 but doubles vague recall@5.

The one miss at k=10, "water usage in the US", returned items such as "Estimated Use of
Water in the United States County-Level Data for 2015" ahead of the labeled target
"National Water Use Projects". Those results are arguably more relevant: an evaluation
(labeling) failure as much as a retrieval failure.

**Citations** (one example query, "how much water do farms in Kansas use", top 5):

- All 5 results are Kansas irrigation items. Three of them say "This U.S. Geological Survey
  (USGS) Data Release provides..." yet carry no Data Release tag and no DOI: they are child
  items of the 2014 Kansas irrigation data release, and the DOI and release tag live on the
  parent item.
- Item rank and best-passage similarity disagree: results 3–4 have the closest passages
  (0.71, 0.70) but rank below results 1–2 (0.59, 0.58).
- The best passages are descriptive ("This dataset describes irrigation water use in Kansas
  in 2016.") and contain no numbers. Metadata search points to where an answer is (the data
  files), not to the answer itself, which is the main reason I did not add LLM generation.

## Limitations

- One topic, one search query, 500 items in relevance order: not a random sample of ScienceBase.
- The completeness rules are my own heuristic with equal weights; different rules would give
  different scores. A higher score for data releases is a difference, not evidence that
  review caused it.
- Scoring looks at each item alone and ignores the parent/child hierarchy. Child items of a
  data release are counted as "other items" and fail `has_doi` even though their parent has
  a DOI, so the data-release vs. other comparison is distorted in a direction I have not measured.
- License and use-constraint information is not a top-level field in the item JSON. It likely
  sits in the attached metadata records (284 of 500 items have one), which I did not parse,
  so licensing is not scored.
- The evaluation set is small (20 queries), hand-made by one person, with one relevant id per
  query. Exact queries were written from titles, so they are easy by construction.
- Not tested: other embedding models, keyword (BM25) baseline, chunking of the longer `body`
  field, re-ranking by passage similarity, answer generation, and any real user queries or logs.
- The citation output was inspected on example queries only; passage quality was not
  measured.

## What I'd do next

- Make scoring hierarchy-aware: inherit data-release status and DOI from the parent item,
  then re-run the comparison.
- Parse the attached FGDC/XML metadata for use constraints and attribute definitions, and
  score license and data-dictionary presence.
- Compare against a keyword baseline and a second embedding model.
- Grow the evaluation set with multiple relevant ids per query, judged by more than one person.
- Treat folder/child title matches separately in duplicate detection.
- Re-rank by best-passage similarity and check whether recall@k changes.

---

## Addendum: a local tool-calling agent (LangGraph + llama.cpp)

A follow-up learning project (Nov 6–11, 2026) to understand how an LLM agent is wired: a chat
assistant that answers questions about the 500 harvested items by calling the code above as
tools, in a ReAct loop (the model picks a tool, reads its result, repeats, then answers). It
runs entirely on my own machine. Like the rest of this repo, it is a learning project on public
data, not USGS work, and not production software.

### What I built

- **Local model server.** Llama 3.1 8B Instruct (4-bit GGUF) served by `llama-server`
  (llama.cpp) on CPU only (4-core Ryzen 3 1200, 30 GB RAM), through its OpenAI-compatible API,
  so the backend can be swapped by changing one URL.
- **Four tools** (`agent/tools.py`) wrapping the Phase 1 code: `search_items` (embedding
  search), `item_details`, `score_summary` (completeness scores by group) and `find_anomalies`.
  Each returns compact text (at most 1,200 characters), returns a message instead of raising on
  bad input, and caches its data once per process. The four tool schemas the model sees on
  every call total 2,046 characters.
- **The agent graph, written by hand** with LangGraph (`agent/graph.py`, diagram in
  `docs/graph.mermaid`): state with a message reducer and a step counter, an agent node, a tool
  node I wrote myself (unknown tools, bad arguments and tool exceptions become error messages
  the model can act on), a conditional edge, and a step limit (`MAX_STEPS = 4`).
- **Tests without the model.** A scripted fake model drives the graph through direct answers,
  tool round trips, two tool calls in one reply, the three error cases and a looping model.
  The agent's tool and graph tests (28) and the full suite (50) pass.
- **Comparison with the prebuilt agent** (`langchain.agents.create_agent`) on the same model,
  prompt and tools (`agent/compare.py`).

### Results (all from real runs on the machine above)

**Speed is dominated by the model, and by what it has to read.** Benchmark (`agent/bench.py`):

| Case | Read | Write 128 tokens | Total |
|---|---|---|---|
| 1,812-token prompt, cold | 296.6 s (6.1 tokens/s) | 51.5 s (2.5 tokens/s) | 348 s |
| Same prompt, cached prefix | 0.6 s | 54.0 s | 54.6 s |

This set the design rules: a short, fixed system prompt and tool list so they stay cached;
compact tool results, because every new token is read at about 6 tokens/s; capped replies.

**Agent runs:**
- "How many data releases are missing a DOI?" called `find_anomalies` with the right check
  and answered 4, matching the tool output: 99.6 s.
- "Find five items about water use": 52.2 s (choose tool 8.2 s, tool 6.3 s, answer 37.7 s).
  Asking for 5 results instead of 10 cut the answer step from 68 s to 38 s, because the model
  had about half as many new tokens to read (≈204 vs ≈413).

**Hand-built vs. prebuilt agent** ("Give me details on item with ID Gary", 2 warm-up + 3 timed
runs each): both agents made the same 4 model calls with the same tools and arguments, read the
same number of new tokens per call and gave the same answer in every run (temperature 0). Mean
times were 156.0 s (hand-built) and 163.3 s (prebuilt); with identical model work, I read that
as run-to-run noise, not a framework difference.

**Failure modes I saw** (examples, not rates):
- With the tools accidentally not attached to the model, it still answered confidently with a
  made-up count ("123 items found"): a clear hallucination.
- It often described results instead of giving them ("the results are shown above"), even
  though the user never sees tool output, and named tools despite being told not to.
- It sent integer arguments as strings (`"k": "10"`); schema validation quietly converted them.
- A tool's helpful hint misled it: after an unknown id, it searched for that id, took a match
  with similarity 0.18 and reported an unrelated item.

### Limitations and not done

- No systematic accuracy measurement yet: the runs above are a handful of examples. An
  evaluation harness (hand-written cases; right tool, right arguments, numbers grounded in
  tool output) was designed but not implemented or run.
- One small model on a slow CPU; a larger model or a GPU backend was not tested.
- No user interface beyond the command line; no real users.

### Reproduce

```bash
agent/serve.sh                                         # start llama-server (model path inside)
HF_HUB_OFFLINE=1 python agent/graph.py "How many data releases are missing a DOI?"
python agent/compare.py "Give me details on item with ID Gary" --graph custom --iterations 5 --warmupsteps 2
python -m pytest -q tests/test_agent_tools.py tests/test_agent_graph.py
```
