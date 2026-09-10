"""
End-to-End Single-Item Pipeline Test (Milestone 37).
Takes 5 REAL candidate garment photos and runs each one through the full
pipeline back to back via the actual API endpoints:
  1. Intake Flow: POST /api/candidates (Vision Extraction + Try-On + Duplicate Detection + Embedding)
  2. Outfit Matches: GET /api/candidates/{id}/outfit-matches
  3. Decision Axes: GET /api/candidates/{id}/axes
  4. Final Buy Score: GET /api/candidates/{id}/buy-score

Captures step-by-step success/failure, latency, final verdict, overall score,
and a 1-line summary for each of the 6 decision axes.
"""

import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

# Ensure backend root is on sys.path
BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

from dotenv import load_dotenv
load_dotenv(dotenv_path=BACKEND_ROOT.parent / ".env")

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.auth import get_current_user
from app.db import Base, get_db
from app.models import ExtractionSource, GarmentAttributes, User, WardrobeItem
from app.services.chroma_service import (
    get_wardrobe_collection,
    upsert_wardrobe_embedding,
)
from app.services.embedding_service import generate_embedding
from verdict_backend.main import app

# Terminal styling
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


def format_verdict(verdict: str) -> str:
    v = (verdict or "").upper()
    if v == "BUY":
        return f"{GREEN}{BOLD}BUY{RESET}"
    elif v == "CONSIDER":
        return f"{YELLOW}{BOLD}CONSIDER{RESET}"
    elif v == "SKIP":
        return f"{RED}{BOLD}SKIP{RESET}"
    return v


# 5 REAL Candidate Garment Photos
CANDIDATE_ITEMS = [
    {
        "name": "Candidate 1: Classic White Cotton Tee",
        "file_name": "candidate_1_white_tee.jpg",
        "price": 28.00,
        "description": "Casual wardrobe staple. Testing duplicate/redundancy detection against owned white tee.",
    },
    {
        "name": "Candidate 2: Rust Utility Jacket",
        "file_name": "candidate_2_khaki_jacket.jpg",
        "price": 95.00,
        "description": "Casual outer layer. Testing pairing versatility across existing tops, bottoms, and footwear.",
    },
    {
        "name": "Candidate 3: Classic Blue Denim Jeans",
        "file_name": "candidate_3_blue_jeans.jpg",
        "price": 68.00,
        "description": "Core denim bottom. Testing duplicate similarity to owned jeans and top pairing.",
    },
    {
        "name": "Candidate 4: Camel Wool Overcoat",
        "file_name": "candidate_4_black_dress.jpg",
        "price": 180.00,
        "description": "Smart-casual winter overcoat. Testing seasonal relevance, style alignment, and high CPW.",
    },
    {
        "name": "Candidate 5: White Summer Cotton Dress",
        "file_name": "candidate_5_leather_jacket.jpg",
        "price": 75.00,
        "description": "Casual summer one-piece dress. Testing one-piece outfit pairing and seasonal scoring.",
    },
]


