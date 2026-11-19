"""Test setup shared by the search tests: import it before the tools.

The tests never read your own career record or criteria. Record IDs and the capability profile come
from the made-up sample person (examples/sample-person, through ARB_CAREER_REPO, which command-line
runs inherit). Conditions and search families come from a made-up New York searcher
(fixtures/criteria-nyc.yaml), because the location and pay cases are written for New York.
"""
import os
from pathlib import Path

TESTS = Path(__file__).resolve().parent
REPO = TESTS.parents[1]
SAMPLE = REPO / "examples" / "sample-person"
CRITERIA = TESTS / "fixtures" / "criteria-nyc.yaml"
PROFILE = SAMPLE / "career" / "capability-profile.yaml"

os.environ["ARB_CAREER_REPO"] = str(SAMPLE)
