#!/usr/bin/env python3
"""Shared location, workplace and travel conditions for search L1 and Stage 1.

One rule set, read from the `conditions` block of career/search-criteria.yaml
(career/preferences.md is authoritative). Pay, posting age and deadlines are
search-only filters and stay in job-search/tools/pipeline.py.

Rules:
- Onsite or hybrid: pass when any listed location is within `radius_miles` of the user's
  `center` (a US place, "City, ST"), measured in a straight line to the place's nearest ZIP-code
  centroid (tools/us-places.json.gz). A known US place beyond the radius fails. A place the list
  cannot find, or a region only partly inside (`partly_inside`, or a bare state that reaches the radius), is
  unknown: ask. A bare state wholly beyond the radius fails.
- `metro_aliases` are names a posting uses for the user's whole area ("NYC", "Bay Area"): they pass.
- Remote: pass when US-based or no location is given. A remote role based outside the US is
  unknown (ask), because `remote_outside_us: ask` (work authorization covers US roles only).
- A workplace type the user does not accept (`acceptable_workplaces`) fails.
- Travel above `travel_percent_max` is unknown (ask), never a failure.
Places outside the US are not in the list: an onsite or hybrid role there is unknown unless the
posting is plainly abroad, and the agent asks.

Usage (Stage 1):
    python3 tools/conditions.py --location "Dublin, OH" --workplace hybrid [--travel 25]
Prints JSON {"result": pass|fail|unknown, "reasons": [...]}. Requires PyYAML for the criteria file.
"""
import argparse
import gzip
import json
import math
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
# ARB_CAREER_REPO points the tools at another career folder (the tests use the sample person).
DEFAULT_CRITERIA = Path(os.environ.get("ARB_CAREER_REPO") or REPO) / "career" / "search-criteria.yaml"
GAZETTEER = HERE / "us-places.json.gz"

STATES = {
    "alabama": "al", "alaska": "ak", "arizona": "az", "arkansas": "ar", "california": "ca", "colorado": "co",
    "connecticut": "ct", "delaware": "de", "district of columbia": "dc", "florida": "fl", "georgia": "ga",
    "hawaii": "hi", "idaho": "id", "illinois": "il", "indiana": "in", "iowa": "ia", "kansas": "ks",
    "kentucky": "ky", "louisiana": "la", "maine": "me", "maryland": "md", "massachusetts": "ma",
    "michigan": "mi", "minnesota": "mn", "mississippi": "ms", "missouri": "mo", "montana": "mt",
    "nebraska": "ne", "nevada": "nv", "new hampshire": "nh", "new jersey": "nj", "new mexico": "nm",
    "new york": "ny", "north carolina": "nc", "north dakota": "nd", "ohio": "oh", "oklahoma": "ok",
    "oregon": "or", "pennsylvania": "pa", "rhode island": "ri", "south carolina": "sc", "south dakota": "sd",
    "tennessee": "tn", "texas": "tx", "utah": "ut", "vermont": "vt", "virginia": "va", "washington": "wa",
    "west virginia": "wv", "wisconsin": "wi", "wyoming": "wy", "puerto rico": "pr",
}
ABBREVIATIONS = set(STATES.values())
US = {"united states", "united states of america", "usa", "us", "u.s.", "u.s.a."}
REMOTE_ANYWHERE = {"remote", "anywhere", "worldwide", "global", ""}
# Bare names that place a posting outside the US even without a "City, Region" pattern.
FOREIGN = {"canada", "india", "ireland", "united kingdom", "uk", "england", "london", "germany", "mexico", "france",
           "spain", "netherlands", "poland", "brazil", "philippines", "australia", "singapore", "israel", "japan",
           "china", "portugal", "argentina", "colombia", "emea", "europe", "apac", "latam", "toronto", "dublin",
           "bangalore", "bengaluru", "berlin", "paris", "amsterdam", "tel aviv", "sydney", "vancouver", "montreal"}
WORKPLACES = ("remote", "hybrid", "onsite")
EARTH_MILES = 3958.8

_gazetteer = None


def gazetteer():
    global _gazetteer
    if _gazetteer is None:
        _gazetteer = json.loads(gzip.decompress(GAZETTEER.read_bytes()))["places"]
    return _gazetteer