def setup_test_environment():
    """Initializes isolated SQLite test database and seeds realistic owned wardrobe items."""
    db_path = BACKEND_ROOT / "data" / "e2e_test_single_item.db"
    if db_path.exists():
        try:
            db_path.unlink()
        except OSError:
            pass

    test_engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=test_engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    mock_user_dict = {
        "uid": "e2e_pipeline_tester",
        "email": "tester@verdict.engine",
        "name": "E2E Automated Tester",
    }
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: mock_user_dict

    # Seed User & Existing Wardrobe Items
    db = TestingSessionLocal()
    user = User(
        firebase_uid=mock_user_dict["uid"],
        email=mock_user_dict["email"],
        display_name=mock_user_dict["name"],
        created_at=datetime.now(timezone.utc),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    print(f"\n{CYAN}{BOLD}Initializing Seed Wardrobe for User {user.email} (ID: {user.id})...{RESET}")

    try:
        col = get_wardrobe_collection()
        col.delete(where={"user_id": user.id})
    except Exception:
        pass

    seed_items_data = [
        {
            "category": "top",
            "color": "white",
            "pattern": "solid",
            "style": "casual",
            "season": "all-season",
            "material": "cotton",
            "price": 25.0,
            "url": str(BACKEND_ROOT / "data" / "test_candidates" / "candidate_1_white_tee.jpg"),
        },
        {
            "category": "bottom",
            "color": "blue",
            "pattern": "solid",
            "style": "casual",
            "season": "all-season",
            "material": "denim",
            "price": 70.0,
            "url": str(BACKEND_ROOT / "data" / "test_candidates" / "candidate_3_blue_jeans.jpg"),
        },
        {
            "category": "footwear",
            "color": "white",
            "pattern": "solid",
            "style": "casual",
            "season": "all-season",
            "material": "leather",
            "price": 80.0,
            "url": "https://images.unsplash.com/photo-1549298916-b41d501d3772?w=600",
        },
        {
            "category": "footwear",
            "color": "black",
            "pattern": "solid",
            "style": "formal",
            "season": "all-season",
            "material": "leather",
            "price": 120.0,
            "url": "https://images.unsplash.com/photo-1543163521-1bf539c55dd2?w=600",
        },
        {
            "category": "outerwear",
            "color": "navy",
            "pattern": "solid",
            "style": "smart-casual",
            "season": "fall",
            "material": "wool",
            "price": 120.0,
            "url": "https://images.unsplash.com/photo-1591047139829-d91aecb6caea?w=600",
        },
        {
            "category": "top",
            "color": "grey",
            "pattern": "solid",
            "style": "casual",
            "season": "winter",
            "material": "fleece",
            "price": 45.0,
            "url": "https://images.unsplash.com/photo-1556905055-8f358a7a47b2?w=600",
        },
    ]

    for item_spec in seed_items_data:
        wardrobe_item = WardrobeItem(
            user_id=user.id,
            cloudinary_url=item_spec["url"],
            is_candidate=False,
            price=item_spec["price"],
            fit_tightness="regular",
            silhouette="tailored",
            uploaded_at=datetime.now(timezone.utc),
        )
        db.add(wardrobe_item)
        db.commit()
        db.refresh(wardrobe_item)

        attrs = GarmentAttributes(
            wardrobe_item_id=wardrobe_item.id,
            category=item_spec["category"],
            color=item_spec["color"],
            pattern=item_spec["pattern"],
            style=item_spec["style"],
            season=item_spec["season"],
            material=item_spec["material"],
            extraction_source=ExtractionSource.MANUAL_OVERRIDE,
            updated_at=datetime.now(timezone.utc),
        )
        db.add(attrs)
        db.commit()

        # Seed embedding into ChromaDB
        try:
            if Path(item_spec["url"]).exists():
                emb = generate_embedding(item_spec["url"])
                upsert_wardrobe_embedding(
                    item_id=wardrobe_item.id,
                    user_id=user.id,
                    category=attrs.category,
                    embedding=emb,
                )
        except Exception as e:
            print(f"  [Notice] Seed embedding skipped for item #{wardrobe_item.id}: {e}")

    total_owned = db.query(WardrobeItem).filter(WardrobeItem.is_candidate == False).count()
    print(f"  -> Seeded {total_owned} owned wardrobe pieces (tops, bottoms, outerwear).")
    db.close()

    return TestClient(app), TestingSessionLocal


def run_single_candidate(client: TestClient, candidate_spec: dict) -> dict:
    """Runs a single candidate photo through the 4-stage pipeline via HTTP endpoints."""
    file_path = BACKEND_ROOT / "data" / "test_candidates" / candidate_spec["file_name"]
    if not file_path.exists():
        return {
            "name": candidate_spec["name"],
            "error": f"Candidate image not found at {file_path}",
            "stages": {},
        }

    item_name = candidate_spec["name"]
    price = candidate_spec["price"]

    print(f"\n{'='*75}")
    print(f"{BOLD}RUNNING PIPELINE FOR: {item_name}{RESET}")
    print(f"Photo: {file_path.name} | Price: ${price:.2f} | Notes: {candidate_spec['description']}")
    print(f"{'='*75}")

    stage_results = {}
    candidate_id = None
    t_start = time.time()

    # -------------------------------------------------------------
    # STAGE 1: POST /api/candidates (Candidate Intake Flow)
    # -------------------------------------------------------------
    print(f"\n[Stage 1/4] POST /api/candidates (Intake: Vision + Try-On + Duplicates)...")
    s1_t0 = time.time()
    try:
        with open(file_path, "rb") as f:
            files = {"file": (file_path.name, f, "image/jpeg")}
            data = {"price": str(price)}
            resp = client.post("/api/candidates", files=files, data=data)

        s1_dur = time.time() - s1_t0
        if resp.status_code != 201:
            stage_results["intake"] = {
                "success": False,
                "status_code": resp.status_code,
                "error": resp.text,
                "duration": s1_dur,
            }
            print(f"  {RED}FAILED ({resp.status_code}): {resp.text}{RESET}")
            return {"name": item_name, "stages": stage_results, "success": False}

        intake_data = resp.json()
        candidate_id = intake_data.get("candidate_item_id")
        attrs = intake_data.get("attributes") or {}
        tryon = intake_data.get("tryon") or {}
        duplicate = intake_data.get("duplicate") or {}

        stage_results["intake"] = {
            "success": True,
            "status_code": resp.status_code,
            "candidate_id": candidate_id,
            "attributes": attrs,
            "tryon": tryon,
            "duplicate": duplicate,
            "duration": s1_dur,
        }
        print(f"  {GREEN}SUCCESS{RESET} (took {s1_dur:.2f}s) -> Created Candidate ID: {BOLD}#{candidate_id}{RESET}")
        print(f"  - Extracted Attributes: category={attrs.get('category')}, color={attrs.get('color')}, "
              f"style={attrs.get('style')}, season={attrs.get('season')}, material={attrs.get('material')}")
        print(f"  - Vision Provider: {attrs.get('provider_used')}")
        print(f"  - Try-On Status: degraded={tryon.get('tryon_degraded', False)}, tightness={tryon.get('fit_tightness')}, silhouette={tryon.get('silhouette')}")
        if duplicate:
            print(f"  - Duplicate Match: {duplicate.get('similarity_percentage')}% similar to item #{duplicate.get('wardrobe_item_id')}")
        else:
            print(f"  - Duplicate Match: None detected (novel item)")

    except Exception as e:
        s1_dur = time.time() - s1_t0
        stage_results["intake"] = {"success": False, "error": str(e), "duration": s1_dur}
        print(f"  {RED}EXCEPTION: {e}{RESET}")
        return {"name": item_name, "stages": stage_results, "success": False}

    # -------------------------------------------------------------
    # STAGE 2: GET /api/candidates/{id}/outfit-matches (Outfit Compatibility)
    # -------------------------------------------------------------
    print(f"\n[Stage 2/4] GET /api/candidates/{candidate_id}/outfit-matches (Compatibility)...")
    s2_t0 = time.time()
    try:
        resp = client.get(f"/api/candidates/{candidate_id}/outfit-matches")
        s2_dur = time.time() - s2_t0
        if resp.status_code != 200:
            stage_results["outfit_matches"] = {
                "success": False,
                "status_code": resp.status_code,
                "error": resp.text,
                "duration": s2_dur,
            }
            print(f"  {RED}FAILED ({resp.status_code}): {resp.text}{RESET}")
        else:
            matches_data = resp.json()
            total_matches = matches_data.get("total_matches", 0)
            stage_results["outfit_matches"] = {
                "success": True,
                "status_code": resp.status_code,
                "total_matches": total_matches,
                "duration": s2_dur,
            }
            print(f"  {GREEN}SUCCESS{RESET} (took {s2_dur:.2f}s) -> Found {BOLD}{total_matches}{RESET} compatible owned wardrobe pairings.")

    except Exception as e:
        s2_dur = time.time() - s2_t0
        stage_results["outfit_matches"] = {"success": False, "error": str(e), "duration": s2_dur}
        print(f"  {RED}EXCEPTION: {e}{RESET}")

    # -------------------------------------------------------------
    # STAGE 3: GET /api/candidates/{id}/axes (Decision Engine 6 Axes)
    # -------------------------------------------------------------
    print(f"\n[Stage 3/4] GET /api/candidates/{candidate_id}/axes (6-Axis Decision Scores)...")
    s3_t0 = time.time()
    try:
        resp = client.get(f"/api/candidates/{candidate_id}/axes")
        s3_dur = time.time() - s3_t0
        if resp.status_code != 200:
            stage_results["axes"] = {
                "success": False,
                "status_code": resp.status_code,
                "error": resp.text,
                "duration": s3_dur,
            }
            print(f"  {RED}FAILED ({resp.status_code}): {resp.text}{RESET}")
        else:
            axes_data = resp.json()
            axes_list = axes_data.get("axes", [])
            stage_results["axes"] = {
                "success": True,
                "status_code": resp.status_code,
                "axes": axes_list,
                "duration": s3_dur,
            }
            print(f"  {GREEN}SUCCESS{RESET} (took {s3_dur:.2f}s) -> Computed {len(axes_list)} axes:")
            for ax in axes_list:
                print(f"    * {ax['axis']:<20}: {ax['score']:>5.1f}/100 | {ax['reason']}")

    except Exception as e:
        s3_dur = time.time() - s3_t0
        stage_results["axes"] = {"success": False, "error": str(e), "duration": s3_dur}
        print(f"  {RED}EXCEPTION: {e}{RESET}")

    # -------------------------------------------------------------
    # STAGE 4: GET /api/candidates/{id}/buy-score (Final Buy Score Synthesis)
    # -------------------------------------------------------------
    print(f"\n[Stage 4/4] GET /api/candidates/{candidate_id}/buy-score (Final Synthesis)...")
    s4_t0 = time.time()
    try:
        resp = client.get(f"/api/candidates/{candidate_id}/buy-score")
        s4_dur = time.time() - s4_t0
        if resp.status_code != 200:
            stage_results["buy_score"] = {
                "success": False,
                "status_code": resp.status_code,
                "error": resp.text,
                "duration": s4_dur,
            }
            print(f"  {RED}FAILED ({resp.status_code}): {resp.text}{RESET}")
        else:
            buy_score_data = resp.json()
            stage_results["buy_score"] = {
                "success": True,
                "status_code": resp.status_code,
                "data": buy_score_data,
                "duration": s4_dur,
            }
            overall = buy_score_data.get("overall_score", 0.0)
            verdict = buy_score_data.get("verdict", "unknown")
            conf = buy_score_data.get("confidence", {})
            panel = buy_score_data.get("summary_panel", {})

            print(f"  {GREEN}SUCCESS{RESET} (took {s4_dur:.2f}s)")
            print(f"\n  --------------------------------------------------------")
            print(f"  VERDICT:        {format_verdict(verdict)}")
            print(f"  OVERALL SCORE:  {BOLD}{overall:.1f} / 100{RESET}")
            print(f"  CONFIDENCE:     [{conf.get('level', 'N/A').upper()}] {conf.get('reasoning', '')}")
            print(f"  HEADLINE:       {buy_score_data.get('headline_reason', '')}")
            print(f"  SUMMARY PANEL:  CPW: {panel.get('cost_per_wear', 'N/A')} | "
                  f"Sustainability: {panel.get('sustainability', {}).get('tier', 'N/A')} | "
                  f"Versatility: {panel.get('versatility', 'N/A')}")
            print(f"  --------------------------------------------------------")

    except Exception as e:
        s4_dur = time.time() - s4_t0
        stage_results["buy_score"] = {"success": False, "error": str(e), "duration": s4_dur}
        print(f"  {RED}EXCEPTION: {e}{RESET}")

    total_duration = time.time() - t_start
    all_stages_succeeded = all(st.get("success", False) for st in stage_results.values())

    return {
        "candidate_id": candidate_id,
        "name": item_name,
        "price": price,
        "success": all_stages_succeeded,
        "total_duration": total_duration,
        "stages": stage_results,
    }


def print_comparative_summary(results: List[dict]):
    """Prints a clean, human-readable comparison of all 5 tested candidate garments."""
    print(f"\n\n{'='*95}")
    print(f"{BOLD}MILESTONE 37: 5-ITEM PIPELINE END-TO-END VERIFICATION SUMMARY{RESET}")
    print(f"{'='*95}")

    header = f"{'#':<3} {'Candidate Item':<32} {'Price':<8} {'Verdict':<12} {'Score':<8} {'Confidence':<12} {'Pipeline Status':<15}"
    print(header)
    print("-" * 95)

    for i, res in enumerate(results, start=1):
        name = res.get("name", "")
        # Truncate clean label
        clean_name = name.split(":", 1)[-1].strip() if ":" in name else name
        price_str = f"${res.get('price', 0):.2f}"
        
        stages = res.get("stages", {})
        buy_score_stage = stages.get("buy_score", {})
        data = buy_score_stage.get("data", {}) if buy_score_stage.get("success") else {}

        verdict_raw = data.get("verdict", "ERR")
        verdict_str = format_verdict(verdict_raw)
        score_val = data.get("overall_score")
        score_str = f"{score_val:.1f}" if score_val is not None else "N/A"
        conf_level = data.get("confidence", {}).get("level", "N/A").upper()

        status_str = f"{GREEN}All 4 Passed{RESET}" if res.get("success") else f"{RED}Partial Error{RESET}"

        print(f"{i:<3} {clean_name[:32]:<32} {price_str:<8} {verdict_str:<21} {score_str:<8} {conf_level:<12} {status_str}")

    print("-" * 95)
    print("\nDetailed Axis Breakdown by Item:")
    for i, res in enumerate(results, start=1):
        stages = res.get("stages", {})
        axes = stages.get("axes", {}).get("axes", [])
        name = res.get("name", "")
        print(f"\n[{i}] {BOLD}{name}{RESET}")
        if not axes:
            print("  No axis data recorded.")
            continue
        for ax in axes:
            print(f"  * {ax['axis']:<20}: {ax['score']:>5.1f}/100 — {ax['reason']}")

    print(f"\n{'='*95}\n")


def main():
    print(f"{BOLD}========================================================================{RESET}")
    print(f"{BOLD} Verdict Purchase Decision Engine — E2E Single-Item Pipeline Runner    {RESET}")
    print(f"{BOLD} Milestone 37: 5 Real Garment Items Back-to-Back Integration Test       {RESET}")
    print(f"{BOLD}========================================================================{RESET}")

    client, session_factory = setup_test_environment()

    results = []
    for i, item in enumerate(CANDIDATE_ITEMS):
        res = run_single_candidate(client, item)
        results.append(res)
        if i < len(CANDIDATE_ITEMS) - 1:
            time.sleep(2.0)

    print_comparative_summary(results)

    # Exit 0 if all succeeded
    all_ok = all(r.get("success", False) for r in results)
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
