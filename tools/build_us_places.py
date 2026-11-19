#!/usr/bin/env python3
"""Regenerate tools/us-places.json.gz from the zipcodes package's data file (zips.json.bz2).

Usage: python3 tools/build_us_places.py path/to/zips.json.bz2 tools/us-places.json.gz
The data file comes from the zipcodes package (PyPI, MIT licence); this script reads it and
never imports the package. Each US place name ("city|st", lower case, including the ZIP's
acceptable alternative names) maps to the distinct ZIP-code centroids that carry it, rounded
to 0.01 degrees (about 1 km). tools/conditions.py measures the straight-line distance from the
user's center to the nearest of them.
"""
import bz2
import gzip
import json
import sys


def build(src):
    places = {}
    for z in json.load(bz2.open(src)):
        if not z.get("lat"):
            continue
        point = (round(float(z["lat"]), 2), round(float(z["long"]), 2))
        for name in [z["city"]] + z.get("acceptable_cities", []):
            places.setdefault(f'{name.lower()}|{z["state"].lower()}', set()).add(point)
    return {"source": "US ZIP code centroids from the zipcodes 1.2.0 package (PyPI, MIT licence); "
                      "distinct centroids per place name, rounded to 0.01 degrees",
            "places": {k: sorted(v) for k, v in sorted(places.items())}}


if __name__ == "__main__":
    src, out = sys.argv[1], sys.argv[2]
    doc = build(src)
    data = json.dumps(doc, separators=(",", ":"), sort_keys=True).encode()
    with open(out, "wb") as f:
        f.write(gzip.compress(data, mtime=0))
    print(f"{len(doc['places'])} places written to {out}")
