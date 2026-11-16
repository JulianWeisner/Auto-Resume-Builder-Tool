#!/usr/bin/env python3
"""One-step résumé build: render, measure the layout, check, and snapshot decisions.

Usage:
    python3 tools/build_resume.py RESUME.html [--pdf RESUME.pdf] [--max-pages 2]
        [--tags tags.json --terms terms.txt] [--previews]
        [--snapshot FILE ...]
    python3 tools/build_resume.py --check-setup

One command replaces the hand loop of render, count pages, run the check and
inspect page images:

1. Renders the HTML to PDF in Chromium (print media, the template's @page size),
   trying in order: Playwright for Python, Playwright for Node, an installed
   Chrome or Chromium (CHROME_PATH overrides the search; BUILD_RESUME_RENDERER
   =python, node or chrome forces one).
2. Measures the rendered layout and names each problem in words, with its fix:
   - too many pages, and how many lines are over;
   - a heading stranded at the bottom of a page while its content starts on the
     next page (fix: wrap the heading and its first entry in <div class="keep">);
   - a nearly empty last page.
3. Runs tools/resume_check.py (readability, résumé voice, job terms).
4. With --previews, saves small page images for a look when a problem needs one.
5. With --snapshot, copies the decision files (for example fit-check.md,
   tags.json, scores.txt, plan.md, sources.md; --tags and --terms are added
   automatically) into <name>-snapshot/ beside the
   PDF, with the check output, the tool versions and a manifest of hashes (with
   the build time). Each passing build replaces it, so it always matches the
   current résumé. Any report written later is compiled from that snapshot.

Prints "BUILD OK" only when the layout has no problems and the check passes.
Exit 0 on OK, 1 when the résumé needs fixing, 2 when the build cannot run here.
A setup problem prints "BUILD CANNOT RUN (kind)" with one fix:
  missing         a tool is not installed: run --setup
  not downloaded  Playwright's browser is missing: run --setup, or install Chrome
  blocked         the browser exists but the session stopped it: ask once for
                  permission to run this command, then rerun it
  failed          anything else: rerun once, then --check-setup

--setup installs pinned Python packages (PyYAML, pypdf, pypdfium2, Playwright,
pillow) and Chromium into a lasting per-user folder (macOS
~/Library/Caches/resume-tool, Linux ~/.cache/resume-tool; RESUME_TOOL_HOME
overrides), reusing it when it already works. Every tool then restarts itself
in that environment. --check-setup builds a small test résumé end to end and
says READY only when it renders, reads back and passes the check.
Without setup, the build uses the system Python with poppler and Node
Playwright or Chrome when present.
"""
import argparse
import os
import platform
import datetime
import hashlib
import html
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
from resume_check import Poppler, PythonReader, SetupError, has, pdf_reader, tool_home, tool_python, use_tool_env  # noqa: E402
RENDER_JS = r"""
const [html, pdf] = process.argv.slice(1);
let chromium;
try { ({ chromium } = require('playwright')); }
catch (e) { console.error('Node cannot load Playwright: ' + e.message); process.exit(3); }
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  await page.goto('file://' + html, { waitUntil: 'load' });
  await page.emulateMedia({ media: 'print' });
  await page.pdf({ path: pdf, format: 'Letter', preferCSSPageSize: true, printBackground: true });
  await browser.close();
})().catch(e => { console.error(e.message); process.exit(4); });
"""
HEADING = re.compile(r"(?is)<(h[1-4])\b[^>]*>(.*?)</\1>")
SPARSE_LINES = 6  # a last page with fewer text lines than this is nearly empty


FIXES = {
    "missing": "run `python3 tools/build_resume.py --setup` once; it installs what is missing into a "
               "private folder and reuses it afterwards",
    "not downloaded": "run `python3 tools/build_resume.py --setup` (it downloads Chromium), or install Google Chrome",
    "blocked": "the browser is installed but this session stopped it from starting (a sandbox or permission "
               "limit). Ask the user once to approve running `python3 tools/build_resume.py` with permission to "
               "start a browser, then rerun the same command; routine rebuilds reuse that approval",
    "failed": "rerun once; if it fails again, run `python3 tools/build_resume.py --check-setup` and report its output",
}


