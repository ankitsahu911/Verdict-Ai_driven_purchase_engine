"""
Milestone 45 Rehearsal Stopwatch & Diagnostic Script.
Simulates the exact end-to-end live demo flow for Verdict:
1. Wardrobe View (M39 seeded items)
2. Pick Candidate Item & Try-On Render + Fit Signal
3. Buy Score Verdict (6-axis radar, headline, confidence)
4. What-If Lab on Curated Cart (16 subsets, ranked strategies)
5. Opportunity Cost Comparison (Candidate vs Alternative)
6. Purchase Dashboard Panel (5-metric decision summary)

Measures exact stopwatch latency (ms) for every step and captures diagnostic logs.
"""

import os
import sys
import time
from pathlib import Path

# Ensure backend root is in sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv
load_dotenv(dotenv_path=backend_dir.parent / ".env")

from fastapi.testclient import TestClient
from verdict_backend.main import app
from app.db import SessionLocal
from app.models import User, WardrobeItem, GarmentAttributes

def run_rehearsal():
    client = TestClient(app)
    headers = {
        "X-Verdict-User": "demo",
        "Authorization": "Bearer demo-token",
    }

    print("=" * 80)
    print("        MILESTONE 45: FULL DEMO REHEARSAL & STOPWATCH BENCHMARK")
    print("=" * 80)

    db = SessionLocal()
    demo_user = db.query(User).filter(User.firebase_uid == "demo_user_wardrobe").first()
    if not demo_user:
        print("[FATAL] Demo user 'demo_user_wardrobe' not found in database!")
        db.close()
        return

    demo_user_id = demo_user.id
    db.close()

    timings = {}
    observations = []

    # -------------------------------------------------------------
    # STEP 1: Wardrobe View (M9 / M39)
    # -------------------------------------------------------------
    print("\n--- [STEP 1/6] WARDROBE VIEW ---")
    t0 = time.perf_counter()
    resp_w = client.get("/api/wardrobe/items", headers=headers)
    t_wardrobe = (time.perf_counter() - t0) * 1000
    timings["Step 1: Wardrobe View"] = t_wardrobe

    if resp_w.status_code == 200:
        items = resp_w.json()
        item_count = len(items) if isinstance(items, list) else len(items.get("items", []))
        print(f"  [OK] Status 200 ({t_wardrobe:.1f} ms) — Retrieved {item_count} items")
        if item_count != 24:
            observations.append({
                "step": "Step 1: Wardrobe Grid",
                "timing": f"{t_wardrobe:.1f} ms",
                "issue": f"Expected exactly 24 curated demo items, but received {item_count} items.",
                "severity": "awkward but survivable",
            })
    else:
        print(f"  [FAIL] Status {resp_w.status_code}: {resp_w.text}")
        observations.append({
            "step": "Step 1: Wardrobe Grid",
            "timing": f"{t_wardrobe:.1f} ms",
            "issue": f"Wardrobe endpoint failed with HTTP {resp_w.status_code}",
            "severity": "blocks the demo",
        })

    # -------------------------------------------------------------
    # STEP 2: Candidate Intake & Virtual Try-On (M14 / M33 / M42)
    # -------------------------------------------------------------
    print("\n--- [STEP 2/6] CANDIDATE ITEM INTAKE & TRY-ON ---")
    # Fetch candidate items
    t0 = time.perf_counter()
    resp_c = client.get("/api/candidates", headers=headers)
    t_cands = (time.perf_counter() - t0) * 1000
    timings["Step 2A: Fetch Candidates"] = t_cands

    candidates = resp_c.json() if resp_c.status_code == 200 else []
    cand_items = candidates if isinstance(candidates, list) else candidates.get("candidates", [])
    print(f"  [OK] Candidate Fetch ({t_cands:.1f} ms) — {len(cand_items)} candidate items in cart")

    if not cand_items:
        observations.append({
            "step": "Step 2: Candidate Intake",
            "timing": f"{t_cands:.1f} ms",
            "issue": "No candidate items found in cart. Seed script needed.",
            "severity": "blocks the demo",
        })
        selected_cand_id = None
    else:
        selected_cand = cand_items[0]
        selected_cand_id = selected_cand.get("id") or selected_cand.get("item_id")
        print(f"  Selected Demo Candidate: ID #{selected_cand_id}")

        # Check Virtual Try-On Render endpoint
        t0 = time.perf_counter()
        resp_tryon = client.get(f"/api/tryon/render/{selected_cand_id}", headers=headers)
        t_tryon = (time.perf_counter() - t0) * 1000
        timings["Step 2B: Try-On Render"] = t_tryon
        print(f"  Try-On Response ({t_tryon:.1f} ms) — Status: {resp_tryon.status_code}")
        if resp_tryon.status_code != 200:
            observations.append({
                "step": "Step 2: Try-On Render",
                "timing": f"{t_tryon:.1f} ms",
                "issue": f"Try-on render returned HTTP {resp_tryon.status_code}: {resp_tryon.text[:100]}",
                "severity": "awkward but survivable",
            })

    # -------------------------------------------------------------
    # STEP 3: Buy Score Verdict (M23 / M24 / M44)
    # -------------------------------------------------------------
    print("\n--- [STEP 3/6] BUY SCORE VERDICT ---")
    if selected_cand_id:
        t0 = time.perf_counter()
        resp_bs = client.get(f"/api/candidates/{selected_cand_id}/buy-score", headers=headers)
        t_bs = (time.perf_counter() - t0) * 1000
        timings["Step 3: Buy Score Synthesis"] = t_bs

        if resp_bs.status_code == 200:
            bs_data = resp_bs.json()
            verdict = bs_data.get("verdict", "").upper()
            score = bs_data.get("overall_score")
            headline = bs_data.get("headline_reason", "")
            confidence = bs_data.get("confidence", {})
            conf_level = confidence.get("level", "")
            axes = bs_data.get("axes", [])

            print(f"  [OK] Status 200 ({t_bs:.1f} ms)")
            print(f"  Verdict:    {verdict} (Score: {score}/100 | Confidence: {conf_level.upper()})")
            print(f"  Headline:   \"{headline}\"")
            print(f"  Axes Count: {len(axes)}")

            # Check if headline contains awkward phrases
            if "None" in headline or "null" in headline:
                observations.append({
                    "step": "Step 3: Buy Score Screen",
                    "timing": f"{t_bs:.1f} ms",
                    "issue": f"Headline reason contains literal null or None: '{headline}'",
                    "severity": "awkward but survivable",
                })
        else:
            print(f"  [FAIL] Status {resp_bs.status_code}: {resp_bs.text}")
            observations.append({
                "step": "Step 3: Buy Score Screen",
                "timing": f"{t_bs:.1f} ms",
                "issue": f"Buy Score endpoint failed with HTTP {resp_bs.status_code}",
                "severity": "blocks the demo",
            })

    # -------------------------------------------------------------
    # STEP 4: What-If Lab on Curated Cart (M26 / M27 / M40)
    # -------------------------------------------------------------
    print("\n--- [STEP 4/6] WHAT-IF LAB OPTIMIZATION ---")
    cart_ids = [c.get("id") or c.get("item_id") for c in cand_items[:4]]
    t0 = time.perf_counter()
    resp_wi = client.post("/api/what-if/score", json={"item_ids": cart_ids}, headers=headers)
    t_wi = (time.perf_counter() - t0) * 1000
    timings["Step 4: What-If Combinations"] = t_wi

    if resp_wi.status_code == 200:
        wi_data = resp_wi.json()
        subsets = wi_data.get("ranked_subsets", [])
        top_rec = wi_data.get("top_recommendation", {})
        print(f"  [OK] Status 200 ({t_wi:.1f} ms) — Evaluated {len(subsets)} subsets")
        print(f"  Top Strategy: Score {top_rec.get('score')} | Verdict: {top_rec.get('verdict')} | Items: {top_rec.get('item_ids')}")

        if len(subsets) != 16:
            observations.append({
                "step": "Step 4: What-If Lab",
                "timing": f"{t_wi:.1f} ms",
                "issue": f"Expected 16 subset combinations for 4-item cart, but got {len(subsets)}",
                "severity": "cosmetic only",
            })
    else:
        print(f"  [FAIL] Status {resp_wi.status_code}: {resp_wi.text}")
        observations.append({
            "step": "Step 4: What-If Lab",
            "timing": f"{t_wi:.1f} ms",
            "issue": f"What-If endpoint failed with HTTP {resp_wi.status_code}",
            "severity": "blocks the demo",
        })

    # -------------------------------------------------------------
    # STEP 5: Opportunity Cost Comparison (M28 / M30)
    # -------------------------------------------------------------
    print("\n--- [STEP 5/6] OPPORTUNITY COST COMPARISON ---")
    if len(cart_ids) >= 2:
        cand_id = cart_ids[0]
        alt_ids = cart_ids[1:]
        t0 = time.perf_counter()
        resp_oc = client.post(
            "/api/opportunity-cost/evaluate",
            json={"candidate_id": cand_id, "alternative_ids": alt_ids},
            headers=headers,
        )
        t_oc = (time.perf_counter() - t0) * 1000
        timings["Step 5: Opportunity Cost"] = t_oc

        if resp_oc.status_code == 200:
            oc_data = resp_oc.json()
            tradeoff = oc_data.get("comparison_summary", {}).get("tradeoff_headline", "")
            winner = oc_data.get("comparison_summary", {}).get("recommended_path", "")
            print(f"  [OK] Status 200 ({t_oc:.1f} ms)")
            print(f"  Recommendation:  {winner.upper()}")
            print(f"  Tradeoff:        \"{tradeoff}\"")
        else:
            print(f"  [FAIL] Status {resp_oc.status_code}: {resp_oc.text}")
            observations.append({
                "step": "Step 5: Opportunity Cost",
                "timing": f"{t_oc:.1f} ms",
                "issue": f"Opportunity Cost failed with HTTP {resp_oc.status_code}",
                "severity": "blocks the demo",
            })
    else:
        observations.append({
            "step": "Step 5: Opportunity Cost",
            "timing": "N/A",
            "issue": "Not enough candidate items in cart to perform side-by-side comparison.",
            "severity": "blocks the demo",
        })

    # -------------------------------------------------------------
    # STEP 6: Purchase Dashboard Panel (M31 / M43)
    # -------------------------------------------------------------
    print("\n--- [STEP 6/6] PURCHASE DASHBOARD SUMMARY ---")
    if selected_cand_id:
        t0 = time.perf_counter()
        resp_db = client.get(f"/api/candidates/{selected_cand_id}/summary-panel", headers=headers)
        t_db = (time.perf_counter() - t0) * 1000
        timings["Step 6: Dashboard Panel"] = t_db

        if resp_db.status_code == 200:
            db_data = resp_db.json()
            dup_risk = db_data.get("duplicate_risk")
            dup_label = db_data.get("duplicate_risk_label")
            sust_tier = db_data.get("sustainability_tier")
            print(f"  [OK] Status 200 ({t_db:.1f} ms)")
            print(f"  Duplicate Risk:     {dup_risk}% ({dup_label})")
            print(f"  Sustainability:     {sust_tier}")
        else:
            print(f"  [FAIL] Status {resp_db.status_code}: {resp_db.text}")
            observations.append({
                "step": "Step 6: Purchase Dashboard",
                "timing": f"{t_db:.1f} ms",
                "issue": f"Summary panel failed with HTTP {resp_db.status_code}",
                "severity": "blocks the demo",
            })

    # -------------------------------------------------------------
    # TOTAL WALL TIME & SUMMARY TABLE
    # -------------------------------------------------------------
    total_latency_ms = sum(timings.values())
    print("\n" + "=" * 80)
    print("                    STOPWATCH TIMINGS SUMMARY")
    print("=" * 80)
    for step_name, ms in timings.items():
        print(f"  {step_name:<32}: {ms:7.1f} ms ({ms/1000:5.2f} s)")
    print("-" * 80)
    print(f"  {'TOTAL DEMO API LATENCY':<32}: {total_latency_ms:7.1f} ms ({total_latency_ms/1000:5.2f} s)")
    print("=" * 80)

    print("\n" + "=" * 80)
    print("                    DIAGNOSTIC ISSUES LOGGED")
    print("=" * 80)
    if not observations:
        print("  [CLEAN] Zero blocking errors or critical failures detected in automated walk.")
    else:
        for obs in observations:
            print(f"  [{obs['severity'].upper()}] {obs['step']} ({obs['timing']}): {obs['issue']}")
    print("=" * 80 + "\n")

if __name__ == "__main__":
    run_rehearsal()
