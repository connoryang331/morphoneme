# morph-query

[English](README.md) | [简体中文](README_zh.md)

Search English words by morphological annotation columns.

A morphological query tool based on the **umLabeller** and **CityLex** morpheme-annotation datasets. Search by prefix, suffix, root, derivational suffix, or inflectional suffix. Get morpheme segmentation, full morphological structure analysis, and batch processing.

## Data Sources

This tool is a query front-end for two publicly available morphological annotation datasets. The data is used **as-is, without any modifications**. The author of this tool does not alter, correct, or enrich the source data in any way.

### umLabeller (UniMorph)

- **Source:** [github.com/unimorph/umLabeller](https://github.com/unimorph/umLabeller/tree/main/data)
- **Local file:** `data/eng.word.full.230613.r7_morphologic_division.tsv` — 4 columns, ~611k rows
- License and terms of use follow the UniMorph project.

### CityLex

- **Source:** [citylex.onrender.com](https://citylex.onrender.com/)
- **Local file:** `data/citylex-2026-06-15_morphology_segmention.tsv` — 3 columns, ~68k rows
- License and terms of use follow the CityLex project.

### Disclaimer

The morphological annotations in these datasets are provided by their respective projects. **No guarantee of correctness is made.** If the source data contains errors or inconsistencies, query results will reflect those issues. Use at your own discretion.

## Installation

```bash
pip install morph-query
```

Use the `mq` command after installation.

### Local Development

```bash
git clone https://github.com/connoryang331/morph-query
cd morph-query
pip install -e .
```

If you are developing locally, you can build the database yourself from the raw TSV files:

```bash
python scripts/build_morph_query_db.py
```

This compiles both the primary `words` table and an indexed `word_morphemes` relation table for sub-millisecond morpheme queries.

### Database Auto-download & Storage

To keep the installation package lightweight, the SQLite database (`morph_query.db`, ~50MB) is **not** bundled in the PyPI distribution.

When you instantiate the `MQ` class or run the CLI for the first time:
1. It looks for a bundled database in the package directory (used for local development).
2. If not found, it checks `~/.morph_query/morph_query.db`.
3. If still missing, it **automatically downloads** a pre-compiled database zip from GitHub Releases and extracts it to `~/.morph_query/`.

No manual configuration is required.

## CLI Usage


Invoke via the `mq` command:

```bash
mq <cmd> <arg> [source] [seg] [--json] [--exclude-inf] [--exclude=STR] [--exact] [--limit=N] [--fq=VAL]
```

Or directly via the Python module:

```bash
python -m morph_query <cmd> <arg> [source] [seg] [--json] [--exclude-inf] [--exclude=STR] [--exact] [--limit=N] [--fq=VAL]
```

### Search Commands

| Command         | Description                                                |
| --------------- | ---------------------------------------------------------- |
| `search`        | Search words matching a pattern. Supports wildcards `*` (e.g. `*ough`, `ough*`) |
| `prefix`        | Return words that contain the given prefix                 |
| `suffix`        | Return words that contain the given suffix                 |
| `root`          | Return words that contain the given root                   |
| `deri_suffix`   | Return words that contain the given derivational suffix    |
| `inf_suffix`    | Return words that contain the given inflectional suffix    |
| `count`         | Lightweight count, returns only the number                 |
| `sample`        | Random sampling                                            |

All search commands query **both umLabeller and CityLex datasets merged** by default. Use the `source` parameter to search only one dataset.

> [!TIP]
> The `search` command supports three wildcard matching styles using `*`:
> - `*str` (e.g. `*ough`) — Matches words ending with `str`.
> - `str*` (e.g. `ough*`) — Matches words starting with `str`.
> - `*str*` or `str` (e.g. `*ough*` or `ough`) — Matches words containing `str` anywhere (default behavior).



### Morphology Analysis Commands

| Command                | Description                                                   |
| ---------------------- | ------------------------------------------------------------- |
| `morph_seg` / `word`   | Return morpheme segmentation as a `-`-joined string           |
| `morph_count`          | Return the number of morphemes in the word                    |
| `word_morph`           | Return full morphological structure (JSON, both datasets)     |
| `lemma`                | Return lemma by stripping inflectional suffixes               |

### Parameters

| Parameter        | Description                                                    |
| ---------------- | -------------------------------------------------------------- |
| `source`         | `both` (default) \| `umlabeller` \| `citylex`                 |
| `seg`            | `both` (default) \| `umlabeller` \| `citylex`                 |
| `--json`         | JSON output                                                    |
| `--exclude-inf`  | Exclude results with inflectional suffixes                     |
| `--exclude=S1,S2`| Exclude results containing any of the comma-separated strings (case-insensitive) |
| `--exact`        | Match exact morpheme instead of substring (for `search` cmd)  |
| `--limit=N`      | Limit number of results returned                               |
| `--fq=VAL`       | Filter results by frequency tier: `high` (>=5.0), `medium` (>=1.0 and <5.0), `low` (<1.0). **Note**: Words with missing frequency data (`NULL`) are **never** filtered out in any tier. |

### Examples

```bash
# Search for words containing "ion"
$ mq search ion
Found 29553 results (source=both, seg=both):
  abbreviation      umlabeller=abbreviate @@ion     citylex={a--bbrevi--ate}>ion>
  abdication        umlabeller=abdicate @@ion       citylex={abdicate}>ion>
  abduction         umlabeller=abduce @@t @@ion     citylex={ab--duct}>ion>
  aberration        umlabeller=aberrate @@ion       citylex={aberr--ate}>ion>
  ... and 29549 more

# Search using wildcards (e.g. find words ending with "ough")
$ mq search *ough
Found 107 results (source=both, seg=both):
  rough             umlabeller=rough                citylex={rough}
  cough             umlabeller=cough                citylex={cough}
  ... and 105 more

# Return words that contain the given prefix
$ mq prefix un
Found 33987 results (source=both, seg=both):
  unabandoned       umlabeller=un @@abandon @@ed    citylex=
  unabashed         umlabeller=un @@abash @@ed      citylex=
  unable            umlabeller=un @@able            citylex=
  unabridged        umlabeller=un @@abridge @@ed    citylex=
  ... and 33983 more

# Return words that contain the given derivational suffix
$ mq deri_suffix able
Found 7556 results (source=both, seg=both):
  abandonable       umlabeller=abandon @@able       citylex=
  acceptable        umlabeller=accept @@able        citylex=
  accessible        umlabeller=access @@ible        citylex=
  accountable       umlabeller=account @@able       citylex=
  ... and 7552 more

# Full morphological analysis (JSON)
$ mq word_morph unbelievable --json
{
  "word": "unbelievable",
  "seg": "un-believe-able",
  "prefixes": ["un"],
  "roots": ["believe"],
  "root": "believe",
  "suffixes": ["able"],
  "derivational": ["able"],
  "inflectional": [],
  "base": "believe",
  "lemma": "un-believe-able"
}

# Return lemma by stripping inflectional suffixes
$ mq lemma running
"run"

# Random sampling
$ mq sample 3
Found 3 results (source=both, seg=both):
  flagrance         umlabeller=flagrant @@ce        citylex=
  gangway           umlabeller=gang @@way           citylex={gang}{way}
  excorticated      umlabeller=excorticate @@ed     citylex=

# Query only one dataset with JSON output
$ mq search ion citylex --json
[{"word": "abacination", "citylex": ""}, {"word": "abalienation", "citylex": ""}, ...]

# Exclude inflectional suffixes
$ mq search ion --exclude-inf
Found 19252 results (source=both, seg=both, exclude_inf):
  abbreviation      umlabeller=abbreviate @@ion     citylex={a--bbrevi--ate}>ion>
  abdication        umlabeller=abdicate @@ion       citylex={abdicate}>ion>
  abduction         umlabeller=abduce @@t @@ion     citylex={ab--duct}>ion>
  aberration        umlabeller=aberrate @@ion       citylex={aberr--ate}>ion>
  ... and 19248 more

# Exclude results containing specific strings (e.g. search 'ough' but exclude 'ought')
$ mq search ough --exclude=ought
Found 362 results (source=both, seg=both, exclude=ought):
  rough             umlabeller=rough                citylex={rough}
  tough             umlabeller=tough                citylex={tough}
  ... and 360 more

# Exact morpheme search (matching exact morpheme instead of substring)
$ mq search ch --exact
Found 8 results (source=both, seg=both, exact):
  chad              umlabeller=ch @@have @@ed       citylex={chad}
  cham              umlabeller=ch @@am              citylex=
  ... and 6 more

# Filter results by frequency (e.g. search "ion" but only high-frequency words)
$ mq search ion --fq=high --limit=3
Found 2782 results (source=both, seg=both, fq=high, limit=3):
  abolition                       umlabeller=abolish @@ion                        citylex={abolish}>ion>                    fq=5.33
  abortion                        umlabeller=abort @@ion                          citylex={abort}>ion>                      fq=9.94
  absorption                      umlabeller=absorb @@t @@ion                     citylex={absorb}>t>ion>                   fq=15.02
```

## Python API

```python
from morph_query import MQ

mq = MQ()

# All search methods below are semantic aliases of search()
# — they all do the same LIKE match on morpheme columns
results = mq.search("ion")                      # generic search
results = mq.words_with_prefix("un")            # semantic alias: "prefix"
results = mq.words_with_suffix("ing")           # semantic alias: "suffix"
results = mq.words_with_root("believe")         # semantic alias: "root"
results = mq.words_with_deri("able")            # semantic alias: "deri_suffix"
results = mq.words_with_inf("ed")               # semantic alias: "inf_suffix"

# Morphology analysis
seg = mq.morph_seg("unbelievable")   # → "un-believe-able"
count = mq.morph_count("running")    # → 2
morph = mq.word_morph("cats")        # → full structure dict
lemma = mq.lemma("running")          # → "run"

# Batch processing
mq.batch_words("words.txt", mode="morph", fmt="csv")

# Count
n = mq.word_count("ion")

# Random sample
samples = mq.sample(10)
```

### `word_morph()` Return Structure

```python
{
    "word": "unbelievable",
    "seg": "un-believe-able",
    "prefixes": ["un"],
    "roots": ["believe"],
    "root": "believe",
    "suffixes": ["able"],
    "derivational": ["able"],
    "inflectional": [],
    "base": "believe",
    "lemma": "un-believe-able"
}
```

## Batch Processing

Process words from a file, output JSON or CSV:

```python
mq.batch_words("words.txt", mode="seg", fmt="json")
mq.batch_words("words.txt", mode="morph", fmt="csv")
mq.batch_words("words.txt", mode="morph:ai", fmt="json")  # with AI validation
```

Input file format: one word per line, lines starting with `#` are comments.

## Inflectional Suffixes

The inflectional suffix list lives at `morph_query/inf_suffixes.txt`, one per line (supports `-` prefix). Default values:

```
-s
-ed
-ing
-en
-est
-es
```

Use `--exclude-inf` to filter out results with inflectional suffixes. If the file is missing, the CLI will prompt to generate the default list.

# Why "semantic aliases"?

In `morph-query`, CLI commands like `prefix`, `suffix`, and `root` (and their corresponding Python API methods) are **semantic aliases** of the generic `search` command. Under the hood, they all query the same SQLite database using simple SQL `LIKE` substring queries against the morphological annotation columns. 

The aliases exist to provide a cleaner, more intuitive interface (e.g., `mq prefix un` is more readable than `mq search un`).

### How it differs from Datamuse, Webster, and OneLook

Querying `morph-query` differs fundamentally from doing a wildcard or substring search on online tools like the **Datamuse API**, **Merriam-Webster**, or **OneLook**:

#### 1. Morpheme-Level Matching vs. Surface-Spelling Matching
* **Datamuse / Webster / OneLook:** These platforms perform search matches based purely on the **raw word spelling (orthography)**. If you search for words ending in `ion` (using wildcards like `*ion`), you will match any word that ends with those letters, regardless of whether it's a suffix.
  * *False Positives (Noise):* Searching for suffix `ion` will return words like *onion*, *cushion*, *lion*, and *million*, where `ion` is just part of the root spelling, not a suffix. Similarly, searching for prefix `un*` will return *uncle*, *under*, *union*, and *unit*, where `un` is not a prefix.
* **morph-query:** It queries the **morpheme segmentation columns** (`umlabeller` and `citylex` data columns) in the database, *not* the raw word column.
  * *Precision:* A search for the prefix `un` only matches words where `un` is annotated as a prefix morpheme (e.g., `un @@abandon`), avoiding spelling false positives like *under* or *uncle*.
  * *Noise reduction (but not complete elimination):* While querying annotated morpheme columns significantly reduces noise, it cannot guarantee 100% matching accuracy because the underlying datasets (UniMorph & CityLex) are subject to annotator variations and minor inconsistencies. However, there is a qualitative difference in the noise:
    * *Without morph-query (raw spelling search):* You get **extremely loud and annoying noise** (e.g., hundreds of completely unrelated words matching spelling patterns like `under` or `million`).
    * *With morph-query (morpheme search):* The spelling-based noise is eliminated. Any remaining noise consists of minor annotation inconsistencies in the underlying research datasets—which, compared to spelling-based noise, are **like the gentle song of little birds outside the window**.

#### 2. Local Database vs. External Web APIs
* **Datamuse / Webster / OneLook:** These are remote web services. To use them, you must make HTTP API requests or scrape pages. This introduces network latency, rate limits, dependency on internet connectivity, and potential API key requirements.
* **morph-query:** Operates completely **locally** using a bundled SQLite database compiled from source datasets. It works offline, queries execute in sub-milliseconds, and it is highly suitable for large-scale batch queries.

#### 3. Structured Morphological Output
* **Datamuse / Webster / OneLook:** These tools return plain text definitions, word lists, or synonyms. They do not understand or return the structural components of the word.
* **morph-query:** Provides a structured, parsed breakdown of the word's morphology. It distinguishes between roots, prefixes, derivational suffixes, and inflectional suffixes, allowing you to easily retrieve lemmas, count morphemes, or export full JSON structures.

## Project Structure

```
morph_query/
├── morph_query/                 # Python package (published to PyPI)
│   ├── __init__.py
│   ├── __main__.py              # CLI entry point
│   ├── mq.py                    # Core MQ class
│   ├── morph_query.db           # SQLite database (bundled in package)
│   └── inf_suffixes.txt         # Inflectional suffix list
├── data/
│   ├── citylex-2026-06-15_morphology_segmention.tsv      # CityLex raw data (~68k rows)
│   ├── eng.word.full.230613.r7_morphologic_division.tsv  # umLabeller raw data (~611k rows)
│   └── morph_data.tsv           # Merged TSV (build source)
├── scripts/
│   └── build_morph_query_db.py  # Build database from TSV
├── tests/
│   ├── __init__.py
│   └── test_mq.py
├── pyproject.toml
├── Makefile
├── requirements.txt
├── LICENSE
└── README.md
```

## Roadmap

We plan to support the following features in future releases:

- **Word Frequency Integration**: Include word frequency metrics (e.g., from COCA, Google Web 1T, or Subtlex) to allow sorting and filtering by word popularity.
- **Part-of-Speech (POS) Support**: Integrate POS tags (e.g., noun, verb, adjective) to filter search results by syntactic categories.
- **IPA, Phonetic Transcriptions & Syllables**:
  - **IPA (International Phonetic Alphabet)**: Add standard IPA transcriptions for pronunciation lookups.
  - **ARPAbet / CMUDict Support**: Support machine-readable phonetic transcriptions (e.g., `S T ER1` representing ARPAbet phoneme sequences).
  - **Syllable Metrics**: Add syllable count and syllabification details (stress patterns).
- **Etymology & Word Origins**:
  - **Bilingual Etymological Data**: Provide historical origins and development paths of English words in both English and Chinese (e.g., source languages, historical semantic shifts, and cognates).
- **Definitions & Explanations**:
  - **Bilingual Word Meanings**: Integrate dictionary definitions and explanations in both English and Chinese to serve as a fast and comprehensive vocabulary learning tool.

## Feedback & Requests

If you have any feature requests, bug reports, or suggestions, feel free to open an issue on the [GitHub Issues](https://github.com/connoryang331/morph-query/issues) page.

## License

MIT

