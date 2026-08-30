import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_CATEGORY_BASELINES: dict[str, dict[str, Any]] = {
    "top": {"annual_wears": 30, "baseline_return_risk": 20, "typical_cost_per_wear_ceiling": 3.50},
    "bottom": {"annual_wears": 35, "baseline_return_risk": 30, "typical_cost_per_wear_ceiling": 4.00},
    "outerwear": {"annual_wears": 15, "baseline_return_risk": 25, "typical_cost_per_wear_ceiling": 12.00},
    "dress": {"annual_wears": 10, "baseline_return_risk": 40, "typical_cost_per_wear_ceiling": 15.00},
    "footwear": {"annual_wears": 40, "baseline_return_risk": 45, "typical_cost_per_wear_ceiling": 4.50},
    "accessory": {"annual_wears": 20, "baseline_return_risk": 10, "typical_cost_per_wear_ceiling": 3.00},
}

BASELINES_FILE = Path(__file__).resolve().parent.parent / "data" / "wear_baselines.json"


def load_wear_baselines() -> dict[str, dict[str, Any]]:
    if BASELINES_FILE.exists():
        try:
            with open(BASELINES_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                result = {}
                for k, v in data.items():
                    key = k.lower()
                    if isinstance(v, dict):
                        fallback_data = DEFAULT_CATEGORY_BASELINES.get(key, {})
                        result[key] = {
                            "annual_wears": int(v.get("annual_wears", fallback_data.get("annual_wears", 30))),
                            "baseline_return_risk": int(v.get("baseline_return_risk", fallback_data.get("baseline_return_risk", 20))),
                            "typical_cost_per_wear_ceiling": float(v.get("typical_cost_per_wear_ceiling", fallback_data.get("typical_cost_per_wear_ceiling", 3.50))),
                        }
                    else:
                        fallback_data = DEFAULT_CATEGORY_BASELINES.get(key, {})
                        result[key] = {
                            "annual_wears": int(v),
                            "baseline_return_risk": fallback_data.get("baseline_return_risk", 20),
                            "typical_cost_per_wear_ceiling": fallback_data.get("typical_cost_per_wear_ceiling", 3.50),
                        }
                return result
        except Exception as e:
            logger.warning("Failed loading wear_baselines.json, using fallback: %s", e)
    return DEFAULT_CATEGORY_BASELINES


def normalize_category_key(raw_category: str | None) -> str:
    if not raw_category:
        return "top"
    cleaned = raw_category.strip().lower()

    if cleaned in {"top", "shirt", "t-shirt", "blouse", "sweater", "hoodie", "polo", "tank"}:
        return "top"
    if cleaned in {"bottom", "pants", "jeans", "trousers", "shorts", "skirt", "leggings", "sweatpants"}:
        return "bottom"
    if cleaned in {"outerwear", "jacket", "coat", "blazer", "cardigan", "vest"}:
        return "outerwear"
    if cleaned in {"dress", "jumpsuit", "romper", "one-piece"}:
        return "dress"
    if cleaned in {"footwear", "shoes", "sneakers", "boots", "heels", "sandals", "loafers", "flats"}:
        return "footwear"
    if cleaned in {"accessory", "bag", "belt", "hat", "scarf", "jewelry"}:
        return "accessory"

    return "top"


def calculate_cost_per_wear(category: str | None, price: float) -> dict:
    if price is None or price <= 0:
        raise ValueError("Price must be a positive number to calculate cost-per-wear.")

    baselines = load_wear_baselines()
    cat_key = normalize_category_key(category)
    cat_data = baselines.get(cat_key, baselines.get("top", {"annual_wears": 30}))
    baseline_wears = cat_data["annual_wears"]

    cpw = round(price / float(baseline_wears), 2)

    return {
        "cost_per_wear": cpw,
        "baseline_wears_used": baseline_wears,
        "category": cat_key,
        "price": price,
    }


def normalize_fit_tightness(fit_tightness: str | None) -> tuple[str, int, str]:
    if not fit_tightness:
        return "unspecified", 0, "unspecified fit"

    cleaned = fit_tightness.strip().lower()
    if any(k in cleaned for k in ["tight", "snug", "small"]):
        return "tight", 25, "tight fit"
    if any(k in cleaned for k in ["oversized", "loose", "baggy", "large"]):
        return "oversized", 15, "oversized fit"
    if any(k in cleaned for k in ["regular", "relaxed", "perfect", "true", "standard"]):
        return "regular", -5, "regular/relaxed fit"

    return "unspecified", 0, "unspecified fit"


def calculate_return_risk(category: str | None, fit_tightness: str | None) -> dict:
    baselines = load_wear_baselines()
    cat_key = normalize_category_key(category)
    cat_data = baselines.get(cat_key, baselines.get("top", {"baseline_return_risk": 20}))
    baseline_risk = cat_data["baseline_return_risk"]

    norm_fit, fit_adj, fit_desc = normalize_fit_tightness(fit_tightness)

    raw_score = baseline_risk + fit_adj
    capped_score = max(0, min(100, raw_score))

    if fit_adj > 0:
        reasoning = (
            f"{fit_desc.capitalize()} (+{fit_adj}%) on a {cat_key} with an already-elevated baseline return risk "
            f"of {baseline_risk}% increases total return risk to {capped_score}%."
        )
    elif fit_adj < 0:
        reasoning = (
            f"{fit_desc.capitalize()} ({fit_adj}%) on a {cat_key} with a baseline return risk of {baseline_risk}% "
            f"reduces total return risk to {capped_score}%."
        )
    else:
        reasoning = (
            f"{fit_desc.capitalize()} (+0%) on a {cat_key} yields a return risk equal to category baseline "
            f"of {capped_score}%."
        )

    return {
        "return_risk_score": capped_score,
        "baseline_risk": baseline_risk,
        "fit_adjustment": fit_adj,
        "fit_tightness": norm_fit,
        "reasoning": reasoning,
    }
