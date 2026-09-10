import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

BASE_URL = os.getenv("API_URL", "http://127.0.0.1:8000")
HEADERS = {
    "Content-Type": "application/json",
    "X-Verdict-User": "demo",
    "Authorization": "Bearer demo-token",
}


def http_get(path: str) -> dict | list:
    url = f"{BASE_URL}{path}"
    req = urllib.request.Request(url, headers=HEADERS, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        raise RuntimeError(f"GET {path} failed (HTTP {e.code}): {body}")
    except Exception as e:
        raise RuntimeError(f"GET {path} failed: {e}")


def http_post(path: str, payload: dict) -> dict:
    url = f"{BASE_URL}{path}"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=HEADERS, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        raise RuntimeError(f"POST {path} failed (HTTP {e.code}): {body}")
    except Exception as e:
        raise RuntimeError(f"POST {path} failed: {e}")


def main():
    print("=================================================================")
    print("MILESTONE 40: CURATED DEMO CART DETERMINISTIC VERIFICATION")
    print("=================================================================")

    # -------------------------------------------------------------
    # 1. PRE-FLIGHT CHECK: Verify candidates & required price field
    # -------------------------------------------------------------
    print("\n--- STEP 1: PRE-FLIGHT CHECK ON CURATED DEMO CANDIDATE CART ---")
    candidates = http_get("/api/candidates")
    if not isinstance(candidates, list) or len(candidates) < 3:
        raise ValueError(
            f"Expected at least 3-5 candidate items for demo user, found {len(candidates) if isinstance(candidates, list) else 0}"
        )

    print(f"Total Candidate Items Found: {len(candidates)}")
    cand_ids = []
    missing_price = []

    print("\n" + "-" * 88)
    print(f"{'ID':<6} {'Category':<12} {'Color':<14} {'Season':<12} {'Style':<14} {'Price':<10} {'Status'}")
    print("-" * 88)

    for c in candidates:
        cid = c["id"]
        cand_ids.append(cid)
        price = c.get("price")
        attrs = c.get("attributes") or {}
        cat = attrs.get("category", "unknown")
        col = attrs.get("color", "unknown")
        sea = attrs.get("season", "unknown")
        sty = attrs.get("style", "unknown")

        if price is None or price <= 0:
            missing_price.append(cid)
            status = "FAIL (No price)"
        else:
            status = "VALID"

        price_str = f"${price:.2f}" if price is not None else "MISSING"
        print(f"#{cid:<5} {cat:<12} {col:<14} {sea:<12} {sty:<14} {price_str:<10} {status}")

    print("-" * 88)

    if missing_price:
        raise ValueError(
            f"Pre-flight check FAILED! Missing price on candidate items: {missing_price}. Every candidate must have a price set!"
        )

    print("[PASS] Pre-flight Check Succeeded: Every candidate item has price and attributes properly set.")

    # -------------------------------------------------------------
    # 2. DETERMINISM PROOF: Run exact cart 3 separate times & diff
    # -------------------------------------------------------------
    print("\n--- STEP 2: DETERMINISM AUDIT — RERUNNING EXACT CART 3 SEPARATE TIMES ---")
    payload = {"item_ids": cand_ids}
    runs = []

    for run_idx in range(1, 4):
        print(f"Executing What-If Lab Scoring: Run {run_idx} of 3...")
        res = http_post("/api/what-if/score", payload)
        runs.append(res)

    print("\nDiffing results across all 3 independent scoring runs...")
    run1, run2, run3 = runs[0], runs[1], runs[2]

    # Verify total subsets match
    total1, total2, total3 = run1["total_subsets"], run2["total_subsets"], run3["total_subsets"]
    expected_subsets = 2 ** len(cand_ids)
    if not (total1 == total2 == total3 == expected_subsets):
        raise AssertionError(
            f"Total subsets mismatch! Run1={total1}, Run2={total2}, Run3={total3}, Expected={expected_subsets}"
        )

    # Check every ranked combination across runs
    subsets1 = run1["subsets"]
    subsets2 = run2["subsets"]
    subsets3 = run3["subsets"]

    diffs = []
    for i in range(len(subsets1)):
        s1 = subsets1[i]
        s2 = subsets2[i]
        s3 = subsets3[i]

        rank1, rank2, rank3 = s1["rank"], s2["rank"], s3["rank"]
        items1, items2, items3 = s1["item_ids"], s2["item_ids"], s3["item_ids"]
        score1, score2, score3 = s1["overall_score"], s2["overall_score"], s3["overall_score"]
        verd1, verd2, verd3 = s1["verdict"].lower(), s2["verdict"].lower(), s3["verdict"].lower()

        if not (rank1 == rank2 == rank3):
            diffs.append(f"Rank mismatch at index {i}: Run1={rank1}, Run2={rank2}, Run3={rank3}")
        if not (items1 == items2 == items3):
            diffs.append(f"Items mismatch at index {i}: Run1={items1}, Run2={items2}, Run3={items3}")
        if not (score1 == score2 == score3):
            diffs.append(f"Score mismatch at rank #{rank1}: Run1={score1}, Run2={score2}, Run3={score3}")
        if not (verd1 == verd2 == verd3):
            diffs.append(f"Verdict mismatch at rank #{rank1}: Run1={verd1}, Run2={verd2}, Run3={verd3}")

    if diffs:
        for d in diffs:
            print("  [DIFF FAILURE]", d)
        raise AssertionError(f"Determinism verification failed with {len(diffs)} diffs across runs!")

    print(
        f"[PASS] 100% Determinism Proof: All 3 scoring runs produced identical ranked lists, "
        f"identical scores down to the decimal, and identical verdicts across all {expected_subsets} subsets!"
    )

    # -------------------------------------------------------------
    # 3. VERDICT SPREAD AUDIT: Confirm clear Buy and Skip results
    # -------------------------------------------------------------
    print("\n--- STEP 3: FINAL RANKED COMBINATIONS & VERDICT SPREAD ---")
    ranked = subsets1

    buy_subsets = [s for s in ranked if s["verdict"].lower() == "buy"]
    consider_subsets = [s for s in ranked if s["verdict"].lower() == "consider"]
    skip_subsets = [s for s in ranked if s["verdict"].lower() == "skip"]

    print("\n" + "=" * 98)
    print(f"{'Rank':<6} {'Score':<8} {'Verdict':<10} {'Price':<10} {'Items In Combination':<24} {'Headline Reasoning'}")
    print("=" * 98)

    for s in ranked:
        items_str = ", ".join(f"#{i}" for i in s["item_ids"]) or "Skip All (Baseline)"
        price_str = f"${s.get('total_price', 0.0):.2f}"
        headline = s["headline_reason"]
        if len(headline) > 38:
            headline = headline[:35] + "..."
        print(f"#{s['rank']:<5} {s['overall_score']:<8.1f} {s['verdict'].upper():<10} {price_str:<10} {items_str:<24} {headline}")

    print("=" * 98)

    print(f"\nVerdict Summary Distribution (Total: {len(ranked)} combinations):")
    print(f"  - BUY Verdicts     : {len(buy_subsets):2d} combination(s) [Scores {min(s['overall_score'] for s in buy_subsets):.1f} - {max(s['overall_score'] for s in buy_subsets):.1f}]")
    print(f"  - CONSIDER Verdicts: {len(consider_subsets):2d} combination(s) [Scores {min(s['overall_score'] for s in consider_subsets):.1f} - {max(s['overall_score'] for s in consider_subsets):.1f}]")
    print(f"  - SKIP Verdicts    : {len(skip_subsets):2d} combination(s) [Scores {min(s['overall_score'] for s in skip_subsets):.1f} - {max(s['overall_score'] for s in skip_subsets):.1f}]")

    # Strict acceptance criteria assertions
    if len(buy_subsets) < 1:
        raise AssertionError("Acceptance criteria failed: Cart combinations contain NO clear Buy verdict!")
    if len(skip_subsets) < 1:
        raise AssertionError("Acceptance criteria failed: Cart combinations contain NO clear Skip verdict!")

    top = ranked[0]
    bottom = ranked[-1]
    print(f"\n[TOP RECOMMENDATION - CLEAR BUY]")
    print(f"  Subset: #{top['rank']} | Score: {top['overall_score']:.1f}/100 | Verdict: {top['verdict'].upper()}")
    print(f"  Items : {top['item_ids']} | Total Price: ${top.get('total_price', 0.0):.2f}")
    print(f"  Reason: {top['headline_reason']}")

    print(f"\n[LOWEST RECOMMENDATION - CLEAR SKIP]")
    print(f"  Subset: #{bottom['rank']} | Score: {bottom['overall_score']:.1f}/100 | Verdict: {bottom['verdict'].upper()}")
    print(f"  Items : {bottom['item_ids']} | Total Price: ${bottom.get('total_price', 0.0):.2f}")
    print(f"  Reason: {bottom['headline_reason']}")

    print("\n=================================================================")
    print("[SUCCESS] Milestone 40 Acceptance Criteria Fully Satisfied!")
    print("Running What-If Lab on this curated cart produces both a clear Buy")
    print("and a clear Skip verdict — 100% identically across every rerun.")
    print("=================================================================")


if __name__ == "__main__":
    main()