def die(kind, message):
    """A tool or setup problem: the build cannot run here (exit 2), unlike a résumé problem (exit 1)."""
    print(f"BUILD CANNOT RUN ({kind}): {message}\nFix: {FIXES[kind]}.\n"
          "Until it builds, the résumé is a draft, not built.", file=sys.stderr)
    sys.exit(2)


def run(cmd, **kw):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, **kw)
    except FileNotFoundError:
        die("missing", f"{cmd[0]} is not installed")


CHROME_CANDIDATES = [
    "google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
]


def find_chrome():
    """An installed Chrome or Chromium, or None. CHROME_PATH wins when set."""
    if os.environ.get("CHROME_PATH"):
        path = os.environ["CHROME_PATH"]
        return path if Path(path).is_file() else None
    for name in CHROME_CANDIDATES:
        found = shutil.which(name) or (name if Path(name).is_file() else None)
        if found:
            return found
    return None


def node_playwright():
    if not shutil.which("node"):
        return False
    return subprocess.run(["node", "-e", "require('playwright')"], capture_output=True).returncode == 0


def classify(error):
    e = error.lower()
    if "executable doesn't exist" in e or "playwright install" in e:
        return "not downloaded"
    if any(w in e for w in ("permission denied", "operation not permitted", "eperm", "sandbox", "crashpad",
                            "sigtrap", "sigabrt", "has been closed", "failed to launch", "not allowed")):
        return "blocked"
    return "failed"


def render_python(html_path, pdf):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(timeout=60000)
        except Exception as e:  # its own Chromium is not downloaded: use an installed Chrome
            chrome = find_chrome()
            if not chrome or classify(str(e)) != "not downloaded":
                raise
            browser = p.chromium.launch(executable_path=chrome, timeout=60000)
        page = browser.new_page()
        page.goto(html_path.as_uri(), wait_until="load")
        page.emulate_media(media="print")
        page.pdf(path=str(pdf), format="Letter", prefer_css_page_size=True, print_background=True)
        browser.close()


def render_node(html_path, pdf):
    r = run(["node", "-e", RENDER_JS, str(html_path), str(pdf)], timeout=180)
    if r.returncode:
        raise RuntimeError(r.stderr.strip() or f"exit {r.returncode}")


def render_chrome(html_path, pdf):
    r = run([find_chrome(), "--headless", "--disable-gpu", "--no-sandbox", "--no-pdf-header-footer",
             "--print-to-pdf-no-header", f"--print-to-pdf={pdf}", html_path.as_uri()], timeout=180)
    if not pdf.is_file():
        raise RuntimeError(r.stderr.strip()[-400:] or f"exit {r.returncode}")


RENDERERS = [  # name, available, render
    ("Playwright (Python)", lambda: has("playwright"), render_python),
    ("Playwright (Node)", node_playwright, render_node),
    ("Chrome", lambda: bool(find_chrome()), render_chrome),
]


def render(html_path, pdf):
    """Try each available renderer in order; BUILD_RESUME_RENDERER=python, node or chrome forces one."""
    forced = os.environ.get("BUILD_RESUME_RENDERER", "auto").lower()
    errors = []
    for name, available, fn in RENDERERS:
        if forced != "auto" and forced not in name.lower():
            continue
        if not available():
            continue
        if pdf.exists():
            pdf.unlink()
        try:
            fn(html_path, pdf)
            if pdf.is_file():
                return name
            errors.append((name, "no PDF was written"))
        except Exception as e:
            errors.append((name, str(e).strip().splitlines()[0][:300] if str(e).strip() else type(e).__name__))
    if not errors:
        die("missing", "no PDF renderer found (Playwright for Python or Node, or Chrome/Chromium)")
    kinds = [classify(msg) for _, msg in errors]
    kind = next((k for k in ("blocked", "not downloaded", "failed") if k in kinds), "failed")
    die(kind, "; ".join(f"{n}: {m}" for n, m in errors))


def tool_versions(renderer, reader):
    from importlib.metadata import version, PackageNotFoundError
    out = {"python": platform.python_version(), "system": f"{platform.system()} {platform.machine()}",
           "renderer": renderer, "pdf_reader": reader.version(),
           "tool_env": str(tool_python()) if tool_python() else "none (system Python)"}
    for pkg in ("playwright", "pypdf", "pypdfium2", "PyYAML"):
        try:
            out[pkg] = version(pkg)
        except PackageNotFoundError:
            pass
    if "Chrome" in renderer and find_chrome():
        r = run([find_chrome(), "--version"])
        out["chrome"] = (r.stdout or "").strip()
    return out


