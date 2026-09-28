#!/usr/bin/env python3
import csv
import gzip
import io
import re
import sys
from collections import OrderedDict
from pathlib import Path

LINE_RE = re.compile(r"^(\S+)\s+(\S+)\s+\[([^\]]+)\]\s+/(.*)/$")

def normalized_pinyin(pinyin: str) -> str:
    p = pinyin.lower().replace("u:", "v").replace("ü", "v")
    p = re.sub(r"[1-5]", "", p)
    p = re.sub(r"[\s'’\-·.]+", "", p)
    return p

def clean_definition(d: str) -> str:
    d = d.strip()
    d = re.sub(r"\s+", " ", d)
    return d

def main(source: str, output: str) -> None:
    opener = gzip.open if source.endswith(".gz") else open
    entries = OrderedDict()

    with opener(source, "rt", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line or line.startswith("#"):
                continue
            m = LINE_RE.match(line)
            if not m:
                continue

            trad, _simp, pinyin, defs_raw = m.groups()
            pronunciation = normalized_pinyin(pinyin)
            if not pronunciation:
                continue

            defs = [clean_definition(x) for x in defs_raw.split("/") if clean_definition(x)]
            defs = [x for x in defs if not x.startswith("CL:")]
            if not defs:
                continue

            key = (trad, pronunciation)
            bucket = entries.setdefault(key, [])
            for definition in defs:
                if definition not in bucket:
                    bucket.append(definition)

    out = Path(output)
    out.parent.mkdir(parents=True, exist_ok=True)

    with out.open("w", encoding="utf-8", newline="") as f:
        f.write("""---
name: mandarin_english
version: "2026.09.28"
sort: original
use_preset_vocabulary: false
...

""")
        for (trad, pronunciation), definitions in entries.items():
            # CandidateEntry expects English at raw dictionary column 11.
            english = "; ".join(definitions[:6])
            if len(english) > 320:
                english = english[:317].rstrip() + "..."

            fields = [
                pronunciation, "1", "", "", "", "", "", "", "", "", "", english
            ]
            buf = io.StringIO()
            writer = csv.writer(buf, lineterminator="", quoting=csv.QUOTE_MINIMAL)
            writer.writerow(fields)
            metadata = buf.getvalue()
            f.write(metadata + "\t" + trad + "\n")

    print(f"Wrote {len(entries):,} Traditional Mandarin-English lookup entries to {out}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: build_dictionary.py <cedict.txt[.gz]> <output.dict.yaml>")
    main(sys.argv[1], sys.argv[2])
