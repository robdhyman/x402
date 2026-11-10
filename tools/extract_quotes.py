#!/usr/bin/env python3
"""Extract every meeting quote from the local evidence ledger into evidence/quotes.json.

Run locally. The ledger, its commentary and the raw transcripts stay off GitHub; only the
quote, its speaker label, its time and the heading it was filed under are published.

  python3 tools/extract_quotes.py --cowork "/path/to/Cowork/x402"

Sources read:
  analysis/02-evidence-ledger-v2.md   meetings 1-5 (every quote passed verify_quotes.py when the ledger was built)
  analysis/11-cheatsheet-quotes.md    extra quotes per meeting, same convention
  analysis/16-oct27-ledger.md         meeting 7, built by time range from the transcript and verified the same way
  use-cases/*.json (this repo)        quotes cited on the boards, re-checked here against the transcript
"""
import argparse, glob, json, os, re, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEETINGS = {1: "2026-08-03", 2: "2026-08-18", 3: "2026-09-01", 4: "2026-09-15", 5: "2026-09-29", 6: "2026-10-13", 7: "2026-10-27"}
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
BULLET = re.compile(r'^\s*- \*\*([^*]+)\*\* \[(chat )?(\d\d:\d\d:\d\d)\] "(.+)"\s*$')
INLINE = re.compile(r'\*\*([^*]+)\*\* \[(chat )?(\d\d:\d\d:\d\d)\] "(.+?)"(?=[\s.,;:)]|$)')
CITE = re.compile(r"([A-Z][a-z]+) \[(\d\d:\d\d:\d\d)\] “([^”]+)”")
# A board may cite a stretch of the Oct 27 call without quoting it: "(Nicole, Oct 27 00:37–00:42)" or "(Oct 27 00:32–00:36)".
RANGE = re.compile(r"(?:([A-Z][a-z]+), )?Oct 27 (\d\d:\d\d)(?:[–-](\d\d:\d\d))?")


def clean(s):
    return EMAIL.sub("[email removed]", s).strip()


def secs(t):
    h, m, s = t.split(":")
    return int(h) * 3600 + int(m) * 60 + int(float(s))


def norm(s):
    return re.sub(r"[^a-z0-9]", "", re.sub(r"\[[^\]]*\]", "", s.lower()))


def parse_markdown(path, quotes, meeting_from_heading):
    meeting = section = topic = None
    for line in open(path, encoding="utf-8"):
        line = line.rstrip("\n")
        if line.startswith("# ") or (line.startswith("## ") and meeting_from_heading == "h2"):
            m = re.match(r"#+ (?:Meeting |M)(\d)\b", line)
            meeting = int(m.group(1)) if m else None
            section, topic = ("Reference sheet" if meeting_from_heading == "h2" else None), None
            continue
        if line.startswith("## "):
            section, topic = re.sub(r"^\d+\.\s*", "", line[3:].strip()), None
            continue
        if meeting not in MEETINGS:
            continue
        t = re.match(r"^\*\*(\d+\.\d+ [^*]+?)\.?\*\*", line)
        if t:
            topic = t.group(1)
        found = [BULLET.match(line)] if BULLET.match(line) else list(INLINE.finditer(line))
        for m in found:
            add(quotes, meeting, m.group(3), bool(m.group(2)), m.group(1), m.group(4), section, topic)


def add(quotes, meeting, time, chat, speaker, text, section, topic, board=None, verified=True):
    key = (meeting, time, chat, speaker.split(" (")[0])
    q = quotes.get(key)
    if q is None:
        q = quotes[key] = {"meeting": meeting, "date": MEETINGS[meeting], "time": time, "chat": chat,
                           "speaker": clean(speaker), "text": clean(text), "section": section, "topic": topic,
                           "boards": [], "verified": verified}
    elif len(text) > len(q["text"]) and not board:
        q["text"] = clean(text)
    if board and board not in q["boards"]:
        q["boards"].append(board)
    return q


def load_vtt(cowork, date):
    hits = glob.glob(os.path.join(cowork, "transcripts", f"GMT{date.replace('-', '')}-*_Recording.transcript.vtt"))
    cues = []
    if not hits:
        return cues
    for block in open(hits[0], encoding="utf-8").read().split("\n\n"):
        lines = [l for l in block.strip().split("\n") if l]
        ti = next((i for i, l in enumerate(lines) if "-->" in l), None)
        if ti is None or ti + 1 >= len(lines):
            continue
        body = " ".join(lines[ti + 1:])
        if ": " not in body:
            continue
        who, said = body.split(": ", 1)
        cues.append((secs(lines[ti].split(" --> ")[0]), who.strip(), said))
    return cues