# --- Setup and readiness -------------------------------------------------------

PINNED = ["PyYAML==6.0.3", "pypdf==6.17.0", "pypdfium2==5.13.0", "playwright==1.49.1", "pillow==11.3.0"]
FIXTURE = """<!doctype html><html><head><meta charset="utf-8"><style>
@page {{ size: Letter; margin: .75in; }} body {{ font: 10.5pt/13pt Arial, sans-serif; }}
</style></head><body><h1>{name}</h1><p>{location} | {email} | {phone}</p>
<h2>Experience</h2><h3><span>Setup Check Company</span> <span class="date">Jan 2020 - Mar 2021</span></h3>
<ul><li>Ran a readiness test that renders this page, reads its text back and checks its fonts.</li>
<li>Confirmed that the screening check can read every line, so real résumés will build here too.</li></ul>
<h2>Education</h2><p><strong>Example College:</strong> BA, Physics | <strong>2014</strong></p>
</body></html>"""


def readiness():
    """Build a one-page test résumé end to end. Returns (ok, output)."""
    import tempfile
    contact_file = TOOLS.parent / "career" / "contact.json"
    contact = json.loads(contact_file.read_text(encoding="utf-8")) if contact_file.is_file() else {}
    # A new user's contact file is still empty: the test page then uses placeholders,
    # and the check skips contact fields that are empty.
    contact = {k: contact.get(k) or v for k, v in
               {"name": "Setup Check", "location": "Anytown", "email": "", "phone": ""}.items()}
    with tempfile.TemporaryDirectory() as d:
        page = Path(d) / "readiness.html"
        page.write_text(FIXTURE.format(**{k: html.escape(contact.get(k, "")) for k in
                                          ("name", "location", "email", "phone")}), encoding="utf-8")
        r = subprocess.run([sys.executable, str(Path(__file__).resolve()), str(page), "--max-pages", "1"],
                           capture_output=True, text=True, env={**os.environ, "RESUME_TOOL_ENV": "off"})
        return r.returncode == 0, (r.stdout + r.stderr).strip()


def check_setup():
    print(f"Setup check on {platform.system()} {platform.machine()}, Python {platform.python_version()}")
    print(f"  Tool environment: {tool_python() or 'not set up (using this Python)'}")
    items = [
        ("PyYAML (career view)", has("yaml")),
        ("PDF reader: poppler", Poppler.available()),
        ("PDF reader: pypdfium2 + pypdf", PythonReader.available()),
        *[(f"Renderer: {name}", available()) for name, available, _ in RENDERERS],
    ]
    for name, ok in items:
        print(f"  {'✓' if ok else '·'} {name}")
    if find_chrome():
        print(f"    Chrome found at: {find_chrome()}")
    print("  Test build (render, read back, check)…")
    ok, out = readiness()
    for line in out.splitlines()[:6]:
        print("    " + line)
    if ok:
        print("READY: a test résumé rendered, read back and passed the check on this machine.")
        return 0
    print("NOT READY: the test build did not pass. " +
          ("Run `python3 tools/build_resume.py --setup` once." if not tool_python() else
           "Follow the Fix line above."))
    return 2


def candidate_pythons():
    """This Python first, then other installed Python 3 versions: a brand-new Python can lack
    packages for the pinned versions (Python 3.14 did), so setup falls back to an older one."""
    names = [sys.executable] + [f"python3.{m}" for m in range(13, 8, -1)]
    names += [f"{root}/python3.{m}" for m in range(13, 8, -1) for root in
              ("/opt/homebrew/bin", "/usr/local/bin", f"/Library/Frameworks/Python.framework/Versions/3.{m}/bin")]
    seen, out = set(), []
    for n in names:
        path = shutil.which(n) or (n if Path(n).is_file() else None)
        if path and Path(path).resolve() not in seen:
            seen.add(Path(path).resolve())
            out.append(path)
    return out