def load_conditions(criteria_path=None):
    import yaml
    with open(criteria_path or DEFAULT_CRITERIA, encoding="utf-8") as f:
        return (yaml.safe_load(f) or {}).get("conditions") or {}


def names(conditions, key):
    return {str(x).strip().lower() for x in conditions.get(key) or [] if str(x).strip()}


def segments(location):
    """Split a multi-location string; 'or' splits only in lower case so 'Portland, OR' survives."""
    parts = re.split(r"\s+or\s+|;|\||\s/\s|\n|\s•\s", location or "")
    return [p.strip(" ,.") for p in parts if p.strip(" ,.")]


def place(segment, conditions=None):
    """('us', city, state) | ('foreign', None, None) | ('unknown', None, None) for one location."""
    conditions = conditions or {}
    tokens = [t.strip().lower() for t in segment.split(",") if t.strip()]
    tokens = [re.sub(r"\s*\(.*?\)\s*|\b\d{5}(-\d{4})?\b", "", t).strip() for t in tokens]
    tokens = [t for t in tokens if t]
    country_us = bool(tokens) and tokens[-1] in US
    if country_us:
        tokens = tokens[:-1]
    if not tokens:
        return ("us", None, None) if country_us else ("unknown", None, None)
    last = tokens[-1]
    state = last if last in ABBREVIATIONS else STATES.get(last)
    if state and len(tokens) >= 2:
        return "us", tokens[-2], state
    if state:  # a bare state name; "New York" alone means the city
        return ("us", "new york", "ny") if last == "new york" else ("us", None, state)
    if last in names(conditions, "metro_aliases") or last in names(conditions, "partly_inside"):
        return "us", last, None
    if country_us:
        return "unknown", None, None
    if any(t in FOREIGN for t in tokens):
        return "foreign", None, None
    # "City, Region" whose last part is not a US state reads as outside the US; a single bare name is unknown.
    return ("foreign", None, None) if len(tokens) >= 2 else ("unknown", None, None)


def url_segment(url):
    """HiringCafe job URLs end with '<title>-<company>-<city>-<state>-<job id>'; the location text
    sometimes drops the state. Returns 'city, st' when the slug ends in a state, else None."""
    slug = re.sub(r"[?#].*", "", url or "").rstrip("/").rsplit("/", 1)[-1]
    words = slug.lower().split("-")[:-1]
    for n in (2, 1):  # "new-jersey" or "nj"
        name = " ".join(words[-n:])
        state = STATES.get(name) or (name if n == 1 and name in ABBREVIATIONS else None)
        if state and len(words) > n:
            before = words[:-n]
            for k in (3, 2, 1):  # longest place name the list knows
                city = " ".join(before[-k:])
                if f"{city}|{state}" in gazetteer():
                    return f"{city}, {state}"
            return f"{before[-1]}, {state}"
    return None


def miles(a, b):
    (lat1, lon1), (lat2, lon2) = a, b
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_MILES * math.asin(math.sqrt(h))


def center_point(conditions):
    """(lat, lon) of the user's center: center_lat/center_lon, or the "City, ST" in `center`."""
    if conditions.get("center_lat") is not None and conditions.get("center_lon") is not None:
        return float(conditions["center_lat"]), float(conditions["center_lon"])
    kind, city, state = place(str(conditions.get("center") or ""))
    points = gazetteer().get(f"{city}|{state}") if kind == "us" and city and state else None
    if not points:
        return None
    return (sum(p[0] for p in points) / len(points), sum(p[1] for p in points) / len(points))


def center_name(conditions):
    return str(conditions.get("center") or "your center")


def distance(city, state, conditions):
    """Miles from the user's center to the nearest ZIP centroid of the place, or None when it cannot be placed."""
    if city in names(conditions, "metro_aliases"):
        return 0
    if city is None or state is None:
        return None
    origin = center_point(conditions)
    points = gazetteer().get(f"{city}|{state}")
    if origin is None or not points:
        return None
    return round(min(miles(origin, p) for p in points))


