#!/usr/bin/env python3
"""Voxel-wise PiB SUVR to Centiloid (CL) conversion.

Conversion formula:
    CL = gradientPiBGlobal * PiB_SUVR + PiB_regionalInterceptCL
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


def convert_PiB_SUVR_to_CL(
    suvr_map: Union[str, Path],
    output_prefix: Union[str, Path],
    calibration_dir: Optional[Union[str, Path]] = None,
) -> Path:
    """Converts a PiB SUVR NIfTI map (3D volume or 4D series) to Centiloid space.

    Parameters
    ----------
    suvr_map : str or Path
        Path to input PiB SUVR NIfTI file (.nii or .nii.gz).
    output_prefix : str or Path
        Directory path + base filename prefix for the output map.
    calibration_dir : str or Path, optional
        Path to equations/Voxelwise directory. Defaults to package internal path.

    Returns
    -------
    Path
        Path to the saved Centiloid NIfTI volume (*_cl.nii.gz).
    """
    suvr_path = Path(suvr_map)
    calib_voxelwise = (
        Path(calibration_dir) if calibration_dir is not None else DEFAULT_VOXELWISE_DIR
    )

    global_dir = (
        (calib_voxelwise.parent / "Global")
        if (calib_voxelwise.parent / "Global").exists()
        else DEFAULT_GLOBAL_DIR
    )

    gradient_pib_file = global_dir / "global_equations.csv"
    brain_mask_file = calib_voxelwise / "brain_mask.nii.gz"
    intercept_file = calib_voxelwise / "PiB" / "PiB_regionalInterceptCL.nii.gz"

    if not suvr_path.is_file():
        raise FileNotFoundError(f"Input PiB SUVR map not found: {suvr_path.resolve()}")
    if not brain_mask_file.is_file():
        raise FileNotFoundError(f"Brain mask file not found: {brain_mask_file.resolve()}")
    if not intercept_file.is_file():
        raise FileNotFoundError(f"PiB intercept file not found: {intercept_file.resolve()}")

    # Setup output path
    prefix_path = Path(output_prefix)
    prefix_path.parent.mkdir(parents=True, exist_ok=True)
    output_cl_map = prefix_path.with_name(f"{prefix_path.name}_cl.nii.gz")

    # Read global PiB gradient from global_equations.csv
    gradient_pib_global = _read_pib_global_gradient(gradient_pib_file)

    print("Converting PiB SUVR to Centiloid (Voxel-wise)...")
    print(f"  Input SUVR map:         {suvr_path}")
    print(f"  Global PiB cl_gradient: {gradient_pib_global} (from {gradient_pib_file.name})")
    print(f"  Voxel-wise Intercept:   {intercept_file}")
    print(f"  Brain mask file:        {brain_mask_file}")
    print(f"  Output CL map:          {output_cl_map}")

    # Load NIfTI volumes
    suvr_nii = nib.load(suvr_path)
    intercept_nii = nib.load(intercept_file)
    mask_nii = nib.load(brain_mask_file)

    suvr_data = suvr_nii.get_fdata(dtype=np.float32)
    intercept_data = intercept_nii.get_fdata(dtype=np.float32)
    mask_data = mask_nii.get_fdata(dtype=np.float32)

    # Conversion: handles single 3D volumes or 4D time/subject series
    if suvr_data.ndim == 4 and intercept_data.ndim == 3:
        cl_data = gradient_pib_global * suvr_data + intercept_data[..., np.newaxis]
        cl_data[mask_data == 0, :] = 0.0
    else:
        cl_data = gradient_pib_global * suvr_data + intercept_data
        cl_data[mask_data == 0] = 0.0

    # Save output NIfTI
    cl_nii = nib.Nifti1Image(cl_data.astype(np.float32), suvr_nii.affine, suvr_nii.header)
    cl_nii.set_data_dtype(np.float32)
    nib.save(cl_nii, output_cl_map)

    print(f"SUCCESS: Masked PiB CL map created: {output_cl_map}")
    return output_cl_map


def _parse_args():
    parser = argparse.ArgumentParser(
        description="Convert a PiB SUVR map to Centiloid space using voxel-wise calibration equations."
    )
    parser.add_argument(
        "-i", "--input", required=True, dest="suvr_map", help="Path to input PiB SUVR map (NIfTI file)"
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
    convert_PiB_SUVR_to_CL(
        suvr_map=args.suvr_map,
        output_prefix=args.output_prefix,
        calibration_dir=args.calibration_dir,
    )