def setup():
    """Install pinned packages and a browser into a lasting per-user folder; reuse it when it works."""
    home = tool_home()
    if tool_python():
        print(f"Tool environment found: {home}. Checking it…")
        if subprocess.run([str(tool_python()), str(Path(__file__).resolve()), "--check-setup"]).returncode == 0:
            print("Setup already complete; nothing installed.")
            return 0
        print("It is incomplete; repairing.")
    home.mkdir(parents=True, exist_ok=True)
    used = None
    for base in candidate_pythons():
        version = subprocess.run([base, "-c", "import platform; print(platform.python_version())"],
                                 capture_output=True, text=True).stdout.strip()
        print(f"• Python {version} ({base}): create a private environment and install {', '.join(PINNED)}…")
        shutil.rmtree(home / "venv", ignore_errors=True)
        if subprocess.run([base, "-m", "venv", str(home / "venv")], capture_output=True).returncode:
            print("  could not create an environment with it (on Debian or Ubuntu, install python3-venv)")
            continue
        r = subprocess.run([str(tool_python()), "-m", "pip", "install", "--quiet", "--disable-pip-version-check",
                            *PINNED], capture_output=True, text=True)
        if r.returncode == 0:
            used = base
            break
        print("  packages did not install with this Python: " + (r.stderr.strip().splitlines() or ["?"])[-1][:200])
    if not used:
        shutil.rmtree(home / "venv", ignore_errors=True)
        print("Setup stopped: the pinned packages installed with no Python found here. Install Python 3.12 or 3.13 "
              "from python.org (or check the network to the Python package index), then rerun --setup.")
        return 2
    py = str(tool_python())
    print("• Download Chromium for Playwright…")
    env = {**os.environ, "PLAYWRIGHT_BROWSERS_PATH": str(home / "browsers")}
    if subprocess.run([py, "-m", "playwright", "install", "chromium"], env=env,
                      capture_output=True).returncode:
        print("  Chromium download failed" + (f"; using the installed Chrome at {find_chrome()} instead."
                                               if find_chrome() else "; install Google Chrome, then rerun --setup."))
    (home / "setup.json").write_text(json.dumps({"python": py, "base_python": used, "packages": PINNED,
        "set_up_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")}, indent=1) + "\n")
    print(f"Installed in {home}. Checking…")
    return subprocess.run([py, str(Path(__file__).resolve()), "--check-setup"], env=env).returncode


def norm(text):
    return re.sub(r"\s+", " ", text).strip().lower()


def headings(source):
    """Visible text of each h1-h4, with its first child span when the heading
    carries a right-aligned date (the date is its own text run in the PDF)."""
    found = []
    for _, inner in HEADING.findall(source):
        first = re.search(r"(?is)<span\b[^>]*>(.*?)</span>", inner)
        text = html.unescape(re.sub(r"<[^>]+>", " ", first.group(1) if first else inner))
        if norm(text):
            found.append(norm(text))
    return found


def measure(reader, pdf, source, max_pages):
    pages = reader.pages(pdf)
    lines = [[norm(l) for l in reader.page_text(pdf, n).splitlines() if norm(l)] for n in range(1, pages + 1)]
    heads = headings(source)
    problems = []
    if pages > max_pages:
        over = sum(len(p) for p in lines[max_pages:])
        problems.append(f"{pages} pages, target {max_pages}: about {over} lines over. Shorten or cut the "
                        "lowest-value bullets, then rebuild.")
    for n, plines in enumerate(lines[:-1], 1):
        tail = plines[-2:] if plines else []
        for h in heads:
            if tail and tail[-1].startswith(h[:40]):
                problems.append(f"Heading stranded at the bottom of page {n}: \"{h}\". Wrap the heading and its "
                                "first entry in <div class=\"keep\"> so they move together, then rebuild.")
                break
    if pages > 1 and len(lines[-1]) < SPARSE_LINES:
        problems.append(f"The last page holds only {len(lines[-1])} lines. Tighten the previous page or cut a "
                        "bullet so the content ends with no near-empty page.")
    return pages, problems


