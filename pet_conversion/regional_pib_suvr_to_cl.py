from pathlib import Path
from typing import List, Optional, Union
import numpy as np
import pandas as pd


def _clean_roi_name(roi: str) -> str:
    """Standardizes ROI naming convention to match equation table IDs."""
    if roi.startswith("LR_"):
        return roi.replace("LR_", "lh_", 1)
    return (
        roi.replace("Left_", "")
        .replace("Right_", "")
        .replace("Left-", "")
        .replace("Right-", "")
        .replace("_Proper", "")
        .replace("-Proper", "")
    )


def _get_default_equations_path() -> Path:
    """Returns the equation path. """
    try:
        base_dir = Path(__file__).resolve().parent.parent
    except NameError:
        base_dir = Path.cwd()
    return base_dir / "equations" / "Regional"


def _load_tabular_file(file_path: Union[str, Path]) -> pd.DataFrame:
    """Loads CSV, TSV, or Excel tables into a DataFrame."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path.resolve()}")

    ext = path.suffix.lower()
    if ext in [".xlsx", ".xls"]:
        return pd.read_excel(path)
    elif ext == ".tsv":
        return pd.read_csv(path, sep="\t")
    else:
        return pd.read_csv(path, sep=None, engine="python")


def convert_PiBSUVR_to_CL_withRegionalFormula(
    SUVRtab_input: Union[str, Path, pd.DataFrame],
    ROIlist: Optional[List[str]] = None,
    conversionTab_fp: Optional[Union[str, Path]] = None,
    output_fp: Optional[Union[str, Path]] = None,
    drop_unconverted_rois: bool = True,
) -> pd.DataFrame:
    """Convert PiB SUVR values to Centiloids.

    Parameters
    ----------
    SUVRtab_input : str, Path, or pd.DataFrame
        Path to the *SUVRSPiB* table or pre-loaded DataFrame.
    ROIlist : list of str, optional
        Explicit ROIs to convert. If None, automatically detects all matching ROIs.
    conversionTab_fp : str or Path, optional
        Path to directory containing 'PiBsuvr-to-CL.csv' (or 'equations/').
    output_fp : str or Path, optional
        Path where the converted Centiloid CSV/Excel table will be saved.
    drop_unconverted_rois : bool, default True
        If True, drops ROIs that cannot be converted to Centiloid from the output table,
        keeping only metadata and converted Centiloid columns.
    """
    # 1. Load input SUVR data
    if isinstance(SUVRtab_input, (str, Path)):
        suvr_df = _load_tabular_file(SUVRtab_input)
    elif isinstance(SUVRtab_input, pd.DataFrame):
        suvr_df = SUVRtab_input.copy()
    else:
        raise TypeError(
            "SUVRtab_input must be a file path (str or Path) or a pandas DataFrame."
        )

    # 2. Locate and load the PiB to Centiloid equations table
    conversion_dir = (
        Path(conversionTab_fp)
        if conversionTab_fp is not None
        else _get_default_equations_path()
    )

    file_path = conversion_dir / "PiBsuvr-to-CL.csv"
    if not file_path.exists():
        # Fallback search for any table matching PiBsuvr*to*CL
        candidates = list(conversion_dir.glob("*PiB*to*CL*")) + list(
            conversion_dir.glob("*pib*to*cl*")
        )
        if candidates:
            file_path = candidates[0]
        else:
            raise FileNotFoundError(
                f"Could not find PiB-to-CL conversion table in: {conversion_dir.resolve()}"
            )

    if file_path.suffix.lower() in [".xlsx", ".xls"]:
        df_conv = pd.read_excel(file_path)
    else:
        df_conv = pd.read_csv(file_path, sep=None, engine="python")

    # Standardize column names and IDs in conversion table
    id_col = "ID" if "ID" in df_conv.columns else "ROI"
    df_conv[id_col] = (
        df_conv[id_col]
        .astype(str)
        .str.replace("-", "_", regex=False)
        .str.replace("occipitial", "occipital", regex=False)
        .str.lower()
    )

    # Detect slope and intercept column names
    grad_col = "cl_gradient" if "cl_gradient" in df_conv.columns else "gradient"
    inter_col = "cl_intercept" if "cl_intercept" in df_conv.columns else "intercept"

    param_dict = {
        row[id_col]: (float(row[grad_col]), float(row[inter_col]))
        for _, row in df_conv.iterrows()
    }

    # Metadata columns to preserve
    meta_cols = [
        "patid",
        "visitid",
        "visitidpet",
        "group",
        "tracer",
        "diagnosis",
        "age",
        "sex",
    ]
    present_meta = [c for c in meta_cols if c in suvr_df.columns]

    # 3. Determine ROIs that can actually be converted
    available_rois = [
        col
        for col in suvr_df.columns
        if col not in present_meta and _clean_roi_name(col).lower() in param_dict
    ]

    if ROIlist is not None:
        target_rois = [
            r
            for r in ROIlist
            if r in suvr_df.columns and _clean_roi_name(r).lower() in param_dict
        ]
    else:
        target_rois = available_rois

    # 4. Perform Centiloid conversion
    cl_study = suvr_df.copy()
    converted_rois = []

    for roi in target_rois:
        clean_name = _clean_roi_name(roi).lower()
        if clean_name in param_dict:
            slope, intercept = param_dict[clean_name]
            # Vectorized CL calculation: CL = slope * SUVR + intercept
            cl_study[roi] = slope * pd.to_numeric(cl_study[roi], errors="coerce") + intercept
            converted_rois.append(roi)

    # 5. Drop unconverted ROIs if requested
    if drop_unconverted_rois:
        # Keep metadata columns + converted ROI columns
        cols_to_keep = [
            col
            for col in suvr_df.columns
            if col in present_meta or col in converted_rois
        ]
        cl_study = cl_study[cols_to_keep]

    # 6. Save results to output_fp
    if output_fp is not None:
        save_path = Path(output_fp)
        save_path.parent.mkdir(parents=True, exist_ok=True)

        ext = save_path.suffix.lower()
        if ext in [".xlsx", ".xls"]:
            cl_study.to_excel(save_path, index=False)
        elif ext == ".tsv":
            cl_study.to_csv(save_path, sep="\t", index=False)
        else:
            if ext != ".csv":
                save_path = save_path.with_suffix(".csv")
            cl_study.to_csv(save_path, index=False)

        print(f"Centiloid table saved ({len(converted_rois)} ROIs converted) to: {save_path.resolve()}")

    return cl_study