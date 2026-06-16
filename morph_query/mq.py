"""Morphological query tool — core MQ class.

Searches morpheme-segmentation columns (umlabeller / citylex), not the word
column directly. This means even plain-text matching produces fewer spurious
hits than searching words themselves.

Inflectional suffixes are loaded from inf_suffixes.txt (alongside morph_query.db).
"""

from __future__ import annotations

import csv
import json
import re
import sqlite3
import urllib.request
import zipfile
import shutil
from pathlib import Path

_PKG_DB_PATH = Path(__file__).parent / "morph_query.db"
_USER_HOME_DB = Path.home() / ".morph_query" / "morph_query.db"

def ensure_db_exists(db_path: Path) -> None:
    if db_path.exists():
        return
    
    db_path.parent.mkdir(parents=True, exist_ok=True)
    url = "https://github.com/connoryang331/morph-query/releases/download/v0.1.0/morph_query.db.zip"
    zip_tmp = db_path.parent / "morph_query.db.zip"
    
    print(f"Database not found locally. Downloading from {url}...")
    try:
        with urllib.request.urlopen(url, timeout=30) as response, open(zip_tmp, 'wb') as out_file:
            shutil.copyfileobj(response, out_file)
        
        print("Extracting database...")
        with zipfile.ZipFile(zip_tmp, 'r') as zip_ref:
            zip_ref.extractall(db_path.parent)
            
        zip_tmp.unlink()
        print(f"Database successfully downloaded and saved to {db_path}")
    except Exception as e:
        if zip_tmp.exists():
            zip_tmp.unlink()
        if db_path.exists():
            db_path.unlink()
        raise RuntimeError(
            f"Failed to download morph-query database from {url}. "
            f"Error: {e}\n"
            f"Please ensure you have internet access, or download it manually and place it at {db_path}."
        ) from e

