"""
refresh_data.py

Task 4: a lightweight "refresh" script that re-validates and re-builds
data/processed/ outputs on demand. There's no live data feed for this
project -- every source is a manually-researched citation -- so this
doesn't pull anything new by itself. What it *does* do is lay the
groundwork for a real monitoring cadence:

  1. Re-runs the full build pipeline, in dependency order, from the raw
     starter data through every task's additions:
         build_enrichment.py            (Task 1)
         build_impact_refinements.py    (Task 3 calibration)
         build_task4_targets.py         (Task 4 targets)
         build_quality_trust_enrichment.py  (Task 3: Quality/Trust pillar)
  2. Re-validates the resulting workbook (src/validate.py): schema
     conformance against reference_codes.xlsx, no duplicate record_ids, no
     orphaned impact_links, required fields populated, events have blank
     pillar, etc.
  3. Writes a JSON manifest (data/processed/_refresh_manifest.json) with a
     timestamp, per-stage pass/fail, record counts, and any validation
     errors/warnings -- something a dashboard, a cron job, or a CI step can
     all read without re-running the pipeline themselves.
  4. Exits non-zero if any build stage fails OR validation finds a
     structural error, so this is usable as a real monitoring/CI check, not
     just a convenience script.

Run from the project root:
    python refresh_data.py
    python refresh_data.py --quiet     # suppress per-stage stdout, print only the summary
"""
import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

import pandas as pd  # noqa: E402
from data_loader import load_reference_codes  # noqa: E402
from validate import validate_workbook  # noqa: E402
from constants import PIPELINE_STAGE_SCRIPTS, FINAL_DATASET_FILENAME  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
RAW_DIR = PROJECT_ROOT / "data" / "raw"
MANIFEST_PATH = PROCESSED_DIR / "_refresh_manifest.json"

# (script, output file it's expected to produce) -- run in this exact order,
# since each stage reads the previous stage's output. Defined once in
# constants.py so refresh_data.py and any other consumer share one source
# of truth for pipeline ordering.
PIPELINE = PIPELINE_STAGE_SCRIPTS
FINAL_OUTPUT = FINAL_DATASET_FILENAME  # fullest current dataset


def run_pipeline(quiet: bool = False) -> List[dict]:
    """Run each build script in order. Returns a list of per-stage result
    dicts. Raises subprocess.CalledProcessError (propagated) on the first
    stage that fails -- a build failure should stop the pipeline immediately
    rather than validating a partial/stale downstream file."""
    stages = []
    for script, expected_output in PIPELINE:
        script_path = PROJECT_ROOT / script
        result = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=str(PROJECT_ROOT), capture_output=True, text=True,
        )
        stage = dict(script=script, returncode=result.returncode,
                     stdout=result.stdout.strip(), stderr=result.stderr.strip())
        stages.append(stage)
        if not quiet:
            print(f"[{'OK' if result.returncode == 0 else 'FAILED'}] {script}")
            if result.stdout.strip():
                print("  " + result.stdout.strip().replace("\n", "\n  "))
        if result.returncode != 0:
            if not quiet:
                print(f"  stderr:\n  {result.stderr.strip()}")
            raise subprocess.CalledProcessError(result.returncode, script, result.stdout, result.stderr)
        out_path = PROCESSED_DIR / expected_output
        if not out_path.exists():
            raise FileNotFoundError(
                f"{script} exited 0 but did not produce the expected output {out_path}"
            )
    return stages


def refresh(quiet: bool = False) -> dict:
    """Full refresh: rebuild pipeline, validate the final output, write a
    manifest. Returns the manifest dict. Never raises for a VALIDATION
    failure (that's a normal, reportable outcome) -- only raises if a build
    stage itself crashes, since that leaves data/processed/ in an unknown
    state that validation can't meaningfully assess."""
    started_at = datetime.now(timezone.utc)
    stages = run_pipeline(quiet=quiet)

    final_path = PROCESSED_DIR / FINAL_OUTPUT
    main = pd.read_excel(final_path, sheet_name="ethiopia_fi_unified_data")
    links = pd.read_excel(final_path, sheet_name="Impact_sheet")
    ref = load_reference_codes(RAW_DIR / "reference_codes.xlsx")
    report = validate_workbook(main, links, ref)

    manifest = dict(
        refreshed_at=started_at.isoformat(),
        pipeline_stages=[s["script"] for s in stages],
        final_output=FINAL_OUTPUT,
        validation_passed=report.passed,
        validation_errors=report.errors,
        validation_warnings=report.warnings,
        record_counts=report.record_counts,
    )
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2))

    if not quiet:
        print()
        print(f"Validation: {'PASSED' if report.passed else 'FAILED'}")
        for e in report.errors:
            print(f"  ERROR: {e}")
        for w in report.warnings:
            print(f"  warning: {w}")
        print(f"Record counts: {report.record_counts}")
        print(f"Manifest written to {MANIFEST_PATH}")

    return manifest


def load_last_manifest() -> Optional[dict]:
    """Read the manifest without triggering a refresh -- what the dashboard
    calls to show 'last refreshed' status without paying the rebuild cost
    on every page load. Returns None if no refresh has run yet."""
    if not MANIFEST_PATH.exists():
        return None
    try:
        return json.loads(MANIFEST_PATH.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quiet", action="store_true", help="Suppress per-stage stdout")
    args = parser.parse_args()

    try:
        manifest = refresh(quiet=args.quiet)
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"REFRESH FAILED (build stage error, not a validation issue): {e}", file=sys.stderr)
        sys.exit(2)

    sys.exit(0 if manifest["validation_passed"] else 1)


if __name__ == "__main__":
    main()
