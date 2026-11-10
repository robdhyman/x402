#!/usr/bin/env python3
"""verify_arrows.py: check swimlane diagram steps against the x402 protocol whitelist.

Usage:
  python3 -I verify_arrows.py DIAGRAMS.json [--whitelist whitelist.json] [--strict]

DIAGRAMS.json: {"<id>": {"lanes": [[key, name, role], ...], "steps": [...]}, ...}
A step is one of:
  {"from": key, "to": key, "label": str, "ret": 0|1, "dashed": 0|1, "e": "E1", "s": "S3"}
  {"self": key, "label": str, ...}            (annotation on a lane: never an arrow)
  {"alt": [{"label": str, "steps": [...]}, ...]} (branches; each inner step is checked)

Rules (from the x402 Protocol Reference Sheet, v2):
  R1  A solid arrow must match a whitelisted protocol message by label pattern.
  R2  A matched arrow must run between the roles the spec gives it, in that direction.
  R3  An arrow that matches nothing must be dashed (identity or mechanism-open step).
  R4  An arrow that touches a lane whose role is not client/server/facilitator must be dashed.
  R5  Facilitator arrows must never touch the client lane (the facilitator talks only to the server).
Exit code 1 if any FAIL. --strict turns WARN into FAIL.
"""
import json, re, sys, argparse

ROLE_ALIASES = {
    "client": ["client", "agent", "agent / buyer", "buyer agent", "coding agent", "travel assistant", "procurement agent", "buying agent"],
    "server": ["server", "resource server", "seller", "data api", "vendor", "airline", "resource"],
    "facilitator": ["facilitator", "verify and settle", "payment facilitator"],
}

HUMAN = ["buyer", "the developer", "the traveller", "developer", "traveller"]

DEFAULT_WHITELIST = [
    # id, label regex (case-insensitive), from-role, to-role, note
    ["M1 request",          r"^(get|post|put) /|\brequest\b|\bhttp\b",                      "client", "server",      "optional if the client already knows the requirements"],
    ["M2 402",              r"\b402\b|payment\s*required",                            "server", "client",      "PAYMENT-REQUIRED header (v2); body (v1)"],
    ["M3 payment payload",  r"payment\s*payload|payment-signature|x-payment\b",       "client", "server",      "PAYMENT-SIGNATURE header (v2); X-PAYMENT (v1)"],
    ["M4 verify",           r"\bverify\b",                                            "server", "facilitator", "POST /verify; optional if verified locally"],
    ["M5 verify response",  r"verif(y|ication)\s*response|verifyresponse|isvalid",    "facilitator", "server", "VerifyResponse"],
    ["M6 settle",           r"\bsettle\b",                                            "server", "facilitator", "POST /settle; or direct chain"],
    ["M7 settle response",  r"settle(ment)?\s*response|settleresponse|payment execution response", "facilitator", "server", "SettlementResponse"],
    ["M8 resource 200",     r"\b200\b|payment-response|x-payment-response|resource\b|ticket\b", "server", "client", "200 + PAYMENT-RESPONSE header (v2)"],
]

def norm_role(role, name=""):
    """Exact alias match on the lane name, then on the role text; then substring. 'principal' is never a protocol party."""
    for r in ((name or "").strip().lower(), (role or "").strip().lower()):
        if not r:
            continue
        if "principal" in r or r in HUMAN or "person" in r:
            return "other"   # Session 0: the Buyer is a person who runs the agent, not the x402 client (Adrian, Oct 27)
        for canon, names in ROLE_ALIASES.items():
            if r == canon or r in names:
                return canon
    for r in ((name or "").strip().lower(), (role or "").strip().lower()):
        for canon, names in ROLE_ALIASES.items():
            for n in names:
                if n in r:
                    return canon
    return "other"

def match(label):
    hits = []
    for mid, pat, f, t, note in WHITELIST:
        if re.search(pat, label, re.I):
            hits.append((mid, f, t))
    return hits

def check_step(st, roles, out):
    if "alt" in st:
        for br in st["alt"]:
            for s in br.get("steps", []):
                check_step(s, roles, out)
        return
    if "self" in st:
        out["annotations"] += 1
        return
    fr, to, label = st["from"], st["to"], st.get("label", "")
    dashed = bool(st.get("dashed")) or bool(st.get("identity"))
    rf, rt = roles.get(fr, "other"), roles.get(to, "other")
    hits = match(label)
    # a combined label like "verify, settle" may hit two messages; all must share the direction
    ok_dir = [h for h in hits if (h[1], h[2]) == (rf, rt)]
    if dashed:
        # a dashed arrow is non-protocol by declaration; only warn if it looks like a real message in the right direction
        if ok_dir:
            out["warn"].append(f"dashed arrow reads as a protocol message ({', '.join(h[0] for h in ok_dir)}); should it be solid? '{label}'")
        if "facilitator" in (rf, rt) and "client" in (rf, rt):
            out["fail"].append(f"R5 facilitator arrow touches the client lane: '{label}' ({fr} -> {to})")
            return
        out["nonprotocol"].append((label, fr, to, "dashed: ok"))
        return
    if hits and ok_dir:
        out["protocol"].append((", ".join(h[0] for h in ok_dir), label))
        return
    if hits and not ok_dir:
        out["fail"].append(f"R2 '{label}' reads as {', '.join(h[0] for h in hits)} but runs {fr}({rf}) -> {to}({rt}); spec says {hits[0][1]} -> {hits[0][2]}")
        return
    # no protocol match
    touches_other = "other" in (rf, rt)
    if "facilitator" in (rf, rt) and "client" in (rf, rt):
        out["fail"].append(f"R5 facilitator arrow touches the client lane: '{label}' ({fr} -> {to})")
        return
    rule = "R4" if touches_other else "R3"
    out["fail"].append(f"{rule} solid arrow is not a protocol message; must be dashed: '{label}' ({fr}({rf}) -> {to}({rt}))")

def run(diagrams, strict):
    total_fail = 0
    for did, d in diagrams.items():
        roles = {l[0]: norm_role(l[2] if len(l) > 2 else "", l[1]) for l in d["lanes"]}
        out = {"protocol": [], "nonprotocol": [], "annotations": 0, "fail": [], "warn": []}
        for st in d["steps"]:
            check_step(st, roles, out)
        if strict:
            out["fail"] += out["warn"]; out["warn"] = []
        print(f"== {did}: lanes {[f'{k}:{v}' for k, v in roles.items()]}")
        print(f"   protocol arrows OK: {len(out['protocol'])}  annotations: {out['annotations']}  non-protocol dashed: {len(out['nonprotocol'])}  WARN: {len(out['warn'])}  FAIL: {len(out['fail'])}")
        for mid, label in out["protocol"]:
            print(f"   ok    {mid:<22} '{label}'")
        for label, fr, to, why in out["nonprotocol"]:
            print(f"   dash  {fr}->{to}: '{label}' ({why})")
        for w in out["warn"]:
            print(f"   WARN  {w}")
        for f in out["fail"]:
            print(f"   FAIL  {f}")
        total_fail += len(out["fail"])
    print(f"TOTAL FAIL {total_fail}")
    return 1 if total_fail else 0

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("diagrams")
    ap.add_argument("--whitelist")
    ap.add_argument("--strict", action="store_true")
    a = ap.parse_args()
    WHITELIST = json.load(open(a.whitelist)) if a.whitelist else DEFAULT_WHITELIST
    sys.exit(run(json.load(open(a.diagrams)), a.strict))
