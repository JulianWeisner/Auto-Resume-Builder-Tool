"""B5 JD ingestion adapter tests. Standard library (jsonschema optional)."""
import sample_env  # noqa: F401  (must come before the tools: sample person and test criteria)
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
sys.path.insert(0, str(ROOT / "tools"))
import jd_ingest as J  # noqa: E402
from pipeline import validate as validate_run  # noqa: E402

FIXTURES = ROOT / "tests/fixtures/jd"
MANIFEST = json.loads((FIXTURES / "fixtures.json").read_text(encoding="utf-8"))
SCHEMA = json.loads((ROOT / "schemas/jd-artifact.schema.json").read_text(encoding="utf-8"))
try:
    import jsonschema
except ImportError:  # pragma: no cover
    jsonschema = None

SAMPLE = ("About us\n"
          "We build tools for teams.\n"
          "\n"
          "What you'll do\n"
          "• Own the product roadmap for the platform team and work with engineering partners to ship "
          "reliable releases every quarter, and keep customers informed.\n"
          "• Lead discovery.\n")


def sha(b):
    return hashlib.sha256(b).hexdigest()


def fixture(name):
    meta = next(f for f in MANIFEST["fixtures"] if f["file"] == name)
    return (FIXTURES / name).read_bytes(), meta


def lines_of(artifact, prefix, normalized):
    """[first, last] physical lines of the block whose text starts with prefix."""
    canonical = J.reconstruct(artifact, normalized)[0]
    for b in artifact["blocks"]:
        s, e = b["source"]
        if canonical[s:e].lstrip("• ").startswith(prefix):
            return b["lines"]
    raise AssertionError(prefix)


def skip_all_except(artifact, keep):
    """skip map lines covering every block except the given [first, last] ranges."""
    out = []
    for b in artifact["blocks"]:
        a, z = b["lines"]
        if not any(k[0] <= a and z <= k[1] for k in keep):
            out.append(f"skip L{a}-L{z} not under test")
    return out


class Workspace(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, artifact, normalized, name="art"):
        d = self.dir / name
        J.write_artifact(d, artifact, normalized)
        return d

    def tamper(self, d, fn):
        art = json.loads((d / "artifact.json").read_text(encoding="utf-8"))
        fn(art)
        (d / "artifact.json").write_text(J.dump_json(art), encoding="utf-8")

    def codes(self, errors):
        return {e["code"] for e in errors}


