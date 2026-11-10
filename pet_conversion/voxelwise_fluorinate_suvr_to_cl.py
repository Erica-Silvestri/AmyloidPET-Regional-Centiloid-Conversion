#!/usr/bin/env python3
"""Voxel-wise SUVR to Centiloid (CL) conversion.

Calculates Centiloids via:
    CL = (gradientPiBGlobal / tracer_gradient) * SUVR + interceptCL_local
masked by brain_mask.nii.gz.
"""

import argparse
from pathlib import Path
from typing import Optional, Union
import nibabel as nib
import numpy as np
import pandas as pd

DEFAULT_EQUATIONS_DIR = Path(__file__).resolve().parent.parent / "equations"
DEFAULT_VOXELWISE_DIR = DEFAULT_EQUATIONS_DIR / "Voxelwise"
DEFAULT_GLOBAL_DIR = DEFAULT_EQUATIONS_DIR / "Global"


def _read_pib_global_gradient(pib_file: Path) -> float:
    """Extracts cl_gradient for Tracer == 'PiB' from global_equations.csv."""
    if not pib_file.is_file():
        raise FileNotFoundError(f"Global equations table not found: {pib_file.resolve()}")

    df = pd.read_csv(pib_file).dropna(how="all", axis=0).dropna(how="all", axis=1)
    df.columns = df.columns.str.strip()

    pib_mask = df["Tracer"].astype(str).str.strip().str.upper() == "PIB"
    pib_row = df[pib_mask]

    if pib_row.empty:
        raise ValueError(f"Could not find entry for Tracer == 'PiB' in {pib_file.name}")

    return float(pib_row["cl_gradient"].iloc[0])


def _read_tracer_gradient(gradient_file: Path, tracer: str) -> float:
    """Extracts tracer GAAIN calibration slope from Voxelwise/gradients.txt."""
    if not gradient_file.is_file():
        raise FileNotFoundError(f"Gradient file not found: {gradient_file.resolve()}")

    tracer_clean = tracer.strip().upper()
    with open(gradient_file, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if ":" in line:
                key, val = line.split(":", 1)
                if key.strip().upper() == tracer_clean:
                    return float(val.strip())

    raise ValueError(f"Could not find gradient for tracer: {tracer} in {gradient_file.name}")


def convert_SUVR_to_CL(
    suvr_map: Union[str, Path],
    tracer: str,
    output_prefix: Union[str, Path],
    calibration_dir: Optional[Union[str, Path]] = None,
) -> Path:
    """Converts a tracer SUVR map to Centiloid space using voxel-wise calibration.

    Parameters
    ----------
    suvr_map : str or Path
        Path to input SUVR NIfTI file (.nii or .nii.gz).
    tracer : str
        Tracer identifier (e.g., 'FBB', 'FBP', 'FMM', 'NAV').
    output_prefix : str or Path
        Output directory path + base filename prefix.
    calibration_dir : str or Path, optional
        Path to equations/Voxelwise folder. Defaults to package internal path.
    """
    suvr_path = Path(suvr_map)
    tracer_clean = tracer.strip().upper()
    calib_voxelwise = (
        Path(calibration_dir) if calibration_dir is not None else DEFAULT_VOXELWISE_DIR
    )

    # Global equations directory (for global PiB cl_gradient)
    global_dir = (
        (calib_voxelwise.parent / "Global")
        if (calib_voxelwise.parent / "Global").exists()
        else DEFAULT_GLOBAL_DIR
    )

    gradient_pib_file = global_dir / "global_equations.csv"

    # Voxelwise directory assets
    gradient_tracer_file = calib_voxelwise / "gradients.txt"
    brain_mask_file = calib_voxelwise / "brain_mask.nii.gz"
    tracer_dir = calib_voxelwise / tracer_clean
    intercept_file = tracer_dir / f"{tracer_clean}_regionalInterceptCL_brain.nii.gz"

    # Validation
    if not suvr_path.is_file():
        raise FileNotFoundError(f"Input SUVR map not found: {suvr_path.resolve()}")
    if not intercept_file.is_file():
        raise FileNotFoundError(f"Intercept file not found: {intercept_file.resolve()}")
    if not brain_mask_file.is_file():
        raise FileNotFoundError(f"Brain mask file not found: {brain_mask_file.resolve()}")

    # Setup output path
    prefix_path = Path(output_prefix)
    prefix_path.parent.mkdir(parents=True, exist_ok=True)
    output_cl_map = prefix_path.with_name(f"{prefix_path.name}_cl.nii.gz")

    # Read calibration parameters
    gradient_pib_global = _read_pib_global_gradient(gradient_pib_file)
    tracer_gradient = _read_tracer_gradient(gradient_tracer_file, tracer_clean)

    print(f"Converting {tracer_clean} SUVR to Centiloid...")
    print(f"  Input SUVR map:          {suvr_path}")
    print(f"  Tracer:                  {tracer_clean}")
    print(f"  GAAIN Gradient:          {tracer_gradient}  (from {gradient_tracer_file.name})")
    print(f"  Global PiB cl_gradient:  {gradient_pib_global}  (from {gradient_pib_file.name})")
    print(f"  Intercept file:          {intercept_file}")
    print(f"  Brain mask file:         {brain_mask_file}")
    print(f"  Output CL map:           {output_cl_map}")

    # Load NIfTIs
    suvr_nii = nib.load(suvr_path)
    intercept_nii = nib.load(intercept_file)
    mask_nii = nib.load(brain_mask_file)

    suvr_data = suvr_nii.get_fdata(dtype=np.float32)
    intercept_data = intercept_nii.get_fdata(dtype=np.float32)
    mask_data = mask_nii.get_fdata(dtype=np.float32)

    # Conversion: CL = (gradientPiBGlobal / tracer_gradient) * SUVR + intercept
    slope_factor = gradient_pib_global / tracer_gradient
    cl_data = slope_factor * suvr_data + intercept_data

    # Apply brain mask (set background outside mask to 0.0)
    cl_data[mask_data == 0] = 0.0

    # Save output NIfTI
    cl_nii = nib.Nifti1Image(cl_data.astype(np.float32), suvr_nii.affine, suvr_nii.header)
    cl_nii.set_data_dtype(np.float32)
    nib.save(cl_nii, output_cl_map)

    print(f"SUCCESS: Masked CL map created: {output_cl_map}")
    return output_cl_map


def _parse_args():
    parser = argparse.ArgumentParser(
        description="Convert a tracer SUVR map to Centiloid space using voxel-wise calibration equations."
    )
    parser.add_argument(
        "-i", "--input", required=True, dest="suvr_map", help="Path to input SUVR map (NIfTI file)"
    )
    parser.add_argument(
        "-t", "--tracer", required=True, dest="tracer", help="Tracer identifier (e.g., FBB, FBP, FMM, NAV)"
    )
    parser.add_argument(
        "-o", "--output", required=True, dest="output_prefix", help="Output file prefix (directory path + base name)"
    )
    parser.add_argument(
        "-c", "--calibration", default=None, dest="calibration_dir", help="Path to equations/Voxelwise folder (optional)"
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    convert_SUVR_to_CL(
        suvr_map=args.suvr_map,
        tracer=args.tracer,
        output_prefix=args.output_prefix,
        calibration_dir=args.calibration_dir,
    )