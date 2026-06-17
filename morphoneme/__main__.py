"""CLI entry point: python -m morphoneme <cmd> <arg> ..."""

import json as _json
import sys

from .mq import MQ


def main():
    json_output = "--json" in sys.argv
    exclude_inf = "--exclude-inf" in sys.argv
    exact = "--exact" in sys.argv
    limit = None
    exclude_str = None
    fq = None
    for a in list(sys.argv):
        if a.startswith("--limit="):
            limit = int(a.split("=", 1)[1])
            sys.argv.remove(a)
        elif a.startswith("--exclude="):
            exclude_str = a.split("=", 1)[1]
            sys.argv.remove(a)
        elif a.startswith("--fq="):
            fq_raw = a.split("=", 1)[1].lower()
            fq_list = [f.strip() for f in fq_raw.split(",") if f.strip()]
            valid_levels = {"high", "medium", "low", "rare", "zero"}
            if not fq_list or any(f not in valid_levels for f in fq_list):
                print("Error: --fq must contain comma-separated values from 'high', 'medium', 'low', 'rare', 'zero'")
                sys.exit(1)
            fq = ",".join(fq_list)
            sys.argv.remove(a)
    sys.argv = [a for a in sys.argv if a not in ("--json", "--exclude-inf", "--exact")]

    mq = MQ()

    if exclude_inf and not mq.inflectional_suffixes:
        print("inf_suffixes.txt not found - needed for --exclude-inf.")
        ans = input("Generate with defaults? [Y/n] ").strip().lower()
        if ans in ("", "y", "yes"):
            p = mq.write_default_inf_file()
            print(f"Created {p} - edit to customize suffixes.")
        else:
            print("Cannot exclude inflectional suffixes without a list. Aborting.")
            sys.exit(1)

    if len(sys.argv) < 3:
        print("Usage: python -m morphoneme <cmd> <arg> [source] [seg] [--json] [--exclude-inf] [--exclude=STR] [--exact] [--limit=N] [--fq=VAL]")
        print()
        print("  Commands:")
        print("    search, prefix, suffix, root, deri_suffix, inf_suffix - search words")
        print("    count                                                    - count results")
        print("    sample                                                   - random sample")
        print("    morph_seg / word_seg / word                              - morpheme segmentation")
        print("    morph_count / word_count / count <word>                  - morpheme count")
        print("    lemma                                                    - strip inflection")
        print("    word_morph                                               - full morphological structure")
        print()
        print("  source: both (default), umlabeller, citylex")
        print("  seg:    both (default), umlabeller, citylex")
        print("  --json        JSON output")
        print("  --exclude-inf exclude results with inflectional suffixes")
        print("  --exclude=STR exclude results containing STR (case-insensitive)")
        print("  --exact       exact morpheme match instead of substring (for search cmd)")
        print("  --limit=N     limit number of results")
        print("  --fq=VAL      frequency filter: comma-separated from 'high' (>=5.0), 'medium' (>=1.0), 'low' (>=0.1), 'rare' (>0.0), 'zero' (==0.0/NULL)")
        sys.exit(1)

    cmd, arg = sys.argv[1], sys.argv[2]
    source = sys.argv[3] if len(sys.argv) > 3 else "both"
    seg = sys.argv[4] if len(sys.argv) > 4 else "both"

    # legacy → new method name map
    CMD_MAP = {
        "prefix": "words_with_prefix",
        "suffix": "words_with_suffix",
        "root": "words_with_root",
        "deri_suffix": "words_with_deri",
        "inf_suffix": "words_with_inf",
    }

    match cmd:
        # ── search / count ──
        case "search":
            results = mq.search(arg, source=source, seg=seg,
                                exclude_inf=exclude_inf, limit=limit, exact=exact, fq=fq)
        case "prefix" | "suffix" | "root" | "deri_suffix" | "inf_suffix":
            fn = CMD_MAP.get(cmd, cmd)
            results = getattr(mq, fn)(arg, source=source, seg=seg,
                                      exclude_inf=exclude_inf, limit=limit, fq=fq)
        case "count":
            n = mq.word_count(arg, source=source, exclude_inf=exclude_inf, fq=fq)
            print(n)
            sys.exit(0)
        case "sample":
            n = int(arg)
            results = mq.sample(n, source=source, seg=seg, exclude_inf=exclude_inf, fq=fq)

        # ── morphological analysis ──
        case "word_morph":
            r = mq.word_morph(arg)
            print(_json.dumps(r, ensure_ascii=False) if r else "Not found")
            sys.exit(0)
        case "word" | "word_seg" | "morph_seg":
            r = mq.morph_seg(arg)
            print(_json.dumps(r, ensure_ascii=False) if r else "Not found")
            sys.exit(0)
        case "morph_count":
            n = mq.morph_count(arg)
            print(n)
            sys.exit(0)
        case "lemma":
            r = mq.lemma(arg)
            print(_json.dumps(r, ensure_ascii=False) if r else "Not found")
            sys.exit(0)
        case _:
            print(f"Unknown: {cmd}")
            sys.exit(1)

    if exclude_str:
        excludes = [e.strip().lower() for e in exclude_str.split(",") if e.strip()]
        if excludes:
            results = [
                r for r in results
                if not any(
                    ex in r["word"].lower()
                    or ex in r.get("umlabeller", "").lower()
                    or ex in r.get("citylex", "").lower()
                    for ex in excludes
                )
            ]

    if json_output:
        print(_json.dumps(results, ensure_ascii=False))
    else:
        label = f"source={source}, seg={seg}"
        if exact:
            label += ", exact"
        if exclude_inf:
            label += ", exclude_inf"
        if exclude_str:
            label += f", exclude={exclude_str}"
        if fq:
            label += f", fq={fq}"
        if limit:
            label += f", limit={limit}"
        print(f"Found {len(results)} results ({label}):")
        display_limit = limit if limit is not None else len(results)
        for r in results[:display_limit]:
            parts = [f"  {r['word']:30s}"]
            if seg in ("umlabeller", "both"):
                parts.append(f"umlabeller={r.get('umlabeller',''):35s}")
            if seg in ("citylex", "both"):
                parts.append(f"citylex={r.get('citylex',''):40s}")
            freq_val = r.get('frequency')
            if freq_val is not None:
                parts.append(f"fq={freq_val:.2f}")
            else:
                parts.append("fq=N/A")
            print("  ".join(parts))
        if len(results) > display_limit:
            print(f"  ... and {len(results) - display_limit} more")


if __name__ == "__main__":
    main()