def find_cite(vtts, name, time, text):
    """Return (meeting, full speaker label) when the cited words are in a transcript at that time by that first name."""
    want = [norm(p) for p in re.split(r"\.\.\.", text) if norm(p)]
    for meeting in (6, 7, 5, 4, 3, 2, 1):
        cues = vtts[meeting]
        for i, (start, who, _) in enumerate(cues):
            if abs(start - secs(time)) > 3 or who.split(" ")[0] != name:
                continue
            said = norm(" ".join(c[2] for c in cues[i:i + 14] if c[1] == who))
            pos = 0
            for part in want:
                pos = said.find(part, pos)
                if pos < 0:
                    break
                pos += len(part)
            else:
                return meeting, who
    return None, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cowork", required=True)
    a = ap.parse_args()
    quotes = {}
    parse_markdown(os.path.join(a.cowork, "analysis", "02-evidence-ledger-v2.md"), quotes, "h1")
    ledger_n = len(quotes)
    parse_markdown(os.path.join(a.cowork, "analysis", "11-cheatsheet-quotes.md"), quotes, "h2")
    sheet_n = len(quotes) - ledger_n
    parse_markdown(os.path.join(a.cowork, "analysis", "16-oct27-ledger.md"), quotes, "h1")
    oct27_n = len(quotes) - ledger_n - sheet_n

    vtts = {n: load_vtt(a.cowork, d) for n, d in MEETINGS.items()}
    unverified = []
    for path in sorted(glob.glob(os.path.join(REPO, "use-cases", "uc*.json")) + [os.path.join(REPO, "use-cases", "k0.json")]):
        board = os.path.basename(path)[:-5]
        for name, time, text in CITE.findall(open(path, encoding="utf-8").read()):
            meeting, who = find_cite(vtts, name, time, text)
            if meeting is None:
                unverified.append((board, name, time, text[:60]))
                continue
            add(quotes, meeting, time, False, who, text, "Cited on the boards", None, board=board)
        for name, start, end in RANGE.findall(open(path, encoding="utf-8").read()):
            lo, hi = secs(start + ":00"), secs((end or start) + ":00") + 59
            for q in quotes.values():
                if q["meeting"] == 7 and lo <= secs(q["time"]) <= hi and (not name or q["speaker"].split(" ")[0] == name) and board not in q["boards"]:
                    q["boards"].append(board)

    out = sorted(quotes.values(), key=lambda q: (q["meeting"], q["time"], q["speaker"]))
    seen = {}
    for q in out:
        base = f"m{q['meeting']}-{q['time'].replace(':', '')}"
        seen[base] = seen.get(base, 0) + 1
        q["id"] = base if seen[base] == 1 else f"{base}-{seen[base]}"
    counts = {n: sum(1 for q in out if q["meeting"] == n) for n in MEETINGS}
    json.dump({"meetings": [{"n": n, "date": d, "quotes": counts[n]} for n, d in MEETINGS.items()], "quotes": out},
              open(os.path.join(REPO, "evidence", "quotes.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    rows = []
    for line in open(os.path.join(a.cowork, "analysis", "14-uc1-change-log.md"), encoding="utf-8"):
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if line.startswith("|") and len(cells) == 6 and cells[0].isdigit():
            rows.append(dict(zip(("n", "who", "when", "said", "change", "status"), map(clean, cells))))
    json.dump({"session": "Session 0", "date": "2026-11-09", "feedback_from": "2026-10-27", "rows": rows},
              open(os.path.join(REPO, "evidence", "changes.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(f"change log rows {len(rows)}")
    print(f"ledger {ledger_n} · cheat sheet +{sheet_n} · Oct 27 +{oct27_n} · board cites +{len(out) - ledger_n - sheet_n - oct27_n} new · total {len(out)}")
    print("per meeting", counts)
    for u in unverified:
        print("NOT FOUND IN TRANSCRIPT", *u)
    return 1 if unverified else 0


if __name__ == "__main__":
    sys.exit(main())