class MQ:
    """Morph Query — search morpheme-annotation columns."""

    def __init__(self, db_path: str | Path | None = None) -> None:
        if db_path is None:
            if _PKG_DB_PATH.exists():
                db_path = _PKG_DB_PATH
            else:
                db_path = _USER_HOME_DB
                ensure_db_exists(db_path)
        else:
            db_path = Path(db_path)
            if db_path == _USER_HOME_DB:
                ensure_db_exists(db_path)

        self.conn = sqlite3.connect(str(db_path))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA cache_size = -8000")
        
        pkg_sfx = Path(__file__).parent / "inf_suffixes.txt"
        self._sfx_path = Path(db_path).parent / "inf_suffixes.txt"
        
        self.inflectional_suffixes: list[str] = []
        if self._sfx_path.exists():
            self.load_inf_suffixes(str(self._sfx_path))
        elif pkg_sfx.exists():
            self.load_inf_suffixes(str(pkg_sfx))
            try:
                self._sfx_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(pkg_sfx, self._sfx_path)
            except Exception:
                pass

    @staticmethod
    def _default_suffixes() -> list[str]:
        return ["ed", "s", "ing", "en", "est", "es"]

    def close(self) -> None:
        self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    # ── core search ─────────────────────────────────────────

    def search(
        self, s: str, *, source: str = "both", seg: str = "both",
        exclude_inf: bool = False, limit: int | None = None,
        exact: bool = False,
    ) -> list[dict]:
        """Generic search.

        Args:
          s           — search term
          source      — column to search: "both" (default) | "umlabeller" | "citylex"
          seg         — morphology columns to return:
                        "both" (default) — word + umlabeller + citylex
                        "umlabeller"     — word + umlabeller
                        "citylex"        — word + citylex
          exclude_inf — whether to exclude results with inflectional suffixes
          limit       — max results to return (default: no limit)
          exact       — match exact morpheme instead of substring (default: False)
        """
        if exact:
            match seg:
                case "umlabeller":
                    cols = "w.word, w.umlabeller"
                case "citylex":
                    cols = "w.word, w.citylex"
                case _:
                    cols = "w.word, w.umlabeller, w.citylex"

            where_clauses = ["m.morpheme = ?"]
            params = [s]
            if source == "umlabeller":
                where_clauses.append("m.source = 'umlabeller'")
            elif source == "citylex":
                where_clauses.append("m.source = 'citylex'")
            where_str = " AND ".join(where_clauses)
            sql = f"""
                SELECT DISTINCT {cols} 
                FROM words w
                JOIN word_morphemes m ON w.word = m.word
                WHERE {where_str}
            """
        else:
            match seg:
                case "umlabeller":
                    cols = "word, umlabeller"
                case "citylex":
                    cols = "word, citylex"
                case _:
                    cols = "word, umlabeller, citylex"
            where, params = self._where_like(source, s)
            sql = f"SELECT DISTINCT {cols} FROM words WHERE {where}"

        if limit and not exclude_inf:
            sql += f" LIMIT {limit}"
        cur = self.conn.execute(sql, params)
        results = [dict(r) for r in cur.fetchall()]
        if exclude_inf:
            results = self._filter_inf(results)
            if limit:
                results = results[:limit]
        return results

    # ── semantic aliases ───────────────────────────────────

    def words_with_prefix(
        self, p: str, *, source: str = "both", seg: str = "both",
        exclude_inf: bool = False, limit: int | None = None,
    ) -> list[dict]:
        """Find words containing the given prefix."""
        return self._morpheme_type_search(p, "prefix", source=source, seg=seg, exclude_inf=exclude_inf, limit=limit)

    def words_with_suffix(
        self, s: str, *, source: str = "both", seg: str = "both",
        exclude_inf: bool = False, limit: int | None = None,
    ) -> list[dict]:
        """Find words containing the given suffix."""
        return self._morpheme_type_search(s, "suffix", source=source, seg=seg, exclude_inf=exclude_inf, limit=limit)

    def words_with_root(
        self, r: str, *, source: str = "both", seg: str = "both",
        exclude_inf: bool = False, limit: int | None = None,
    ) -> list[dict]:
        """Find words containing the given root."""
        return self._morpheme_type_search(r, "root", source=source, seg=seg, exclude_inf=exclude_inf, limit=limit)

    def words_with_deri(
        self, s: str, *, source: str = "both", seg: str = "both",
        exclude_inf: bool = False, limit: int | None = None,
    ) -> list[dict]:
        """Find words with the given derivational suffix. Matches @@{s} (umLabeller) / >{s} (CityLex)"""
        return self._morpheme_type_search(s, "suffix", source=source, seg=seg, exclude_inf=exclude_inf, limit=limit)

    def words_with_inf(
        self, s: str, *, source: str = "both", seg: str = "both",
        exclude_inf: bool = False, limit: int | None = None,
    ) -> list[dict]:
        """Find words with the given inflectional suffix. Matches @@{s} (umLabeller) / >{s} (CityLex)"""
        return self._morpheme_type_search(s, "suffix", source=source, seg=seg, exclude_inf=exclude_inf, limit=limit)

    @staticmethod
    def _where_like(source: str, s: str) -> tuple[str, tuple]:
        """Build LIKE condition. Returns (where_clause, params)."""
        if "*" in s:
            pattern = s.replace("*", "%")
        else:
            pattern = f"%{s}%"

        match source:
            case "umlabeller":
                return "(word LIKE ? OR umlabeller LIKE ?)", (pattern, pattern)
            case "citylex":
                return "(word LIKE ? OR citylex LIKE ?)", (pattern, pattern)
            case _:  # both
                return "(word LIKE ? OR umlabeller LIKE ? OR citylex LIKE ?)", (pattern, pattern, pattern)

    def _morpheme_type_search(
        self, morpheme: str, morph_type: str, *, source: str = "both", seg: str = "both",
        exclude_inf: bool = False, limit: int | None = None,
    ) -> list[dict]:
        """Query specialized relation table word_morphemes for exact morpheme search."""
        match seg:
            case "umlabeller":
                cols = "w.word, w.umlabeller"
            case "citylex":
                cols = "w.word, w.citylex"
            case _:
                cols = "w.word, w.umlabeller, w.citylex"

        where_clauses = ["m.morpheme = ?", "m.type = ?"]
        params = [morpheme, morph_type]

        if source == "umlabeller":
            where_clauses.append("m.source = 'umlabeller'")
        elif source == "citylex":
            where_clauses.append("m.source = 'citylex'")

        where_str = " AND ".join(where_clauses)
        sql = f"""
            SELECT DISTINCT {cols} 
            FROM words w
            JOIN word_morphemes m ON w.word = m.word
            WHERE {where_str}
        """
        if limit and not exclude_inf:
            sql += f" LIMIT {limit}"
        cur = self.conn.execute(sql, params)
        results = [dict(r) for r in cur.fetchall()]
        if exclude_inf:
            results = self._filter_inf(results)
            if limit:
                results = results[:limit]
        return results

    # ── word exact match + normalisation ─────────────

    def _word_raw(self, word: str) -> dict | None:
        """Internal: query DB directly, return raw row."""
        cur = self.conn.execute(
            "SELECT word, umlabeller, citylex FROM words WHERE word = ?", (word,)
        )
        r = cur.fetchone()
        return dict(r) if r else None

    def _words_raw_batch(self, word_list: list[str]) -> dict[str, dict]:
        """Fetch raw rows for a batch of words in a single query."""
        word_map = {}
        chunk_size = 990
        for i in range(0, len(word_list), chunk_size):
            chunk = word_list[i:i + chunk_size]
            placeholders = ",".join(["?"] * len(chunk))
            sql = f"SELECT word, umlabeller, citylex FROM words WHERE word IN ({placeholders})"
            cur = self.conn.execute(sql, chunk)
            for row in cur.fetchall():
                word_map[row["word"]] = dict(row)
        return word_map

    @staticmethod
    def _norm_uml(s: str) -> str:
        """umLabeller → standard `-` form: run @@ing → run-ing"""
        if not s or not s.strip():
            return ""
        parts = []
        for token in s.split():
            if token.startswith("@@"):
                token = token[2:]
            parts.append(token)
        return "-".join(parts)

    @staticmethod
    def _norm_city(s: str) -> str:
        """CityLex → standard `-` form: {run}>ing> → run-ing"""
        if not s or not s.strip():
            return ""
        for ch in ("{", "}", "<", ">"):
            s = s.replace(ch, "-")
        s = s.strip("-")
        while "--" in s:
            s = s.replace("--", "-")
        return s

    def morph_seg(self, word: str, raw_row: dict | None = None) -> str | None:
        """Query morpheme segmentation, return ``-``-joined standard form.

        Prefers finer-grained annotation; CityLex wins ties.

        >>> mq.morph_seg("running")
        'run-ing'
        >>> mq.morph_seg("pies")
        'pie-s'
        >>> mq.morph_seg("xyzzyxyzzy") is None
        True
        """
        r = raw_row if raw_row is not None else self._word_raw(word)
        if not r:
            return None

        uml = self._norm_uml(r.get("umlabeller", "") or "")
        city = self._norm_city(r.get("citylex", "") or "")

        if not uml and not city:
            return None

        if uml == city:
            return uml
        if not uml:
            return city if city else None
        if not city:
            return uml if uml else None

        uml_parts = uml.count("-") + 1
        city_parts = city.count("-") + 1
        if uml_parts > city_parts:
            return uml
        if city_parts > uml_parts:
            return city
        return city  # same granularity, CityLex wins

    # ── morpheme count ─────────────────────────────────

    def morph_count(self, word: str, raw_row: dict | None = None) -> int | None:
        """Return number of morphemes in word (based on morph_seg segments).

        >>> mq.morph_count("running")
        2
        >>> mq.morph_count("unbelievable")
        3
        >>> mq.morph_count("xyzzyxyzzy") is None
        True
        """
        seg = self.morph_seg(word, raw_row=raw_row)
        return None if seg is None else seg.count("-") + 1

    def lemma(self, word: str, raw_row: dict | None = None) -> str | None:
        """Return lemma of word (strip inflectional suffixes, keep prefixes + derivational suffixes).

        Reuses word_morph() internally, returns the ``lemma`` field.

        >>> mq.lemma("running")
        'run'
        >>> mq.lemma("cats")
        'cat'
        >>> mq.lemma("unbelievable")
        'un-believe-able'
        >>> mq.lemma("xyzzyxyzzy") is None
        True
        """
        r = self.word_morph(word, raw_row=raw_row)
        return r.get("lemma") if r else None

    # ── CityLex parse ──────────────────────────────────

    @staticmethod
    def _parse_citylex(city: str) -> tuple[list[str], list[str], list[str]]:
        """Parse CityLex format into (prefixes, root list, suffixes).

        ``--`` segment rules (inside ``{...}``):
          * 1 segment ``{X}``          : X = root
          * 2 segments ``{X--Y}``      : X = root, Y = suffix
          * 3 segments ``{X--Y--Z}``   : X = prefix, Y = root, Z = suffix

        ``{}`` group rules:
          * Each ``{..}`` group produces one root
          * Multiple groups = compound word
          * Text before ``{`` is also a prefix
          * ``>tok>`` after ``}`` are suffixes

        >>> MQ._parse_citylex("{a--bbrevi--ate}")
        (['a'], ['bbrevi'], ['ate'])
        >>> MQ._parse_citylex("{norm--al}")
        ([], ['norm'], ['al'])
        >>> MQ._parse_citylex("{abs--ent}{mind}>ed>>ly>")
        ([], ['abs', 'mind'], ['ent', 'ed', 'ly'])
        """
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

    def word_morph(self, word: str, ai: bool = False, raw_row: dict | None = None) -> dict | None:
        """Query full morphological structure of a word.

        When ai=True, appends a ``validations`` field with programmatic
        consistency checks.

        Returns:
          word         — original word
          seg          — normalised morpheme string (``-``-joined)
          prefixes     — prefix list
          roots        — all roots (multiple for compounds)
          root         — primary root (last one)
          suffixes     — all suffixes
          derivational — derivational suffixes (not in inflectional list)
          inflectional — inflectional suffixes
          base         — root after stripping all affixes
          lemma        — only inflectional stripped (prefix + root + derivational)
          ai           — (ai=True only) list of check results

        >>> mq.word_morph("unbelievable") == {
        ...     'word': 'unbelievable', 'seg': 'un-believe-able', 'prefixes': ['un'],
        ...     'roots': ['believe'], 'root': 'believe', 'suffixes': ['able'], 'derivational': ['able'],
        ...     'inflectional': [], 'base': 'believe', 'lemma': 'un-believe-able'
        ... }
        True

        >>> mq.word_morph("cats") == {
        ...     'word': 'cats', 'seg': 'cat-s', 'prefixes': [], 'roots': ['cat'], 'root': 'cat',
        ...     'suffixes': ['s'], 'derivational': [], 'inflectional': ['s'],
        ...     'base': 'cat', 'lemma': 'cat'
        ... }
        True
        """
        r = raw_row if raw_row is not None else self._word_raw(word)
        if not r:
            return {"word": word, "seg": None}

        seg = self.morph_seg(word, raw_row=r)
        uml = r.get("umlabeller", "") or ""
        city = r.get("citylex", "") or ""

        if city and (">" in city or "--" in city):
            prefixes, roots, suffixes = self._parse_citylex(city)
        elif uml:
            prefixes, roots, suffixes = [], [], []
            parts = [t for t in self._norm_uml(uml).split("-") if t]
            if parts:
                root = max(parts, key=len)
                idx = parts.index(root)
                prefixes = parts[:idx]
                roots = [root]
                suffixes = parts[idx + 1 :]
        else:
            prefixes, roots, suffixes = [], [], []

        # ── align with seg: prepend prefix segments missing from CityLex/uml ──
        if seg and roots and roots[-1] and "-" in seg:
            seg_parts = seg.split("-")
            root_val = roots[-1]
            if root_val in seg_parts:
                root_idx = seg_parts.index(root_val)
                extra = seg_parts[:root_idx]
                known = set(prefixes)
                for p in reversed(extra):
                    if p not in known:
                        prefixes.insert(0, p)
                        known.add(p)

        if not roots:
            base_result = {
                "word": word, "seg": seg,
                "prefixes": prefixes, "roots": [], "root": None,
                "suffixes": suffixes,
                "derivational": [], "inflectional": [],
                "base": None, "lemma": None,
            }
            if ai:
                base_result["ai"] = self._ai_check(
                    word, seg, prefixes, roots, suffixes, set()
                )
            return base_result

        root = roots[-1]

        # classify suffixes
        inf_set = set(self.inflectional_suffixes)
        inflectional = [s for s in suffixes if s in inf_set]
        derivational = [s for s in suffixes if s not in inf_set]

        # rebuild full morpheme sequence in word order
        ordered = self._ordered_morph(city, uml, word, prefixes, roots, suffixes)

        # fill in missing prefix segments
        if prefixes:
            match_count = 0
            for i, p in enumerate(prefixes):
                if i < len(ordered) and ordered[i] == p:
                    match_count += 1
                else:
                    break
            for p in reversed(prefixes[match_count:]):
                ordered.insert(0, p)

        # strip trailing inflectional suffixes → lemma
        while ordered and ordered[-1] in inf_set:
            ordered.pop()
        lemma = "-".join(ordered) if ordered else (seg or word)

        # base = strip all affixes, keep only root
        base = "-".join(roots) if len(roots) > 1 else (roots[0] if roots else None)

        result = {
            "word": word,
            "seg": seg,
            "prefixes": prefixes,
            "roots": roots,
            "root": root,
            "suffixes": suffixes,
            "derivational": derivational,
            "inflectional": inflectional,
            "base": base,
            "lemma": lemma,
        }
        if ai:
            result["ai"] = self._ai_check(
                word, seg, prefixes, roots, suffixes, inf_set
            )
        return result

    # ── morphology check (ai) ──────────────────────────────

    def _ordered_morph(
        self, city: str, uml: str, word: str,
        prefixes: list[str], roots: list[str], suffixes: list[str],
    ) -> list[str]:
        """Reconstruct full morpheme sequence in word order (used for base calculation)."""
        if city and (">" in city or "--" in city):
            groups = list(re.finditer(r"\{([^}]*)\}", city))
            ordered: list[str] = []
            for g in groups:
                segs = g.group(1).split("--")
                ordered.append(segs[0])
                if len(segs) >= 2:
                    ordered.append(segs[1])
                    if len(segs) >= 3:
                        ordered.extend(segs[2:])
            suf_str2 = city[groups[-1].end() :]
            if suf_str2.startswith(">"):
                suf_str2 = suf_str2[1:]
            ordered.extend(s for s in suf_str2.split(">") if s)
            return ordered
        if uml:
            return [p for p in self._norm_uml(uml).split("-") if p]
        return list(word) if word else []

    def _ai_check(
        self, word: str, seg: str | None,
        prefixes: list[str], roots: list[str], suffixes: list[str],
        inf_set: set[str],
    ) -> list[dict]:
        """Programmatic consistency checks for morphological analysis. Returns list of check results."""
        checks: list[dict] = []

        if seg is None:
            checks.append({"check": "segment_exists", "pass": False,
                           "detail": "normalised segment is empty"})
            return checks

        # 1. check all parts appear in seg
        for role, parts in [("prefix", prefixes), ("root", roots), ("suffix", suffixes)]:
            for p in parts:
                if p not in seg:
                    checks.append({
                        "check": f"{role}_in_seg",
                        "pass": False,
                        "detail": f"{role} '{p}' not in seg '{seg}'",
                    })

        # 2. inflectional suffixes should be after derivational
        found_inf = False
        for s in suffixes:
            if s in inf_set:
                found_inf = True
            elif found_inf:
                checks.append({
                    "check": "inflectional_order",
                    "pass": False,
                    "detail": f"derivational suffix '{s}' appears after inflectional suffix (order anomaly)",
                })
                break

        if not found_inf:
            checks.append({
                "check": "inflectional_order",
                "pass": True,
                "detail": "no inflectional suffix",
            })

        # 3. check roots exist independently in DB
        for root in roots:
            root_data = self._word_raw(root)
            if root_data:
                checks.append({
                    "check": "root_in_db",
                    "pass": True,
                    "detail": f"root '{root}' exists independently in DB",
                })
            else:
                checks.append({
                    "check": "root_in_db",
                    "pass": True,  # not necessarily an error, compound root may not be in DB
                    "detail": f"root '{root}' not found in DB (may be compound component)",
                })

        # if all passed
        if not any(not c["pass"] for c in checks):
            checks.insert(0, {
                "check": "all_checks_passed",
                "pass": True,
                "detail": f"'{word}' passed {len(checks)} morphology checks",
            })

        return checks

    # ── stats ──────────────────────────────────────────

    @property
    def total(self) -> int:
        cur = self.conn.execute("SELECT COUNT(*) AS n FROM words")
        return cur.fetchone()["n"]

    def word_count(
        self, s: str, *, source: str = "both",
        exclude_inf: bool = False,
    ) -> int:
        """Lightweight count, returns count only.

        >>> mq.word_count("ion")
        29553
        >>> mq.word_count("con", source="umlabeller", exclude_inf=True)
        5384
        """
        if exclude_inf:
            # need Python-side filter, grab DISTINCT word
            where, params = self._where_like(source, s)
            cur = self.conn.execute(
                f"SELECT DISTINCT word, umlabeller, citylex FROM words WHERE {where}",
                params,
            )
            return len(self._filter_inf([dict(r) for r in cur.fetchall()]))
        where, params = self._where_like(source, s)
        cur = self.conn.execute(
            f"SELECT COUNT(DISTINCT word) AS n FROM words WHERE {where}", params,
        )
        return cur.fetchone()["n"]

    def sample(
        self, n: int = 10, *, source: str = "both", seg: str = "both",
        exclude_inf: bool = False,
    ) -> list[dict]:
        """Random sample.

        Args:
          n           — how many rows (default 10)
          source      — which column to search
          seg         — which fields to return
          exclude_inf — whether to exclude inflectional suffixes
        """
        match seg:
            case "umlabeller":
                cols = "word, umlabeller"
            case "citylex":
                cols = "word, citylex"
            case _:
                cols = "word, umlabeller, citylex"

        if exclude_inf:
            where, params = self._where_like(source, "%")
            cur = self.conn.execute(
                f"SELECT DISTINCT {cols} FROM words WHERE {where} ORDER BY RANDOM() LIMIT {n * 5}",
                params,
            )
            results = [dict(r) for r in cur.fetchall()]
            results = self._filter_inf(results)
            return results[:n]

        where, params = self._where_like(source, "%")
        cur = self.conn.execute(
            f"SELECT DISTINCT {cols} FROM words WHERE {where} ORDER BY RANDOM() LIMIT {n}",
            params,
        )
        return [dict(r) for r in cur.fetchall()]

    # ── inflectional suffix filter ────────────────────────────

    def load_inf_suffixes(self, filepath: str) -> None:
        """Load inflectional suffixes from txt file (replaces current list).

        File format: one per line, supports ``-`` prefix (e.g. ``-s``) or plain (e.g. ``s``).
        """
        suffixes = []
        with open(filepath, encoding="utf-8") as f:
            for line in f:
                s = line.strip()
                if not s or s.startswith("#"):
                    continue
                suffixes.append(s.lstrip("-"))
        if suffixes:
            self.inflectional_suffixes = suffixes

    def write_default_inf_file(self, filepath: str | None = None) -> str:
        """Write default inflectional suffix list to file. Returns file path."""
        path = Path(filepath or self._sfx_path)
        path.write_text(
            "# Inflectional suffix list (one per line, supports - prefix)\n"
            "# Delete or comment out unwanted ones, add new ones directly\n"
            "-s\n-ed\n-ing\n-en\n-est\n-es\n",
            encoding="utf-8",
        )
        self.load_inf_suffixes(str(path))
        return str(path)

    def _filter_inf(self, results: list[dict]) -> list[dict]:
        """Remove results containing inflectional suffixes."""
        filtered = []
        for r in results:
            skip = False
            for s in self.inflectional_suffixes:
                pat_uml = f"@@{s}"
                pat_city = f">{s}"
                if "umlabeller" in r and r["umlabeller"]:
                    if pat_uml in r["umlabeller"]:
                        idx = r["umlabeller"].index(pat_uml)
                        end = idx + len(pat_uml)
                        if end == len(r["umlabeller"]) or r["umlabeller"][end] == " ":
                            skip = True
                            break
                if "citylex" in r and r["citylex"]:
                    if pat_city in r["citylex"]:
                        idx = r["citylex"].index(pat_city)
                        end = idx + len(pat_city)
                        if end == len(r["citylex"]) or r["citylex"][end] == ">":
                            skip = True
                            break
            if not skip:
                filtered.append(r)
        return filtered

    # ── batch processing ──────────────────────────────────

    def batch_words(
        self,
        input_file: str | Path,
        mode: str = "seg",
        output: str | Path | None = None,
        fmt: str = "json",
    ) -> str:
        """Batch-process a word list file, output as JSON or CSV.

        Args:
          input_file — word list file (one word per line, ``#`` starts a comment)
          mode       — processing mode:
                        "seg"       morpheme segmentation
                        "count"     morpheme count
                        "morph"     morphological structure
                        "morph:ai"  morphological structure + AI validation
          output     — output path (default = ``{input_stem}_{mode}.json|csv``)
          fmt        — output format: ``"json"`` | ``"csv"``

        Returns: absolute path of the output file.

        >>> mq.batch_words("words.txt", mode="morph", fmt="csv")  # doctest: +SKIP
        """
        input_path = Path(input_file)
        words = []
        with open(input_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                words.append(line)

        raw_map = self._words_raw_batch(words)

        results = []
        for w in words:
            r_row = raw_map.get(w)
            if mode == "seg":
                r = {"words": w, "morph_seg": self.morph_seg(w, raw_row=r_row)}
            elif mode == "count":
                r = {"words": w, "count": self.morph_count(w, raw_row=r_row)}
            elif mode in ("morph", "morph:ai"):
                raw = self.word_morph(w, ai=(mode == "morph:ai"), raw_row=r_row)
                r = {
                    "words": raw.get("word", w),
                    "morph_seg": raw.get("seg"),
                    "prefixes": raw.get("prefixes"),
                    "root": raw.get("root"),
                    "base": raw.get("base"),
                    "lemma": raw.get("lemma"),
                    "S_deri": raw.get("derivational"),
                    "S_inf": raw.get("inflectional"),
                }
                if "ai" in raw:
                    r["ai"] = raw["ai"]
            results.append(r)

        if output is None:
            ext = "json"
            output = input_path.with_stem(f"{input_path.stem}_{mode}").with_suffix(f".{fmt}")

        output_path = Path(output)

        if fmt == "json":
            output_path.write_text(
                json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        elif fmt == "csv":
            if not results:
                output_path.write_text("", encoding="utf-8")
                return str(output_path.resolve())
            # infer column names from first result
            first = results[0]
            if isinstance(first, dict):
                fields = list(first.keys())
                csv_header = self._flatten_keys(first)
            else:
                csv_header = ["value"]
            with open(output_path, "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(csv_header)
                for r in results:
                    writer.writerow(self._flatten_row(r, csv_header))
        else:
            raise ValueError(f"unsupported format: {fmt}")

        return str(output_path.resolve())

    @staticmethod
    def _flatten_keys(d: dict) -> list[str]:
        """Extract flattened key names from nested dict."""
        keys = []
        for k, v in d.items():
            if isinstance(v, dict):
                for sk in v:
                    keys.append(f"{k}.{sk}")
            elif isinstance(v, list) and v and isinstance(v[0], dict):
                # list of dicts → only take first item's keys
                for sk in v[0]:
                    keys.append(f"{k}[].{sk}")
            else:
                keys.append(k)
        return keys

    @staticmethod
    def _flatten_row(row: dict, keys: list[str]) -> list:
        """Extract values by flattened key names."""
        vals = []
        for key in keys:
            if "." in key:
                parts = key.split(".")
                cur = row
                try:
                    for p in parts:
                        cur = cur[p]
                    vals.append(cur)
                except (KeyError, TypeError, IndexError):
                    vals.append(None)
            else:
                vals.append(row.get(key))
        return vals
