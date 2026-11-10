"""Benchmark performance of local LLM.

Usage:
    python agent/bench.py



"""

import argparse
# import json
import pandas as pd
import re
import time
from pathlib import Path

import requests

BASE_URL = "http://localhost:8080/v1/chat/completions"
MAX_TOKENS = 128


PAUSE_SECONDS = 1.0  # between requests, to be polite
MAX_RETRIES = 4


def fetch_page(session, prompt,do_cache:bool):
    payload = {'messages':[{'role':'user', 'content':prompt}],'max_tokens':MAX_TOKENS,'cache_prompt':do_cache,'stream':False}
    for attempt in range(MAX_RETRIES + 1):
        try:
            resp = session.post (url=BASE_URL, json=payload,timeout=3600)
            if resp.status_code == 429 or resp.status_code >= 500:
                raise requests.HTTPError(f"HTTP {resp.status_code}", response=resp)
            resp.raise_for_status()  # other 4xx: a real bug, fail immediately
            return resp.json()
        except (requests.ConnectionError, requests.Timeout, requests.HTTPError) as err:
            retryable = not isinstance(err, requests.HTTPError) or (
                err.response is not None
                and (err.response.status_code == 429 or err.response.status_code >= 500)
            )
            if not retryable or attempt == MAX_RETRIES:
                raise
            wait = 2 ** attempt * 5  # 5, 10, 20, 40 s
            # print(f"  offset {offset}: {err}; retrying in {wait}s")
            time.sleep(wait)


def do_bench(prompt_filename,  out_root):

    session = requests.Session()
    session.headers["Content-Type"] = "application/json"
    benchmark_rows =[]
    scenario = 0
    # let's cache the 3rd scenario
    cache_scenarios = [3]
    with open(prompt_filename, 'r') as infile:
        for line in infile:
            scenario+=1
            benchmark = {}
            prompt = line.strip()
            do_cache = scenario in cache_scenarios
            benchmark['scenario'] = scenario
            benchmark['prompt_chars'] = len(prompt)
            print(f"prompt {prompt}")
            fetch_start = time.perf_counter()
            response = fetch_page(session,prompt,do_cache)
            fetch_end = time.perf_counter()
            benchmark['server_response_time'] = fetch_end-fetch_start
            # timings = response['timings']
            for k,v in response['timings'].items():
                benchmark['timings_'+k] = v
            for k,v in response['usage'].items():
                benchmark['usage_' + k] = v
            benchmark_rows.append(benchmark)
    df = pd.DataFrame(benchmark_rows)
    OUT_PATH = out_root / "derived/llm_timings.csv"
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_PATH, index=False)
    print(f"Wrote {len(df)} rows to {OUT_PATH}")





def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--prompt_filename", required=True, help="Each line of the file is one prompt")
    parser.add_argument("--out", type=Path, default=Path("data"),help="A table of benchmarks will be written here")
    args = parser.parse_args()
    do_bench(prompt_filename = args.prompt_filename,  out_root = args.out)


if __name__ == "__main__":
    main()
