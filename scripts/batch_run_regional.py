#!/usr/bin/env python3
"""Batch runner and validation script for Regional SUVR-to-Centiloid conversions.

Handles:
  1. Fluorinated SUVR -> Direct Centiloids (*-SUVRSFlu-* -> *-CLFlu-*_tool.csv)
  2. Fluorinated SUVR -> PiB-equivalent SUVR (*-SUVRSFlu-* -> *-SUVRSPIB-*_tool.csv)
  3. Converted PiB SUVR -> Centiloids (*-SUVRSPIB-*_tool.csv -> *-CLPIB-fromFlu-*_tool.csv)
  4. Actual PiB SUVR -> Centiloids (*-SUVRSPiB-* -> *-CLPiB-*_tool.csv)
"""

import sys
from pathlib import Path

# Add repository root directory to sys.path so pet_conversion can be imported
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Now import pet_conversion modules
from pet_conversion.regional_fluorinate_suvr_to_cl import (
    convert_SUVR_to_CL_withRegionalFormula,
)
from pet_conversion.regional_fluorinate_to_pib_suvr import (
    convert_SUVR_to_PiBSUVR_withRegionalFormula,
)
from pet_conversion.regional_pib_suvr_to_cl import (
    convert_PiBSUVR_to_CL_withRegionalFormula,
)


def run_batch_regional_conversions(base_test_dir: Path, equations_dir: Path):
    """Executes tabular conversions for all 4 cohorts including actual PiB SUVR."""
    input_dir = base_test_dir / "InputTables"
    out_dir = base_test_dir / "OutTables"
    out_dir.mkdir(parents=True, exist_ok=True)

    tracers = ["FBB", "FBP", "FMM", "NAV"]

    print("=================================================================")
    print("RUNNING REGIONAL CONVERSIONS ON EXAMPLE TABLES")
    print(f"Input Directory:     {input_dir.resolve()}")
    print(f"Output Directory:    {out_dir.resolve()}")
    print(f"Equations Directory: {equations_dir.resolve()}")
    print("=================================================================\n")

    # -----------------------------------------------------------------
    # PART 1: Conversions starting from Fluorinated SUVR
    # -----------------------------------------------------------------
    print(">>> PART 1: Conversions from Fluorinated SUVR (Direct & Stepwise)")
    for tracer in tracers:
        input_suvr_flu = input_dir / f"{tracer}-SUVRSFlu-PETREG-standard.csv"
        out_cl_flu = out_dir / f"{tracer}-CLFlu-PETREG-standard_tool.csv"
        out_pib_equiv = out_dir / f"{tracer}-SUVRSPIB-PETREG-standard_tool.csv"
        out_cl_via_pib = out_dir / f"{tracer}-CLPIB-fromFlu-PETREG-standard_tool.csv"

        print(f"\n--- Tracer: {tracer} (Fluorinated) ---")
        if not input_suvr_flu.is_file():
            print(f"[SKIPPED] Missing input file: {input_suvr_flu.name}")
            continue

        # 1A. Direct 18F-SUVR -> Centiloids
        print(f"1A. {tracer} SUVR -> Direct Centiloids...")
        df_cl_direct = convert_SUVR_to_CL_withRegionalFormula(
            SUVRtab_input=input_suvr_flu,
            conversionTab_fp=equations_dir,
            output_fp=out_cl_flu,
            drop_unconverted_rois=True,
        )
        print(f"    -> Wrote: {out_cl_flu.name} (Shape: {df_cl_direct.shape})")

        # 1B. 18F-SUVR -> PiB SUVR equivalent
        print(f"1B. {tracer} SUVR -> PiB SUVR equivalent...")
        df_pib_equiv = convert_SUVR_to_PiBSUVR_withRegionalFormula(
            SUVRtab_input=input_suvr_flu,
            conversionTab_fp=equations_dir,
            output_fp=out_pib_equiv,
            drop_unconverted_rois=True,
        )
        print(f"    -> Wrote: {out_pib_equiv.name} (Shape: {df_pib_equiv.shape})")

        # 1C. Converted PiB SUVR -> Centiloids
        print(f"1C. Converted PiB SUVR -> Centiloids...")
        df_cl_via_pib = convert_PiBSUVR_to_CL_withRegionalFormula(
            SUVRtab_input=df_pib_equiv,
            conversionTab_fp=equations_dir,
            output_fp=out_cl_via_pib,
            drop_unconverted_rois=True,
        )
        print(f"    -> Wrote: {out_cl_via_pib.name} (Shape: {df_cl_via_pib.shape})")

    # -----------------------------------------------------------------
    # PART 2: Actual PiB SUVR -> Centiloids
    # -----------------------------------------------------------------
    print("\n\n>>> PART 2: Conversion of Actual PiB SUVR Tables")
    for tracer in tracers:
        input_suvr_pib = input_dir / f"{tracer}-SUVRSPiB-PETREG-standard.csv"
        out_cl_pib = out_dir / f"{tracer}-CLPiB-PETREG-standard_tool.csv"

        print(f"\n--- Cohort: {tracer} (Actual PiB SUVR) ---")
        if not input_suvr_pib.is_file():
            print(f"[SKIPPED] Missing input file: {input_suvr_pib.name}")
            continue

        print(f"Converting actual PiB SUVR -> Centiloids...")
        df_cl_actual_pib = convert_PiBSUVR_to_CL_withRegionalFormula(
            SUVRtab_input=input_suvr_pib,
            conversionTab_fp=equations_dir,
            output_fp=out_cl_pib,
            drop_unconverted_rois=True,
        )
        print(f"    -> Wrote: {out_cl_pib.name} (Shape: {df_cl_actual_pib.shape})")

    print("\n=================================================================")
    print("All regional tabular conversions completed.")
    print("=================================================================")


if __name__ == "__main__":
    REPO_ROOT = Path(__file__).resolve().parent.parent
    REGIONAL_BASE_DIR = REPO_ROOT / "examples" / "Regional"
    EQUATIONS_REGIONAL = REPO_ROOT / "equations" / "Regional"

    run_batch_regional_conversions(
        base_test_dir=REGIONAL_BASE_DIR,
        equations_dir=EQUATIONS_REGIONAL,
    )