def state_distance(state, conditions):
    """Miles from the user's center to the nearest place in a state, or None when the center is unknown."""
    origin = center_point(conditions)
    if origin is None:
        return None
    suffix = "|" + state
    return round(min((miles(origin, p) for k, pts in gazetteer().items() if k.endswith(suffix) for p in pts),
                     default=float("inf")))


def workplace_kind(workplace):
    w = (workplace or "").lower().replace("-", "").replace(" ", "")
    return next((k for k in WORKPLACES if k in w), None)


def check_location(location, workplace, conditions, url=None):
    """Location and workplace only. Returns (pass|fail|unknown, reasons)."""
    radius = conditions.get("radius_miles")
    where = center_name(conditions)
    kind_of_work = workplace_kind(workplace)
    accepted = names(conditions, "acceptable_workplaces")
    if accepted and kind_of_work and kind_of_work not in accepted:
        return "fail", [f"{kind_of_work} work is not among the accepted workplaces ({', '.join(sorted(accepted))})"]
    segs = segments(location)
    from_url = None
    if url and segs and all(place(s, conditions)[0] != "us" or place(s, conditions)[2] is None for s in segs):
        from_url = url_segment(url)
        if from_url:
            city = from_url.rsplit(",", 1)[0]
            same = [s for s in segs if s.lower() == city]
            segs = [from_url if s.lower() == city else s for s in segs] if same else segs + [from_url]
    if kind_of_work == "remote":
        kinds = [place(s, conditions)[0] for s in segs]
        if "us" in kinds or not segs or any(s.lower() in REMOTE_ANYWHERE for s in segs) or "foreign" not in kinds:
            return "pass", ["remote role"]
        return "unknown", [f"remote role based outside the US ('{location}'); work authorization covers US roles only, so ask"]
    if not segs:
        return "unknown", ["no location stated; confirm the permitted work region"]
    if radius is None or center_point(conditions) is None:
        return "unknown", [f"no search center and radius recorded (career/search-criteria.yaml); ask whether '{location}' works"]
    unknown, outside = [], []
    for s in segs:
        kind, city, state = place(s, conditions)
        if kind == "foreign":
            outside.append(f"'{s}' is outside the US")
            continue
        if kind != "us":
            unknown.append(f"'{s}' could not be placed")
            continue
        if city is None and state:
            nearest = state_distance(state, conditions)
            if nearest is not None and nearest > radius:
                outside.append(f"'{s}' is a state beyond {radius} miles of {where} (nearest place about {nearest})")
            else:
                unknown.append(f"'{s}' is only partly within {radius} miles of {where}; confirm the office")
            continue
        if city in names(conditions, "partly_inside"):
            unknown.append(f"'{s}' is only partly within {radius} miles of {where}; confirm the office")
            continue
        dist = distance(city, state, conditions)
        if dist is None:
            unknown.append(f"'{s}' is not in the place list; confirm its distance from {where}")
        elif dist <= radius:
            note = " (state taken from the posting URL)" if s == from_url else ""
            return "pass", [f"'{s}' is about {dist} miles from {where}, within {radius}{note}"]
        else:
            outside.append(f"'{s}' is beyond {radius} miles of {where} (about {dist})")
    if unknown:
        return "unknown", unknown + outside
    return "fail", [f"location '{location}' with workplace '{workplace or ''}': " + "; ".join(outside)]


def check(location, workplace, conditions, travel=None, url=None):
    result, reasons = check_location(location, workplace, conditions, url)
    limit = conditions.get("travel_percent_max", 50)
    if result == "pass" and isinstance(travel, (int, float)) and limit is not None and travel > limit:
        result = "unknown"
        reasons.append(f"travel {travel:g}% is above the confirmed {limit}%; ask")
    return result, reasons


def main(argv=None):
    ap = argparse.ArgumentParser(description="Check a posting's location, workplace and travel against the shared conditions.")
    ap.add_argument("--location", default="")
    ap.add_argument("--workplace", default="")
    ap.add_argument("--travel", type=float)
    ap.add_argument("--criteria")
    a = ap.parse_args(argv)
    result, reasons = check(a.location, a.workplace, load_conditions(a.criteria), a.travel)
    print(json.dumps({"result": result, "reasons": reasons}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
