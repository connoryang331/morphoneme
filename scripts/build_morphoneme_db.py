"""Rebuild morphoneme.db from TSV data, including optimized relation table."""
import csv
import sqlite3
import re
from pathlib import Path

TSV = Path(__file__).parent.parent / "data" / "morph_data.tsv"
DB = Path(__file__).parent.parent / "morphoneme" / "morphoneme.db"

def norm_uml(s: str) -> str:
    if not s or not s.strip():
        return ""
    parts = []
    for token in s.split():
        if token.startswith("@@"):
            token = token[2:]
        parts.append(token)
    return "-".join(parts)

def parse_citylex(city: str) -> tuple[list[str], list[str], list[str]]:
    if not city:
        return [], [], []

    groups = list(re.finditer(r"\{([^}]*)\}", city))
    if not groups:
        return [], [], []

    # text before { → prefixes
    outer_text = city[: groups[0].start()]
    prefixes = [t for t in re.split(r"[<>{}]", outer_text) if t]

    roots: list[str] = []
    suffixes: list[str] = []

    for g in groups:
        segs = g.group(1).split("--")
        if len(segs) == 1:
            roots.append(segs[0])
        elif len(segs) == 2:
            roots.append(segs[0])
            suffixes.append(segs[1])
        else:  # 3+
            prefixes.append(segs[0])
            roots.append(segs[1])
            suffixes.extend(segs[2:])

    # after } → suffixes
    suf_str = city[groups[-1].end() :]
    if suf_str.startswith(">"):
        suf_str = suf_str[1:]
    suffixes.extend(s for s in suf_str.split(">") if s)

    return prefixes, roots, suffixes

def extract_morphemes(rows):
    seen = set()  # avoid duplicate inserts for (word, morpheme, type, source)
    for word, uml, city, *_ in rows:
        if not word or word == "Wordsss":  # skip header
            continue
            
        # Parse umLabeller
        if uml:
            parts = [t for t in norm_uml(uml).split("-") if t]
            if parts:
                root = max(parts, key=len)
                idx = parts.index(root)
                prefixes = parts[:idx]
                roots = [root]
                suffixes = parts[idx + 1 :]
                
                for p in prefixes:
                    key = (word, p, 'prefix', 'umlabeller')
                    if key not in seen:
                        seen.add(key)
                        yield key
                for r in roots:
                    key = (word, r, 'root', 'umlabeller')
                    if key not in seen:
                        seen.add(key)
                        yield key
                for s in suffixes:
                    key = (word, s, 'suffix', 'umlabeller')
                    if key not in seen:
                        seen.add(key)
                        yield key

        # Parse CityLex
        if city:
            prefixes, roots, suffixes = parse_citylex(city)
            for p in prefixes:
                key = (word, p, 'prefix', 'citylex')
                if key not in seen:
                    seen.add(key)
                    yield key
            for r in roots:
                key = (word, r, 'root', 'citylex')
                if key not in seen:
                    seen.add(key)
                    yield key
            for s in suffixes:
                key = (word, s, 'suffix', 'citylex')
                if key not in seen:
                    seen.add(key)
                    yield key

def main():
    print(f"Opening DB: {DB}")
    conn = sqlite3.connect(str(DB))
    
    # Enable WAL mode for faster inserts
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = OFF")
    
    conn.execute("DROP TABLE IF EXISTS words")
    conn.execute("DROP TABLE IF EXISTS word_morphemes")
    
    conn.execute("CREATE TABLE words (word TEXT, umlabeller TEXT, citylex TEXT, frequency REAL)")
    conn.execute("CREATE TABLE word_morphemes (word TEXT, morpheme TEXT, type TEXT, source TEXT)")
    
    print(f"Reading TSV: {TSV}")
    with open(TSV, encoding="utf-8") as f:
        reader = csv.reader(f, delimiter="\t")
        all_rows = []
        for r in reader:
            word = r[0] if len(r) > 0 else ""
            if word == "Wordsss":
                continue  # skip header
            
            freq = None
            if len(r) > 3 and r[3].strip():
                try:
                    freq = float(r[3])
                except ValueError:
                    pass

            all_rows.append((
                word,
                r[1] if len(r) > 1 else "",
                r[2] if len(r) > 2 else "",
                freq
            ))
            
    print(f"Inserting {len(all_rows)} rows into words table...")
    conn.executemany("INSERT INTO words VALUES (?,?,?,?)", all_rows)
    conn.commit()
    
    print("Extracting and inserting morphemes...")
    # Insert in batches to prevent huge memory spikes
    batch = []
    count = 0
    for key in extract_morphemes(all_rows):
        batch.append(key)
        if len(batch) >= 100000:
            conn.executemany("INSERT INTO word_morphemes VALUES (?,?,?,?)", batch)
            conn.commit()
            count += len(batch)
            print(f"Inserted {count} morpheme entries...")
            batch = []
            
    if batch:
        conn.executemany("INSERT INTO word_morphemes VALUES (?,?,?,?)", batch)
        conn.commit()
        count += len(batch)
        print(f"Inserted {count} morpheme entries...")
        
    print("Creating indexes...")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_word ON words(word)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_morpheme ON word_morphemes(morpheme, type, source)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_morpheme_word ON word_morphemes(word)")
    conn.commit()
    print("Database build complete!")

if __name__ == "__main__":
    main()
