import csv
import json
import os
import sys
import time
from pathlib import Path
import signal

TSV_PATH = Path(__file__).parent.parent / "data" / "morph_data.tsv"
CACHE_PATH = Path(__file__).parent.parent / "data" / "pronunciation_cache.json"

BATCH_SAVE_SIZE = 2000

def load_cache():
    if CACHE_PATH.exists():
        try:
            with open(CACHE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading main cache: {e}.")

    temp_path = CACHE_PATH.with_suffix(".tmp")
    if temp_path.exists():
        try:
            print("Attempting to recover cache from temporary file...")
            with open(temp_path, "r", encoding="utf-8") as f:
                data = json.load(f)
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
            writer.writerow(["Wordsss", "umLabeller_seg", "Citylex_seg", "Frequency", "Pronunciation"])
            
            for row in all_rows:
                word, uml_seg, city_seg, freq, _ = row
                pron = cache.get(word, "")
                writer.writerow([word, uml_seg, city_seg, freq, pron])
            f.flush()
            os.fsync(f.fileno())

        os.replace(temp_tsv, TSV_PATH)
    except Exception as e:
        print(f"Error writing TSV: {e}")

def load_cmu_dictionaries():
    print("Loading CMU Pronouncing Dictionaries...")
    cmu_dict = {}
    
    # 1. Load from local cmudict-0.7b.txt
    local_path = Path(r"E:\NLWL\Phonics\cmudict-0.7b.txt")
    if local_path.exists():
        try:
            with open(local_path, "r", encoding="latin-1") as f:
                for line in f:
                    if line.startswith(";;;") or "  " not in line:
                        continue
                    parts = line.strip().split("  ", 1)
                    word_key = parts[0].strip().lower()
                    if "(" in word_key and word_key.endswith(")"):
                        word_key = word_key.split("(", 1)[0].strip()
                    pron = parts[1].strip()
                    if word_key not in cmu_dict:
                        cmu_dict[word_key] = pron
            print(f"Loaded {len(cmu_dict)} entries from local cmudict-0.7b.txt.")
        except Exception as e:
            print(f"Warning: Failed to load local CMUDict: {e}")
    else:
        print("Local cmudict-0.7b.txt not found.")

    # 2. Load from NLTK cmudict dict (fallback / merge)
    try:
        from nltk.corpus import cmudict
        nltk_dict = cmudict.dict()
        nltk_loaded = 0
        for word_key, prons in nltk_dict.items():
            if word_key not in cmu_dict and prons:
                pron = " ".join(prons[0])
                cmu_dict[word_key] = pron
                nltk_loaded += 1
        if nltk_loaded > 0:
            print(f"Loaded {nltk_loaded} additional entries from NLTK CMUDict.")
    except Exception as e:
        print(f"Warning: Failed to load NLTK CMUDict: {e}")

    return cmu_dict

def main():
    if not TSV_PATH.exists():
        print(f"Source file not found: {TSV_PATH}")
        sys.exit(1)

    print("Reading morph_data.tsv...")
    all_rows = []
    
    with open(TSV_PATH, "r", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter="\t")
        header = next(reader)
        # Check if the header already has 5 columns (Pronunciation)
        has_pron_col = len(header) >= 5 and header[4] == "Pronunciation"
        
        for row in reader:
            if not row:
                continue
            word = row[0]
            uml_seg = row[1] if len(row) > 1 else ""
            city_seg = row[2] if len(row) > 2 else ""
            freq = row[3] if len(row) > 3 else ""
            pron = row[4] if len(row) > 4 and has_pron_col else ""
            
            all_rows.append([word, uml_seg, city_seg, freq, pron])

    cache = load_cache()
    print(f"Loaded cache with {len(cache)} entries.")
    
    # Merge existing pronunciations from morph_data.tsv into cache (self-healing)
    merged_count = 0
    for row in all_rows:
        word, _, _, _, pron = row
        if pron != "" and word not in cache:
            cache[word] = pron
            merged_count += 1
    if merged_count > 0:
        print(f"Merged {merged_count} pronunciations from morph_data.tsv into cache.")
        save_cache(cache)
    
    # Sync initial cache to TSV
    if cache:
        print("Syncing initial cache to morph_data.tsv...")
        write_tsv(all_rows, cache)
    
    # Filter words that actually need to be fetched
    pending_words = [row[0] for row in all_rows if row[0] not in cache]
    total_to_fetch = len(pending_words)
    print(f"Total words in dataset: {len(all_rows)}")
    print(f"Already cached: {len(all_rows) - total_to_fetch}")
    print(f"Pending fetch/prediction: {total_to_fetch}")
    
    # Define signal handler for Ctrl+C shutdown
    def handle_sigint(sig, frame):
        print("\nProcess interrupted by user (Ctrl+C). Saving progress...")
        try:
            save_cache(cache)
            write_tsv(all_rows, cache)
            print("Progress saved successfully. Exiting.")
        except Exception as e:
            print(f"Error during shutdown save: {e}")
        os._exit(0)

    signal.signal(signal.SIGINT, handle_sigint)

    if total_to_fetch == 0:
        print("All pronunciations are already cached.")
        return

    # Load dictionaries
    cmu_dict = load_cmu_dictionaries()

    print("Starting pronunciation extraction...")
    completed = 0
    g2p = None  # Lazy load G2P only if needed for non-CMU words
    
    t0 = time.time()
    for word in pending_words:
        pron = None
        
        # 1. Try CMUDict first (very fast)
        if word.lower() in cmu_dict:
            pron = cmu_dict[word.lower()]
        else:
            # 2. Try G2p on-the-fly (python library)
            if g2p is None:
                print("Initializing g2p_en model for out-of-vocabulary words...")
                from g2p_en import G2p
                g2p = G2p()
            
            try:
                phonemes = g2p(word)
                pron = " ".join([p for p in phonemes if p.strip()])
            except Exception as e:
                print(f"Error predicting pronunciation for {word}: {e}")
                pron = ""

        if pron is not None:
            cache[word] = pron
            
        completed += 1
        
        if completed % 100 == 0 or completed == total_to_fetch:
            elapsed = time.time() - t0
            speed = completed / elapsed if elapsed > 0 else 0
            print(f"Progress: {completed}/{total_to_fetch} ({(completed/total_to_fetch)*100:.2f}%) - Speed: {speed:.1f} w/s - {time.strftime('%Y-%m-%d %H:%M:%S')}")
            
        # Incremental save to cache only (fast)
        if completed % BATCH_SAVE_SIZE == 0:
            save_cache(cache)

    # Final save and sync to TSV
    print("Fetch complete. Saving final cache and syncing to morph_data.tsv...")
    save_cache(cache)
    write_tsv(all_rows, cache)
    print("morph_data.tsv is fully up-to-date with pronunciations!")

if __name__ == "__main__":
    main()
