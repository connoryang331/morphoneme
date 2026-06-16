"""
Fetch word frequencies from Datamuse API for words with CityLex values,
and add them as a new column to morph_data.tsv.
"""

import csv
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import requests

TSV_PATH = Path(__file__).parent.parent / "data" / "morph_data.tsv"
CACHE_PATH = Path(__file__).parent.parent / "data" / "frequency_cache.json"

MAX_WORKERS = 20
BATCH_SAVE_SIZE = 100

def get_word_frequency(word):
    url = f"https://api.datamuse.com/words?sp={word}&md=f&max=1"
    for attempt in range(3):
        try:
            r = requests.get(url, timeout=5)
            if r.status_code == 429:
                # Rate limited, backoff
                time.sleep(2 * (attempt + 1))
                continue
            r.raise_for_status()
            data = r.json()
            if data and "tags" in data[0]:
                for tag in data[0]["tags"]:
                    if tag.startswith("f:"):
                        return float(tag.split(":")[1])
            return 0.0
        except Exception as e:
            time.sleep(1)
    return 0.0

def load_cache():
    if CACHE_PATH.exists():
        try:
            with open(CACHE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading cache: {e}. Starting fresh.")
    return {}

def save_cache(cache):
    temp_path = CACHE_PATH.with_suffix(".tmp")
    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
        if temp_path.exists():
            if CACHE_PATH.exists():
                os.remove(CACHE_PATH)
            os.rename(temp_path, CACHE_PATH)
    except Exception as e:
        print(f"Error saving cache: {e}")

def write_tsv(all_rows, cache):
    temp_tsv = TSV_PATH.with_suffix(".tmp_tsv")
    try:
        with open(temp_tsv, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f, delimiter="\t")
            writer.writerow(["Wordsss", "umLabeller_seg", "Citylex_seg", "Frequency"])
            
            for row in all_rows:
                word, uml_seg, city_seg, _ = row
                freq = cache.get(word, "")
                if freq != "":
                    freq = str(freq)
                writer.writerow([word, uml_seg, city_seg, freq])

        if temp_tsv.exists():
            if TSV_PATH.exists():
                os.remove(TSV_PATH)
            os.rename(temp_tsv, TSV_PATH)
    except Exception as e:
        print(f"Error writing TSV: {e}")

def main():
    if not TSV_PATH.exists():
        print(f"Source file not found: {TSV_PATH}")
        sys.exit(1)

    print("Reading morph_data.tsv...")
    words_to_fetch = []
    all_rows = []
    
    with open(TSV_PATH, "r", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter="\t")
        header = next(reader)
        # Check if the header already has 4 columns (Frequency)
        has_freq_col = len(header) >= 4 and header[3] == "Frequency"
        
        for row in reader:
            if not row:
                continue
            word = row[0]
            uml_seg = row[1] if len(row) > 1 else ""
            city_seg = row[2] if len(row) > 2 else ""
            freq = row[3] if len(row) > 3 and has_freq_col else ""
            
            all_rows.append([word, uml_seg, city_seg, freq])
            # Fetch all words
            words_to_fetch.append(word)

    cache = load_cache()
    print(f"Loaded cache with {len(cache)} entries.")
    
    # Sync initial cache to TSV
    if cache:
        print("Syncing initial cache to morph_data.tsv...")
        write_tsv(all_rows, cache)
    
    # Filter words that actually need to be fetched
    pending_words = [w for w in words_to_fetch if w not in cache]
    total_to_fetch = len(pending_words)
    print(f"Total words with CityLex: {len(words_to_fetch)}")
    print(f"Already cached: {len(words_to_fetch) - total_to_fetch}")
    print(f"Pending fetch: {total_to_fetch}")
    
    if total_to_fetch == 0:
        print("All frequencies are already cached.")
    else:
        print(f"Starting fetch using {MAX_WORKERS} threads...")
        completed = 0
        batch_unsaved = 0
        
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {executor.submit(get_word_frequency, w): w for w in pending_words}
            
            for future in as_completed(futures):
                word = futures[future]
                try:
                    freq = future.result()
                    cache[word] = freq
                except Exception as e:
                    cache[word] = 0.0
                    
                completed += 1
                batch_unsaved += 1
                
                if completed % 100 == 0 or completed == total_to_fetch:
                    print(f"Progress: {completed}/{total_to_fetch} ({(completed/total_to_fetch)*100:.2f}%)")
                    
                if batch_unsaved >= BATCH_SAVE_SIZE:
                    save_cache(cache)
                    batch_unsaved = 0

                # Periodically sync to TSV file every 1000 items
                if completed % 1000 == 0 or completed == total_to_fetch:
                    print(f"Syncing frequencies to morph_data.tsv (completed: {completed})...")
                    write_tsv(all_rows, cache)
                    
        # Final save
        save_cache(cache)
        print("Fetch complete and cache saved.")

    print("morph_data.tsv is fully up-to-date!")

if __name__ == "__main__":
    main()
