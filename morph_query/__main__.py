"""CLI entry point: python -m morph_query <cmd> <arg> ..."""

import json as _json
import sys

from .mq import MQ


def main():
    json_output = "--json" in sys.argv
    exclude_inf = "--exclude-inf" in sys.argv
    limit = None
    for a in list(sys.argv):
        if a.startswith("--limit="):
            limit = int(a.split("=", 1)[1])
            sys.argv.remove(a)
    sys.argv = [a for a in sys.argv if a not in ("--json", "--exclude-inf")]

    mq = MQ()

    if exclude_inf and not mq.inflectional_suffixes:
        print("inf_suffixes.txt not found — needed for --exclude-inf.")
        ans = input("Generate with defaults? [Y/n] ").strip().lower()
        if ans in ("", "y", "yes"):
            p = mq.write_default_inf_file()
            print(f"Created {p} — edit to customize suffixes.")
        else:
            print("Cannot exclude inflectional suffixes without a list. Aborting.")
            sys.exit(1)

    if len(sys.argv) < 3:
        print("Usage: python -m morph_query <cmd> <arg> [source] [seg] [--json] [--exclude-inf] [--limit=N]")
        print()
        print("  Commands:")
        print("    search, prefix, suffix, root, deri_suffix, inf_suffix  — search words")
        print("    count                                                    — count results")
        print("    sample                                                   — random sample")
        print("    morph_seg / word_seg / word                              — morpheme segmentation")
        print("    morph_count / word_count / count <word>                  — morpheme count")
        print("    lemma                                                    — strip inflection")
        print("    word_morph                                               — full morphological structure")
        print()
        print("  source: both (default), umlabeller, citylex")
        print("  seg:    both (default), umlabeller, citylex")
        print("  --json        JSON output")
        print("  --exclude-inf exclude results with inflectional suffixes")
        print("  --limit=N     limit number of results")
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
        case "search" | "prefix" | "suffix" | "root" | "deri_suffix" | "inf_suffix":
            fn = CMD_MAP.get(cmd, cmd)
            results = getattr(mq, fn)(arg, source=source, seg=seg,
                                      exclude_inf=exclude_inf, limit=limit)
        case "count":
            n = mq.word_count(arg, source=source, exclude_inf=exclude_inf)
            print(n)
            sys.exit(0)
        case "sample":
            n = int(arg)
            results = mq.sample(n, source=source, seg=seg, exclude_inf=exclude_inf)

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

    if json_output:
        print(_json.dumps(results, ensure_ascii=False))
    else:
        label = f"source={source}, seg={seg}"
        if exclude_inf:
            label += ", exclude_inf"
        if limit:
            label += f", limit={limit}"
        print(f"Found {len(results)} results ({label}):")
        for r in results[:30]:
            parts = [f"  {r['word']:30s}"]
            if seg in ("umlabeller", "both"):
                parts.append(f"umlabeller={r.get('umlabeller',''):35s}")
            if seg in ("citylex", "both"):
                parts.append(f"citylex={r.get('citylex','')}")
            print("  ".join(parts))
        if len(results) > 30:
            print(f"  ... and {len(results) - 30} more")


if __name__ == "__main__":
    main()