class NormalizationTests(Workspace):
    def test_01_deterministic_byte_identical_outputs(self):
        data, _ = fixture("hiringcafe-tl8aedp1i1kufbe9.txt")
        outs = []
        for name in ("a", "b"):
            art, norm = J.ingest(data, "hiringcafe", {"provider_job_id": "tl8aedp1i1kufbe9"})
            d = self.write(art, norm, name)
            outs.append(((d / "artifact.json").read_bytes(), (d / "jd.txt").read_bytes()))
        self.assertEqual(outs[0], outs[1])
        # CLI output equals the library output byte for byte.
        cli = self.dir / "cli"
        meta = self.dir / "meta.json"
        meta.write_text('{"provider_job_id": "tl8aedp1i1kufbe9"}', encoding="utf-8")
        proc = subprocess.run([sys.executable, str(ROOT / "tools/jd_ingest.py"), "ingest", "--source-type",
                               "hiringcafe", "--input", str(FIXTURES / "hiringcafe-tl8aedp1i1kufbe9.txt"),
                               "--meta", str(meta), "--out", str(cli)], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(((cli / "artifact.json").read_bytes(), (cli / "jd.txt").read_bytes()), outs[0])

    def test_02_exact_reconstruction(self):
        text = "﻿Title\r\nCafé — naïve 😀 résumé\tcombining é\r\n\r\n" + "word " * 60 + "end x y"
        art, norm = J.ingest(text.encode("utf-8"), "user_paste", width=30)
        rebuilt, errors = J.reconstruct(art, norm)
        self.assertEqual(errors, [])
        self.assertEqual(rebuilt.encode("utf-8"), text.encode("utf-8"))
        self.assertEqual(art["canonical"]["sha256"], sha(text.encode("utf-8")))
        self.assertEqual(J.validate_artifact(art, norm), [])

    def test_03_unicode_and_utf8_offsets(self):
        text = "é€😀 alpha\nβeta 😀 gamma delta epsilon zeta eta theta iota kappa lambda mu nu xi"
        art, norm = J.ingest(text, "user_paste", width=20)
        raw = text.encode("utf-8")
        for b in art["blocks"]:
            s, e = b["source"]
            self.assertEqual(b["bytes"], [len(text[:s].encode()), len(text[:e].encode())])
            self.assertEqual(raw[b["bytes"][0]:b["bytes"][1]].decode(), text[s:e])
            self.assertEqual(b["sha256"], sha(text[s:e].encode()))
        for ln in art["lines"]:
            ns, ne = ln["normalized"]
            s, e = ln["source"]
            self.assertEqual(norm[ns:ne], text[s:e])
            self.assertEqual(ln["bytes"], [len(text[:s].encode()), len(text[:e].encode())])
        for x in art["insertions"]:
            self.assertEqual(x["bytes"], len(text[:x["source"]].encode()))

    def test_04_real_newlines_preserved(self):
        text = "Line one\r\nLine two\nLine three\rLast"
        art, norm = J.ingest(text, "user_paste")
        self.assertEqual(norm, text)
        self.assertEqual(art["insertions"], [])
        self.assertEqual([ln["terminator"] for ln in art["lines"]], ["source", "source", "source", "none"])
        self.assertEqual(len(art["blocks"]), 4)

    def test_05_synthetic_newlines_distinguishable(self):
        text = "Paragraph " + "lorem ipsum " * 30 + "\nNext"
        art, norm = J.ingest(text, "user_paste", width=40)
        wraps = [x for x in art["insertions"] if x["reason"] == "wrap"]
        self.assertTrue(wraps)
        for x in wraps:
            self.assertEqual(norm[x["normalized"]], "\n")
            self.assertEqual(text[x["source"] - 1], " ")  # inserted after a space, before a word
        synthetic = [ln for ln in art["lines"] if ln["terminator"] == "synthetic"]
        self.assertEqual(len(synthetic), len(wraps))
        self.assertEqual(sum(ln["terminator"] == "source" for ln in art["lines"]), 1)

    def test_06_display_boundary_alignment(self):
        text = "What you'll do: Own the roadmap.Lead the team.   Requirements: 5+ years of experience."
        blocks = ["What you'll do:", "  Own the roadmap.", "Lead the team.", "Requirements:",
                  "5+ years of experience.\n"]
        art, norm = J.ingest(text, "hiringcafe", {"provider_job_id": "x1"}, display_blocks=blocks)
        self.assertEqual(art["normalization"]["method"], "display_blocks+wrap")
        self.assertEqual(art["normalization"]["display_alignment"]["status"], "aligned")
        self.assertEqual([b["kind"] for b in art["blocks"]], ["content"] * 5)
        self.assertEqual(norm.splitlines(), ["What you'll do: ", "Own the roadmap.", "Lead the team.   ",
                                             "Requirements: ", "5+ years of experience."])
        self.assertEqual({x["reason"] for x in art["insertions"]}, {"block_boundary"})
        self.assertEqual(J.reconstruct(art, norm)[0], text)
        self.assertEqual(J.validate_artifact(art, norm), [])
        # Display text that is not verbatim source falls back, or fails when alignment is required.
        bad = ["What you'll do:", "• Own the roadmap.", "Lead the team.", "Requirements:", "5+ years of experience."]
        art2, _ = J.ingest(text, "hiringcafe", {"provider_job_id": "x1"}, display_blocks=bad)
        self.assertEqual(art2["normalization"]["display_alignment"]["status"], "failed")
        self.assertEqual(art2["normalization"]["display_alignment"]["failure"]["code"], "display_block_not_aligned")
        self.assertEqual(art2["normalization"]["method"], "line_blocks+wrap")
        with self.assertRaises(J.IngestError) as cm:
            J.ingest(text, "hiringcafe", {"provider_job_id": "x1"}, display_blocks=bad,
                     require_display_alignment=True)
        self.assertEqual(cm.exception.code, "display_alignment_failed")
        with self.assertRaises(J.IngestError):
            J.ingest(text, "hiringcafe", {"provider_job_id": "x1"}, display_blocks=["What you'll do:"],
                     require_display_alignment=True)  # trailing unaligned text

    def test_07_mechanical_wrapping_fallback(self):
        token = "https://example.org/" + "x" * 150
        text = "intro " + "words and more words " * 20 + token + " tail"
        art, norm = J.ingest(text, "user_paste", width=50)
        self.assertEqual(art["normalization"]["method"], "line_blocks+wrap")
        lines = norm.splitlines()
        self.assertIn(token, lines[-2] + lines[-1])  # the overlong token is never split
        for ln in lines:
            if token not in ln:
                self.assertLessEqual(len(ln), 50)
        self.assertEqual(len(art["blocks"]), 1)
        self.assertEqual(art["normalization"]["width"], 50)
        with self.assertRaises(J.IngestError):
            J.ingest(text, "user_paste", width=5)

    def test_08_user_paste_without_metadata(self):
        art, _ = J.ingest(SAMPLE, "user_paste")
        self.assertEqual(art["source"], {"type": "user_paste", "provenance": {}, "provenance_basis": "user_supplied",
                                         "completeness": {"status": "unknown"}})
        for bad in ({"provider_job_id": "x"}, {"url": ""}, {"supplied_at": "yesterday"}):
            with self.assertRaises(J.IngestError) as cm:
                J.ingest(SAMPLE, "user_paste", bad)
            self.assertEqual(cm.exception.code, "invalid_provenance")
        with self.assertRaises(J.IngestError):
            J.ingest(SAMPLE, "hiringcafe", {})  # provider_job_id is required
        with self.assertRaises(J.IngestError) as cm:
            J.ingest(SAMPLE, "linkedin")
        self.assertEqual(cm.exception.code, "unsupported_source_type")
        art, _ = J.ingest(SAMPLE, "user_paste", completeness="complete")
        self.assertEqual(art["source"]["completeness"], {"status": "complete", "basis": "caller_asserted"})
        # A pasted marker-like string is ordinary text, not provider metadata.
        art, _ = J.ingest(SAMPLE + "\n…(truncated — read the full posting at https://x.y/z)", "user_paste")
        self.assertEqual(art["source"]["completeness"]["status"], "unknown")
        self.assertTrue(all(b["kind"] == "content" for b in art["blocks"]))

    def test_08b_input_decoding(self):
        with self.assertRaises(J.IngestError) as cm:
            J.ingest(b"Valid \xff invalid", "user_paste")
        self.assertEqual((cm.exception.code, cm.exception.details), ("invalid_utf8", {"byte_offset": 6}))
        with self.assertRaises(J.IngestError) as cm:
            J.ingest("lone \ud800 surrogate", "user_paste")
        self.assertEqual(cm.exception.code, "unencodable_text")
        with self.assertRaises(J.IngestError) as cm:
            J.ingest(" \n\t", "user_paste")
        self.assertEqual(cm.exception.code, "empty_source")
        # Text and its UTF-8 bytes give the same artifact.
        self.assertEqual(J.ingest(SAMPLE, "user_paste"), J.ingest(SAMPLE.encode(), "user_paste"))

    def test_09_stable_logical_unit_ids(self):
        a1, _ = J.ingest(SAMPLE, "user_paste", width=40)
        a2, _ = J.ingest(SAMPLE + "Extra closing line.\n", "user_paste", width=40)
        self.assertEqual([b["id"] for b in a1["blocks"]], ["U001", "U002", "U003", "U004", "U005"])
        self.assertEqual(a1["blocks"], a2["blocks"][:5])  # appending text keeps earlier IDs and hashes

    def test_10_wrapped_lines_form_one_block(self):
        data, _ = fixture("hiringcafe-tl8aedp1i1kufbe9.txt")
        art, norm = J.ingest(data, "hiringcafe", {"provider_job_id": "tl8aedp1i1kufbe9"})
        first = art["blocks"][0]
        self.assertEqual(first["lines"], [1, 6])
        self.assertEqual([ln["role"] for ln in art["lines"][:6]],
                         ["start", "continuation", "continuation", "continuation", "continuation", "end"])
        self.assertEqual({ln["block"] for ln in art["lines"][:6]}, {"U001"})
        self.assertEqual([ln["terminator"] for ln in art["lines"][:6]], ["synthetic"] * 5 + ["source"])


class MarkerTests(Workspace):
    def setUp(self):
        super().setUp()
        self.data, _ = fixture("hiringcafe-n74ybfyjvq7jwsrt.txt")
        self.art, self.norm = J.ingest(self.data, "hiringcafe", {"provider_job_id": "n74ybfyjvq7jwsrt"})

    def test_truncation_marker_recorded(self):
        art = self.art
        self.assertEqual(art["source"]["completeness"]["status"], "truncated")
        self.assertEqual(art["source"]["completeness"]["basis"], "provider_marker")
        marker, tail = art["blocks"][-1], art["blocks"][-2]
        self.assertEqual((marker["kind"], marker["selectable"]), ("provider_marker", False))
        self.assertTrue(tail["truncated_tail"])
        self.assertFalse(tail["selectable"])
        self.assertTrue(all(b["selectable"] for b in art["blocks"][:-2]))
        with self.assertRaises(J.IngestError) as cm:
            J.ingest(self.data, "hiringcafe", {"provider_job_id": "n"}, completeness="complete")
        self.assertEqual(cm.exception.code, "conflicting_completeness")

    def test_marker_and_tail_not_selectable(self):
        marker, tail = self.art["blocks"][-1], self.art["blocks"][-2]
        _, errors = J.check_map(self.art, self.norm, [f"About-1 L{tail['lines'][0]}-L{tail['lines'][1]}",
                                                      f"About-2 L{marker['lines'][0]}-L{marker['lines'][1]}"])
        self.assertEqual(self.codes(errors), {"selection_in_truncated_tail", "selection_in_marker"})


class GuardTests(Workspace):
    def setUp(self):
        super().setUp()
        self.data, _ = fixture("hiringcafe-tl8aedp1i1kufbe9.txt")
        self.art, self.norm = J.ingest(self.data, "hiringcafe", {"provider_job_id": "tl8aedp1i1kufbe9"})
        self.canonical = J.reconstruct(self.art, self.norm)[0]

    def test_11_one_quote_across_wrapped_fragments(self):
        a, z = lines_of(self.art, "The Admissions team", self.norm)
        self.assertGreater(z, a)
        items, errors = J.check_map(self.art, self.norm, [f"About-1 L{a}-L{z}"])
        self.assertEqual(errors, [])
        whole = items[0]
        block = next(b for b in self.art["blocks"] if b["lines"] == [a, z])
        self.assertEqual(whole["quote"], self.canonical[block["source"][0]:block["source"][1]])
        self.assertNotIn("\n", whole["quote"])
        # The spans overlap, so the pair is rejected; each alone is valid.
        _, errors = J.check_map(self.art, self.norm, [f"About-1 L{a}-L{z}",
                                                      f'Role-1 L{a}-L{z} "We orchestrate" ... "delightfully."'])
        self.assertIn("selection_overlap", self.codes(errors))
        items, errors = J.check_map(self.art, self.norm, [
            f'About-1 L{a}-L{z} "The Admissions team" ... "venue entry."',
            f'Role-1 L{a}-L{z} "We orchestrate" ... "reliably and delightfully."',
            f'About-2 L{a}-L{z} "When things go wrong" ... "marketplace trust."'])
        self.assertEqual(errors, [])
        q = items[1]
        self.assertEqual(q["quote"], "We orchestrate a real-time fulfillment network connecting sellers, partners, "
                                     "and systems to get buyers in reliably and delightfully.")
        self.assertEqual(self.canonical[q["source"][0]:q["source"][1]], q["quote"])
        self.assertEqual(self.data[q["bytes"][0]:q["bytes"][1]].decode(), q["quote"])
        self.assertEqual(q["quote_sha256"], sha(q["quote"].encode()))
        crossed = [x for x in self.art["insertions"] if q["source"][0] < x["source"] < q["source"][1]]
        self.assertTrue(crossed)  # the quote spans at least one synthetic newline
        self.assertEqual(q["split_of"], block["id"])

    def test_12_intentional_semantic_split(self):
        a, z = lines_of(self.art, "Buyer and seller policy decisions", self.norm)
        items, errors = J.check_map(self.art, self.norm, [
            f'Want-1 L{a}-L{z} "Buyer and seller policy decisions" ... "and non-payment"',
            f'Want-2 L{a}-L{z} "—are more" ... "adaptable."'])
        self.assertEqual(errors, [])
        self.assertEqual({i["split_of"] for i in items}, {items[0]["blocks"][0]})
        # A split may sit inside one physical line of a multi-line block.
        a2, z2 = lines_of(self.art, "Create clarity around decision rights", self.norm)
        items, errors = J.check_map(self.art, self.norm, [
            f'Do-1 L{a2} "Create clarity around decision rights" ... "escalation paths, and ownership"',
            f'Do-2 L{a2}-L{z2} "across" ... "Customer Experience."'])
        self.assertEqual(errors, [])
        self.assertLess(items[0]["lines"][1], z2)

    def test_13_accidental_partial_unit_rejected(self):
        a, z = lines_of(self.art, "High-stakes marketplace decisions", self.norm)
        _, errors = J.check_map(self.art, self.norm, [f"Want-1 L{a}"])
        self.assertEqual(self.codes(errors), {"wrap_fragment"})
        _, errors = J.check_map(self.art, self.norm, [f"Want-1 L{a}", f"Want-2 L{z}"])
        self.assertEqual(self.codes(errors), {"wrap_fragment"})
        # A quoted span that leaves the rest of its block untagged is incomplete.
        _, errors = J.check_map(self.art, self.norm, [f'Want-1 L{a}-L{z} "High-stakes" ... "senior leadership"'])
        self.assertEqual(self.codes(errors), {"split_remainder_uncovered"})
        # Two spans that meet exactly at a synthetic wrap, mid-phrase, are wrap-derived.
        wrap = next(x for x in self.art["insertions"]
                    if x["reason"] == "wrap" and self.art["lines"][a - 1]["source"][1] == x["source"])
        left = self.canonical[self.art["lines"][a - 1]["source"][0]:wrap["source"]].split()
        right = self.canonical[wrap["source"]:self.art["lines"][z - 1]["source"][1]].split()
        _, errors = J.check_map(self.art, self.norm, [
            f'Want-1 L{a}-L{z} "{" ".join(left[1:3])}" ... "{left[-1]}"',
            f'Want-2 L{a}-L{z} "{right[0]}" ... "{right[-1]}"'])
        self.assertIn("split_at_wrap_boundary", self.codes(errors))

    def test_18_invalid_logical_boundaries_in_map(self):
        a, z = lines_of(self.art, "Buyer and seller policy decisions", self.norm)
        a2, z2 = lines_of(self.art, "The company can clearly measure", self.norm)
        _, errors = J.check_map(self.art, self.norm, [f'Want-1 L{a}-L{z2} "explainable" ... "clearly measure"'])
        self.assertEqual(self.codes(errors), {"block_boundary_crossed"})
        _, errors = J.check_map(self.art, self.norm, [f"skip L{a}-L{a} half a bullet"])
        self.assertEqual(self.codes(errors), {"skip_partial_block"})
        _, errors = J.check_map(self.art, self.norm, [f"skip L{a}-L{z} whole", f"Want-1 L{a}-L{z}"])
        self.assertEqual(self.codes(errors), {"skip_overlaps_selection"})
        _, errors = J.check_map(self.art, self.norm, ["Want-1 L999", "nonsense", f'Want-2 L{a} "absent words"'])
        self.assertEqual(self.codes(errors), {"line_range_invalid", "map_parse_error", "span_not_found"})


class PersistenceTests(Workspace):
    def setUp(self):
        super().setUp()
        art, norm = J.ingest(SAMPLE, "user_paste", {"company": "Example"}, width=40)
        self.d = self.write(art, norm)
        self.art, self.norm = art, norm

    def render_sample(self, extra=()):
        a, z = lines_of(self.art, "Own the product roadmap", self.norm)
        d1 = lines_of(self.art, "Lead discovery", self.norm)
        about = lines_of(self.art, "We build tools", self.norm)
        map_lines = [f"About-1 L{about[0]}-L{about[1]}",
                     f'Do-1 L{a}-L{z} "Own the product roadmap" ... "every quarter,"',
                     f'Do-2 L{a}-L{z} "and keep customers informed."',
                     f"Do-3 L{d1[0]}-L{d1[1]}", *extra]
        return J.render(self.d, "\n".join(map_lines) + "\n")

    def test_19_persisted_artifact_revalidation(self):
        self.assertEqual(J.validate_dir(self.d)[2], [])
        code, key, errors, stderr = self.render_sample()
        self.assertEqual((code, errors), (0, []), stderr)
        art, _, errors = J.validate_dir(self.d)
        self.assertEqual(errors, [])
        self.assertEqual([i["tag"] for i in art["selections"]["items"]], ["About-1", "Do-1", "Do-2", "Do-3"])
        self.assertEqual(art["selections"]["renderer"]["sha256"], sha((REPO / "tools/jd_key.py").read_bytes()))
        proc = subprocess.run([sys.executable, str(ROOT / "tools/jd_ingest.py"), "validate", str(self.d)],
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        if jsonschema:
            jsonschema.validate(art, SCHEMA)
            jsonschema.validate(self.art, SCHEMA)

    def test_14_altered_original_text_rejected(self):
        p = self.d / "jd.txt"
        p.write_bytes(p.read_bytes().replace(b"tools", b"toots"))
        self.assertEqual(self.codes(J.validate_dir(self.d)[2]), {"normalized_hash_mismatch"})
        # Even with the normalized hash updated, the canonical hash catches the edit.
        raw = p.read_bytes()
        self.tamper(self.d, lambda a: a["normalized"].update(sha256=sha(raw), utf8_bytes=len(raw)))
        self.assertEqual(self.codes(J.validate_dir(self.d)[2]), {"reconstruction_mismatch"})

    def test_15_invalid_source_and_byte_offsets_rejected(self):
        self.tamper(self.d, lambda a: a["insertions"][0].update(source=a["insertions"][0]["source"] + 1))
        self.assertEqual(self.codes(J.validate_dir(self.d)[2]), {"insertion_invalid"})
        self.write(self.art, self.norm)
        self.tamper(self.d, lambda a: a["insertions"][0].update(bytes=a["insertions"][0]["bytes"] + 1))
        self.assertEqual(self.codes(J.validate_dir(self.d)[2]), {"artifact_mismatch"})
        self.write(self.art, self.norm)
        self.tamper(self.d, lambda a: a["lines"][2].update(bytes=[0, 1]))
        self.assertEqual(self.codes(J.validate_dir(self.d)[2]), {"artifact_mismatch"})
        self.write(self.art, self.norm)
        self.render_sample()
        art, norm, _ = J.validate_dir(self.d)
        canonical = J.reconstruct(art, norm)[0]
        item = art["selections"]["items"][1]
        s, e = item["source"]
        ok = {"tag": "Do-1", "source": [s, e], "quote_sha256": item["quote_sha256"]}
        self.assertEqual(J.verify_quote(art, canonical, ok, item["quote"]), [])
        for bad in ([s - 1, e], [s, e + 40], [e, s], ["0", e]):
            self.assertTrue(J.verify_quote(art, canonical, dict(ok, source=bad), item["quote"]))
        self.tamper(self.d, lambda a: a["selections"]["items"][1].update(bytes=[0, 3]))
        self.assertEqual(self.codes(J.validate_dir(self.d)[2]), {"selections_invalid"})

    def test_16_incorrect_quotes_or_hashes_rejected(self):
        self.render_sample()
        art, norm, _ = J.validate_dir(self.d)
        canonical = J.reconstruct(art, norm)[0]
        item = art["selections"]["items"][1]
        ref = {"tag": "Do-1", "source": item["source"], "quote_sha256": item["quote_sha256"]}
        self.assertTrue(J.verify_quote(art, canonical, dict(ref, quote_sha256="0" * 64), item["quote"]))
        self.assertTrue(J.verify_quote(art, canonical, ref, item["quote"].replace("roadmap", "road map")))
        self.assertTrue(J.verify_quote(art, canonical, dict(ref, tag="Do-9"), item["quote"]))
        self.assertEqual(J.verify_quote(art, canonical, ref, " ".join(item["quote"].split())), [])
        for field, value in (("quote", "Own the roadmap"), ("quote_sha256", "f" * 64),
                             ("source", [0, 5]), ("split_of", None)):
            self.write(self.art, self.norm)
            self.render_sample()
            self.tamper(self.d, lambda a: a["selections"]["items"][1].update({field: value}))
            self.assertEqual(self.codes(J.validate_dir(self.d)[2]), {"selections_invalid"}, field)
        self.tamper(self.d, lambda a: a["selections"]["map"].__setitem__(1, a["selections"]["map"][1] + " "))
        self.assertEqual(self.codes(J.validate_dir(self.d)[2]), {"selections_invalid"})

    def test_17_corrupted_normalized_text_rejected(self):
        p = self.d / "jd.txt"
        ins = self.art["insertions"][0]["normalized"]
        text = self.norm[:ins] + self.norm[ins + 1:]  # drop one synthetic newline
        p.write_bytes(text.encode())
        self.tamper(self.d, lambda a: a["normalized"].update(sha256=sha(text.encode()), utf8_bytes=len(text.encode())))
        self.assertEqual(self.codes(J.validate_dir(self.d)[2]), {"insertion_invalid"})
        p.write_bytes(self.norm.encode()[:5] + b"\xff" + self.norm.encode()[6:])
        self.assertEqual(self.codes(J.validate_dir(self.d)[2]), {"normalized_invalid_utf8"})
        (self.d / "jd.txt").unlink()
        self.assertEqual(self.codes(J.validate_dir(self.d)[2]), {"artifact_unreadable"})

    def test_18_invalid_logical_boundaries_in_artifact(self):
        def move(a):
            a["blocks"][1]["source"][1] -= 3
        self.tamper(self.d, move)
        self.assertEqual(self.codes(J.validate_dir(self.d)[2]), {"artifact_mismatch"})
        self.write(self.art, self.norm)
        self.tamper(self.d, lambda a: a["lines"][5].update(role="single"))
        self.assertEqual(self.codes(J.validate_dir(self.d)[2]), {"artifact_mismatch"})
        self.write(self.art, self.norm)
        self.tamper(self.d, lambda a: a["blocks"][4].update(selectable=False))
        self.assertEqual(self.codes(J.validate_dir(self.d)[2]), {"artifact_mismatch"})
        self.write(self.art, self.norm)
        self.tamper(self.d, lambda a: a["source"]["provenance"].update(retrieved_at="2026-11-15T00:00:00Z"))
        self.assertEqual(self.codes(J.validate_dir(self.d)[2]), {"artifact_mismatch"})
        self.write(self.art, self.norm)
        self.tamper(self.d, lambda a: a.update(schema_version="9"))
        self.assertEqual(self.codes(J.validate_dir(self.d)[2]), {"unsupported_schema_version"})


class IntegrationTests(Workspace):
    def setUp(self):
        super().setUp()
        art, norm = J.ingest(SAMPLE, "user_paste", width=40)
        self.store = self.dir / "artifacts"
        self.d = self.store / art["artifact_id"]
        J.write_artifact(self.d, art, norm)
        self.art, self.norm = art, norm
        a, z = lines_of(art, "Own the product roadmap", norm)
        d1 = lines_of(art, "Lead discovery", norm)
        about = lines_of(art, "We build tools", norm)
        self.map = "\n".join([f"About-1 L{about[0]}-L{about[1]}",
                              f'Do-1 L{a}-L{z} "Own the product roadmap" ... "every quarter,"',
                              f'Do-2 L{a}-L{z} "and keep customers informed."',
                              f"Do-3 L{d1[0]}-L{d1[1]}"]) + "\n"

    def run_with(self, item, quote=None, **ref):
        run = json.loads((ROOT / "tests/fixtures/sample_run.json").read_text())
        job = run["jobs"][0]
        job["jd_artifact"] = {"artifact_id": self.art["artifact_id"], "canonical_sha256": self.art["canonical"]["sha256"]}
        r = job["requirements"][0]
        r["quote"] = item["quote"] if quote is None else quote
        r["quote_status"] = "source_verified"
        r["source"] = {"tag": item["tag"], "source": item["source"], "quote_sha256": item["quote_sha256"], **ref}
        return run

    def test_20_search_run_validation(self):
        code, _, errors, stderr = J.render(self.d, self.map)
        self.assertEqual((code, errors), (0, []), stderr)
        art, norm, _ = J.validate_dir(self.d)
        item = art["selections"]["items"][1]
        run = self.run_with(item)
        self.assertEqual(validate_run(run, self.store), [])
        self.assertTrue(any("without --artifacts" in e for e in validate_run(run)))
        self.assertTrue(any("quote_sha256" in e for e in validate_run(self.run_with(item, quote_sha256="0" * 64),
                                                                     self.store)))
        self.assertTrue(any("exact source slice" in e for e in
                            validate_run(self.run_with(item, quote="Own the product roadmap"), self.store)))
        # An atomized sub-span inside the selection is valid when exact.
        canonical = J.reconstruct(art, norm)[0]
        s = item["source"][0]
        sub = {"tag": "Do-1", "quote": canonical[s:s + 23], "source": [s, s + 23],
               "quote_sha256": sha(canonical[s:s + 23].encode())}
        self.assertEqual(validate_run(self.run_with(sub), self.store), [])
        bad = self.run_with(item)
        bad["jobs"][0]["jd_artifact"]["canonical_sha256"] = "0" * 64
        self.assertTrue(any("does not match" in e for e in validate_run(bad, self.store)))
        bad = self.run_with(item)
        bad["jobs"][0]["requirements"][0]["quote_status"] = "verified-ish"
        self.assertTrue(any("invalid quote_status" in e for e in validate_run(bad, self.store)))
        # A corrupted stored artifact invalidates the claim.
        (self.d / "jd.txt").write_bytes(b"tampered")
        self.assertTrue(any("normalized_hash_mismatch" in e for e in validate_run(self.run_with(item), self.store)))
        # Runs without source references are unchanged.
        plain = json.loads((ROOT / "tests/fixtures/sample_run.json").read_text())
        self.assertEqual(validate_run(plain), [])
        self.assertEqual(validate_run(plain, self.store), [])

    def test_20b_pipeline_cli(self):
        J.render(self.d, self.map)
        art = J.validate_dir(self.d)[0]
        run_path = self.dir / "run.json"
        run_path.write_text(json.dumps(self.run_with(art["selections"]["items"][3])))
        cmd = [sys.executable, str(ROOT / "tools/pipeline.py"), "validate", str(run_path)]
        ok = subprocess.run(cmd + ["--artifacts", str(self.store)], capture_output=True, text=True)
        self.assertEqual(ok.returncode, 0, ok.stderr)
        self.assertIn("1 source-verified", ok.stdout)
        missing = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(missing.returncode, 1)

    def test_21_jd_key_interface(self):
        code, key, errors, stderr = J.render(self.d, self.map, save=self.dir / "tags.json")
        self.assertEqual((code, errors), (0, []), stderr)
        self.assertIn("## Job-description key (verbatim)", key)
        tags = json.loads((self.dir / "tags.json").read_text(encoding="utf-8"))
        art = J.validate_dir(self.d)[0]
        for item in art["selections"]["items"]:
            self.assertEqual(tags[item["tag"]]["text"], item["rendered_text"])
        # The same map rendered directly by jd_key gives the same key.
        direct = subprocess.run([sys.executable, str(REPO / "tools/jd_key.py"), "render", str(self.d / "jd.txt"), "-"],
                                input=self.map, capture_output=True, text=True)
        self.assertEqual((direct.returncode, direct.stdout), (0, key))
        # jd_key's own checks still run after the guard: untagged text is rejected.
        code, _, errors, stderr = J.render(self.d, "\n".join(self.map.splitlines()[1:]))
        self.assertEqual(self.codes(errors), {"renderer_failed"})
        self.assertIn("Uncovered text", stderr)

    def test_21b_guard_runs_before_renderer(self):
        """B4: jd_key render accepts a wrap-derived partial unit; the guard must stop it first."""
        data, _ = fixture("hiringcafe-tl8aedp1i1kufbe9.txt")
        art, norm = J.ingest(data, "hiringcafe", {"provider_job_id": "tl8aedp1i1kufbe9"})
        d = self.write(art, norm, "stubhub")
        a, z = lines_of(art, "Quantify both the immediate", norm)
        self.assertEqual(z, a + 1)
        partial = skip_all_except(art, [[a, z]]) + [f"Do-1 L{a}"]
        direct = subprocess.run([sys.executable, str(REPO / "tools/jd_key.py"), "render", str(d / "jd.txt"), "-"],
                                input="\n".join(partial), capture_output=True, text=True)
        self.assertEqual(direct.returncode, 0, "jd_key alone accepts the partial unit (B4 finding)")
        with mock.patch.object(J.subprocess, "run") as run:
            code, _, errors, _ = J.render(d, "\n".join(partial))
            run.assert_not_called()
        self.assertEqual((code, self.codes(errors)), (1, {"wrap_fragment"}))
        whole = skip_all_except(art, [[a, z]]) + [f"Do-1 L{a}-L{z}"]
        code, _, errors, stderr = J.render(d, "\n".join(whole))
        self.assertEqual((code, errors), (0, []), stderr)
        self.assertEqual(J.validate_dir(d)[2], [])

    def test_cli_errors_are_machine_readable(self):
        bad = self.dir / "bad.txt"
        bad.write_bytes(b"\xff\xfe")
        proc = subprocess.run([sys.executable, str(ROOT / "tools/jd_ingest.py"), "ingest", "--source-type",
                               "user_paste", "--input", str(bad), "--out", str(self.dir / "x")],
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 1)
        self.assertEqual(json.loads(proc.stderr)["errors"][0]["code"], "invalid_utf8")
        self.assertFalse((self.dir / "x").exists())


class FixtureRegressionTests(Workspace):
    def test_22_fixture_hashes_and_determinism(self):
        for meta in MANIFEST["fixtures"]:
            data = (FIXTURES / meta["file"]).read_bytes()
            self.assertEqual(sha(data), meta["canonical_sha256"], meta["file"])
            runs = [J.ingest(data, "hiringcafe", {"provider_job_id": meta["provider_job_id"]}) for _ in range(2)]
            self.assertEqual(runs[0], runs[1])
            art, norm = runs[0]
            self.assertEqual(art["normalized"]["sha256"], meta["normalized_sha256_w100"], meta["file"])
            self.assertEqual(len(art["blocks"]), meta["blocks"])
            self.assertEqual(len(art["lines"]), meta["physical_lines"])
            self.assertEqual(J.reconstruct(art, norm)[0].encode(), data)
            self.assertEqual(J.validate_artifact(art, norm), [])
            if jsonschema:
                jsonschema.validate(art, SCHEMA)

    def test_b4_reference_hashes_documented_not_reproduced(self):
        ref = MANIFEST["b4_reference"]
        self.assertEqual(ref["status"], "not_reproduced")
        present = {sha((FIXTURES / f["file"]).read_bytes()) for f in MANIFEST["fixtures"]}
        self.assertFalse(present & set(ref["canonical_sha256"].values()))


if __name__ == "__main__":
    unittest.main()
