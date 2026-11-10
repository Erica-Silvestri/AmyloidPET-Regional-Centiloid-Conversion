#!/usr/bin/env python3
"""Batch runner and validation script for Voxel-wise SUVR-to-Centiloid conversions.

Crawls:
    examples/Voxelwise/InputMaps/<TRACER>/
      ├── {group}avg_{TRACER}_2_MNI.nii.gz
      └── {group}avg_PIB_2_MNI.nii.gz

Outputs to:
    examples/Voxelwise/OutputMaps/<TRACER>/
      ├── {group}avg_{TRACER}cl_2_MNI.nii.gz
      └── {group}avg_PIBcl_2_MNI.nii.gz
"""

import sys
from pathlib import Path

# Add repo root to sys.path dynamically so pet_conversion is importable
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from pet_conversion.voxelwise_fluorinate_suvr_to_cl import convert_SUVR_to_CL
from pet_conversion.voxelwise_pib_suvr_to_cl import convert_PiB_SUVR_to_CL


def run_voxelwise_batch_by_folder(
    input_base_dir: Path,
    output_base_dir: Path,
    equations_voxelwise_dir: Path,
):
    """Processes all tracer subdirectories in InputMaps and mirrors structure to OutputMaps."""
    print("=================================================================")
    print("RUNNING VOXEL-WISE CONVERSION BATCH")
    print(f"Input Directory:     {input_base_dir.resolve()}")
    print(f"Output Directory:    {output_base_dir.resolve()}")
    print(f"Equations Directory: {equations_voxelwise_dir.resolve()}")
    print("=================================================================\n")

    if not input_base_dir.is_dir():
        raise FileNotFoundError(f"Input directory not found: {input_base_dir.resolve()}")

    # Find all tracer subdirectories (e.g., NAV, FBB, FBP, FMM)
    tracer_dirs = [d for d in input_base_dir.iterdir() if d.is_dir()]

    if not tracer_dirs:
        print(f"No subdirectories found in {input_base_dir}")
        return

    for t_dir in sorted(tracer_dirs):
        cohort_name = t_dir.name.upper()
        out_cohort_dir = output_base_dir / t_dir.name
        out_cohort_dir.mkdir(parents=True, exist_ok=True)

        print(f"\n==================================================")
        print(f"Processing Cohort / Directory: {t_dir.name}")
        print(f"Destination: {out_cohort_dir}")
        print(f"==================================================")

        nii_files = sorted(list(t_dir.glob("*.nii*")))
        if not nii_files:
            print(f"  No NIfTI files found in {t_dir.name}")
            continue

        for nii_file in nii_files:
            filename = nii_file.name
            fname_upper = filename.upper()

            # Determine output base name (e.g. ADavg_NAV_2_MNI -> ADavg_NAVcl_2_MNI)
            # or (ADavg_PIB_2_MNI -> ADavg_PIBcl_2_MNI)
            if "_2_MNI" in filename:
                out_base_name = filename.replace("_2_MNI", "cl_2_MNI").replace(".nii.gz", "").replace(".nii", "")
            else:
                out_base_name = nii_file.stem.replace(".nii", "") + "_cl"

            out_prefix = out_cohort_dir / out_base_name

            # Route to PiB or Fluorinated converter
            if "PIB" in fname_upper:
                print(f"\n[PIB] Processing: {filename}")
                convert_PiB_SUVR_to_CL(
                    suvr_map=nii_file,
                    output_prefix=out_prefix,
                    calibration_dir=equations_voxelwise_dir,
                )
            else:
                # Identify tracer from cohort folder name or filename
                tracer = cohort_name
                print(f"\n[{tracer}] Processing: {filename}")
                convert_SUVR_to_CL(
                    suvr_map=nii_file,
                    tracer=tracer,
                    output_prefix=out_prefix,
                    calibration_dir=equations_voxelwise_dir,
                )

    print("\n=================================================================")
    print("All voxel-wise conversions completed successfully.")
    print("=================================================================")


if __name__ == "__main__":
    REPO_ROOT = Path(__file__).resolve().parent.parent
    INPUT_DIR = REPO_ROOT / "examples" / "Voxelwise" / "InputMaps"
    OUTPUT_DIR = REPO_ROOT / "examples" / "Voxelwise" / "OutputMaps"
    EQUATIONS_VOXELWISE = REPO_ROOT / "equations" / "Voxelwise"

    run_voxelwise_batch_by_folder(
        input_base_dir=INPUT_DIR,
        output_base_dir=OUTPUT_DIR,
        equations_voxelwise_dir=EQUATIONS_VOXELWISE,
    )