def snapshot(files, pdf, html_path, versions):
    """One snapshot per résumé (<name>-snapshot/), replaced by each passing build so
    revisions do not pile up. Written beside it first, so a failure keeps the old one."""
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")
    final = pdf.parent / f"{pdf.stem}-snapshot"
    folder = pdf.parent / f".{pdf.stem}-snapshot-new"
    shutil.rmtree(folder, ignore_errors=True)
    folder.mkdir()
    manifest = {"built_at": stamp, "note": "Decisions as they stood when this résumé was built. "
                "A report written later is compiled from these files and labeled as compiled after the build.",
                "tools": versions, "files": {}}
    for f in [*files, str(html_path), str(pdf), str(pdf.with_suffix(".check.txt"))]:
        src = Path(f)
        if not src.is_file():
            print(f"Snapshot not saved: file not found: {f}", file=sys.stderr)
            sys.exit(2)
        shutil.copy2(src, folder / src.name)
        manifest["files"][src.name] = hashlib.sha256(src.read_bytes()).hexdigest()
    (folder / "manifest.json").write_text(json.dumps(manifest, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    shutil.rmtree(final, ignore_errors=True)
    folder.rename(final)
    return final


def main():
    ap = argparse.ArgumentParser(description="One-step résumé build (see module docstring).")
    ap.add_argument("html", nargs="?")
    ap.add_argument("--check-setup", action="store_true", help="test-build a résumé here and report readiness")
    ap.add_argument("--setup", action="store_true", help="install pinned tools into a lasting per-user folder")
    ap.add_argument("--pdf", help="output PDF (default: the HTML path with .pdf)")
    ap.add_argument("--max-pages", type=int, default=2)
    ap.add_argument("--tags")
    ap.add_argument("--terms")
    ap.add_argument("--previews", action="store_true", help="save page images (page-1.png …) beside the PDF")
    ap.add_argument("--snapshot", nargs="+", metavar="FILE", help="decision files to copy into the résumé's snapshot (replaced on each passing build)")
    a = ap.parse_args()
    if a.setup:
        return setup()
    if a.check_setup:
        return check_setup()
    if not a.html:
        ap.error("give the résumé HTML file, or --setup / --check-setup")
    if bool(a.tags) != bool(a.terms):
        ap.error("--tags and --terms go together")
    html_path = Path(a.html).resolve()
    pdf = Path(a.pdf).resolve() if a.pdf else html_path.with_suffix(".pdf")
    if not html_path.is_file():
        ap.error(f"no such HTML file: {html_path}")

    try:
        reader = pdf_reader()
    except SetupError as e:
        die("missing", str(e))
    renderer = render(html_path, pdf)
    try:
        pages, problems = measure(reader, pdf, html_path.read_text(encoding="utf-8"), a.max_pages)
    except SetupError as e:
        die("failed", str(e))

    check_cmd = [sys.executable, str(TOOLS / "resume_check.py"), str(pdf), "--source", str(html_path),
                 "--max-pages", str(a.max_pages), "--json", str(pdf.with_suffix(".check.json"))]
    if a.tags:
        check_cmd += ["--tags", a.tags, "--terms", a.terms]
    check = run(check_cmd)
    if check.returncode == 2:
        die("failed", "résumé check could not run: " + (check.stderr or check.stdout).strip())
    (pdf.with_suffix(".check.txt")).write_text(check.stdout, encoding="utf-8")
    summary = next((l for l in reversed(check.stdout.splitlines()) if l.startswith(("PASS", "FAIL"))), "")
    failing = [l.strip() for l in check.stdout.splitlines()
               if l.strip().startswith("FAIL ") and "Checked:" not in l
               and not (pages > a.max_pages and "Page count" in l)]  # overflow is already reported above

    if a.previews:
        if not reader.previews(pdf, pdf.parent / "page"):
            print("Previews not saved: install poppler's pdftoppm, or run --setup (adds pillow).")

    ok = not problems and check.returncode == 0
    print(("BUILD OK" if ok else "BUILD NEEDS FIXES") + f" · {pages} page(s) · {pdf.name} · rendered with {renderer}")
    print("Check: " + (summary or "(no summary)"))
    for n, p in enumerate(problems + failing, 1):
        print(f"  {n}. {p}")
    print(f"Full check output: {pdf.with_suffix('.check.txt').name}")
    if a.snapshot:
        if ok:
            extra = [f for f in (a.tags, a.terms) if f and Path(f).name not in {Path(x).name for x in a.snapshot}]
            print(f"Decisions saved: {snapshot([*a.snapshot, *extra], pdf, html_path, tool_versions(renderer, reader)).name}/")
        else:
            print("Snapshot not saved: fix the problems first, so the snapshot matches the delivered résumé.")
    return 0 if ok else 1


if __name__ == "__main__":
    use_tool_env()
    sys.exit(main())
