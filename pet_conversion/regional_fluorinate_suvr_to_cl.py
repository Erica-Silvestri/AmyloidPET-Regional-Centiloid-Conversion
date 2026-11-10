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


def convert_SUVR_to_CL_withRegionalFormula(
    SUVRtab_input: Union[str, Path, pd.DataFrame],
    ROIlist: Optional[List[str]] = None,
    conversionTab_fp: Optional[Union[str, Path]] = None,
    output_fp: Optional[Union[str, Path]] = None,
    drop_unconverted_rois: bool = True,
) -> pd.DataFrame:
    """Convert regional fluorinated 18F SUVR values to Centiloids using tracer-specific

    equations ({tracer}suvr-to-pib_-to-CL.csv).
    """
    # 1. Load input table
    if isinstance(SUVRtab_input, (str, Path)):
        suvr_df = _load_tabular_file(SUVRtab_input)
    elif isinstance(SUVRtab_input, pd.DataFrame):
        suvr_df = SUVRtab_input.copy()
    else:
        raise TypeError(
            "SUVRtab_input must be a file path (str or Path) or a pandas DataFrame."
        )

    # 2. Resolve equations directory and load tables
    conversion_dir = (
        Path(conversionTab_fp)
        if conversionTab_fp is not None
        else _get_default_equations_path()
    )

    tracers_list = ["FBP", "FBB", "FMM", "NAV"]
    conversion_tabs = {}

    for tracer in tracers_list:
        file_path = conversion_dir / f"{tracer}suvr-to-pib_-to-CL.csv"

        if file_path.exists():
            df_conv = _load_tabular_file(file_path)

            id_col = "ROI" if "ROI" in df_conv.columns else "ID"
            df_conv[id_col] = (
                df_conv[id_col]
                .astype(str)
                .str.replace("-", "_", regex=False)
                .str.replace("occipitial", "occipital", regex=False)
                .str.lower()
            )

            param_dict = {}
            for _, row in df_conv.iterrows():
                param_dict[row[id_col]] = (
                    float(row["cl_gradient"]),
                    float(row["cl_intercept"]),
                )
            conversion_tabs[tracer.upper()] = param_dict

    # 3. Identify metadata columns
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

    # Collect union of all ROIs present across loaded tracer tables
    all_known_rois = set()
    for tab in conversion_tabs.values():
        all_known_rois.update(tab.keys())

    if ROIlist is None:
        target_rois = [
            c
            for c in suvr_df.columns
            if c not in present_meta and _clean_roi_name(c).lower() in all_known_rois
        ]
    else:
        target_rois = [
            r
            for r in ROIlist
            if r in suvr_df.columns and _clean_roi_name(r).lower() in all_known_rois
        ]

    # 4. Perform Centiloid conversion
    cl_study = suvr_df.copy()
    actually_converted_rois = set()

    for idx, row in cl_study.iterrows():
        current_tracer = (
            str(row["tracer"]).strip().upper() if pd.notna(row.get("tracer")) else ""
        )

        matched_tab = None
        for tracer_key in conversion_tabs:
            if tracer_key in current_tracer:
                matched_tab = conversion_tabs[tracer_key]
                break

        if matched_tab is not None:
            for roi in target_rois:
                clean_name = _clean_roi_name(roi).lower()
                if clean_name in matched_tab:
                    slope, intercept = matched_tab[clean_name]
                    suvr_val = row[roi]
                    cl_study.at[idx, roi] = (
                        slope * float(suvr_val) + intercept
                        if pd.notna(suvr_val)
                        else np.nan
                    )
                    actually_converted_rois.add(roi)
                else:
                    cl_study.at[idx, roi] = np.nan
        else:
            for roi in target_rois:
                cl_study.at[idx, roi] = np.nan

    # 5. Drop unconverted ROIs (keeps only metadata + converted regions)
    if drop_unconverted_rois:
        cols_to_keep = [
            col
            for col in suvr_df.columns
            if col in present_meta or col in actually_converted_rois
        ]
        cl_study = cl_study[cols_to_keep]

    # 6. Save results
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

        print(
            f"Centiloid table saved ({len(actually_converted_rois)} ROIs converted) to: {save_path.resolve()}"
        )

    return cl_study