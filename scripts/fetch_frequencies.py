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
import signal

TSV_PATH = Path(__file__).parent.parent / "data" / "morph_data.tsv"
CACHE_PATH = Path(__file__).parent.parent / "data" / "frequency_cache.json"

MAX_WORKERS = 20
BATCH_SAVE_SIZE = 100

def get_word_frequency(word, session=None):
    url = f"https://api.datamuse.com/words?sp={word}&md=f&max=1"
    caller = session if session is not None else requests
    for attempt in range(3):
        try:
            r = caller.get(url, timeout=5)
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
    return None

def load_cache():
    # Check main cache file first
    if CACHE_PATH.exists():
        try:
            with open(CACHE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading main cache: {e}.")

    # Fallback to temp file if main cache is corrupted/missing
    temp_path = CACHE_PATH.with_suffix(".tmp")
    if temp_path.exists():
        try:
            print("Attempting to recover cache from temporary file...")
            with open(temp_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Try to restore main cache from valid temp file
            os.replace(temp_path, CACHE_PATH)
            print("Successfully recovered cache from temp file.")
            return data
        except Exception as e:
            print(f"Error loading temp cache: {e}.")

    print("Starting with empty cache.")
    return {}

def save_cache(cache):
    temp_path = CACHE_PATH.with_suffix(".tmp")
    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_path, CACHE_PATH)
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
                if freq is not None and freq != "":
                    freq = str(freq)
                else:
                    freq = ""
                writer.writerow([word, uml_seg, city_seg, freq])
            f.flush()
            os.fsync(f.fileno())

        os.replace(temp_tsv, TSV_PATH)
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
            # Only fetch if it is NOT a CityLex word
            if not city_seg.strip():
                words_to_fetch.append(word)

    cache = load_cache()
    print(f"Loaded cache with {len(cache)} entries.")
    
    # Merge existing frequencies from morph_data.tsv into cache (self-healing)
    merged_count = 0
    for row in all_rows:
        word, _, _, freq = row
        if freq != "" and word not in cache:
            try:
                cache[word] = float(freq)
                merged_count += 1
            except ValueError:
                pass
    if merged_count > 0:
        print(f"Merged {merged_count} frequencies from morph_data.tsv into cache.")
        save_cache(cache)
    
    # Sync initial cache to TSV
    if cache:
        print("Syncing initial cache to morph_data.tsv...")
        write_tsv(all_rows, cache)
    
    # Filter words that actually need to be fetched
    pending_words = [w for w in words_to_fetch if w not in cache]
    total_to_fetch = len(pending_words)
    print(f"Total target words (umLabeller-only): {len(words_to_fetch)}")
    print(f"Already cached: {len(words_to_fetch) - total_to_fetch}")
    print(f"Pending fetch: {total_to_fetch}")
    
    # Define signal handler for instant and clean Ctrl+C shutdown
    def handle_sigint(sig, frame):
        print("\nFetch interrupted by user (Ctrl+C). Saving progress...")
        try:
            save_cache(cache)
            write_tsv(all_rows, cache)
            print("Progress saved successfully. Exiting immediately.")
        except Exception as e:
            print(f"Error during shutdown save: {e}")
        os._exit(0)

    signal.signal(signal.SIGINT, handle_sigint)

    if total_to_fetch == 0:
        print("All frequencies are already cached.")
    else:
        print(f"Starting fetch using {MAX_WORKERS} threads...")
        completed = 0
        batch_size = 2000
        
        # Create a requests Session with a connection pool matching the thread count
        session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(pool_connections=MAX_WORKERS, pool_maxsize=MAX_WORKERS)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        
        try:
            for i in range(0, total_to_fetch, batch_size):
                chunk = pending_words[i:i + batch_size]
                
                with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                    futures = {executor.submit(get_word_frequency, w, session): w for w in chunk}
                    
                    for future in as_completed(futures):
                        word = futures[future]
                        try:
                            freq = future.result()
                            if freq is not None:
                                cache[word] = freq
                        except Exception:
                            pass
                            
                        completed += 1
                        if completed % 100 == 0 or completed == total_to_fetch:
                            print(f"Progress: {completed}/{total_to_fetch} ({(completed/total_to_fetch)*100:.2f}%) - {time.strftime('%Y-%m-%d %H:%M:%S')}")
                
                # Save chunk progress to cache only (fast JSON save, no TSV write)
                save_cache(cache)
        finally:
            session.close()
            
        print("Fetch complete. Saving final cache and syncing to morph_data.tsv...")
        save_cache(cache)
        write_tsv(all_rows, cache)

    print("morph_data.tsv is fully up-to-date!")

if __name__ == "__main__":
    main()
