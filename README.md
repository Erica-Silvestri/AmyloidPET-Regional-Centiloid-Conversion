Markdown# AmyloidPET-Centiloid-Conversion

[![License: CC BY-NC-ND 4.0](https://img.shields.io/badge/License-CC_BY--NC--ND_4.0-lightgrey.svg)](https://creativecommons.org/licenses/by-nc-nd/4.0/)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

A standardized toolset and calibration suite for converting amyloid PET Standardized Uptake Value Ratios (SUVR) to Centiloid (CL) units across regional tabular datasets and voxel-wise 3D/4D NIfTI maps.

Supports 18F-fluorinated tracers (**Florbetaben [FBB]**, **Florbetapir [FBP]**, **Flutemetamol [FMM]**, **NAV4694 [NAV]**) and standard **11C-PiB**.

---

## Directory Structure

```text
AmyloidPET-Centiloid-Conversion/
├── equations/                                 # Calibration tables and reference assets
│   ├── Regional/                              # Regional tabular calibration equations
│   ├── Voxelwise/                             # Voxel-wise calibration maps
│   └── Global/                                # Global slope and intercept reference parameters
├── examples/                                  # Example cohorts and validation runs
│   ├── Regional/                              # Tabular input and output CSVs
│   └── Voxelwise/                             # 3D/4D NIfTI input and output maps
├── pet_conversion/                            # Core Python package modules
├── scripts/                                   # Batch runners and validation tests
├── .gitignore
├── LICENSE
├── pyproject.toml
├── README.md
└── requirements.txt
InstallationClone the repository and install required dependencies:Bashgit clone [https://github.com/](https://github.com/)<your-username>/AmyloidPET-Centiloid-Conversion.git
cd AmyloidPET-Centiloid-Conversion
pip install -r requirements.txt
To install the package in editable development mode:Bashpip install -e .
Conversion Equations1. Regional Conversions (Tabular)Direct 18F-SUVR to Centiloids: Applies tracer-specific linear models per region.18F-SUVR to PiB-equivalent SUVR: Calibrates fluorinated tracer uptake to PiB SUVR space.PiB SUVR to Centiloids: Linear scaling using regional PiB slope and intercept tables.2. Voxel-wise Conversions (NIfTI)Fluorinated Tracers (FBB, FBP, FMM, NAV):$$\text{CL} = \left(\frac{\text{gradientPiBGlobal}}{\text{gradient}_{\text{tracer}}}\right) \times \text{SUVR} + \text{interceptCL\_local}$$gradientPiBGlobal is extracted from equations/Global/global_equations.csv.gradient_tracer is loaded from equations/Voxelwise/gradients.txt.interceptCL_local is the tracer-specific 3D intercept map (<TRACER>_regionalInterceptCL_brain.nii.gz).11C-PiB:$$\text{CL} = \text{gradientPiBGlobal} \times \text{PiB\_SUVR} + \text{PiB\_regionalInterceptCL}$$PiB_regionalInterceptCL.nii.gz is located in equations/Voxelwise/PiB/.All voxel-wise conversions are automatically masked with equations/Voxelwise/brain_mask.nii.gz.Usage Examples1. Regional Tabular Conversion (Python API)Pythonfrom pet_conversion.regional_fluorinate_to_cl import convert_SUVR_to_CL_withRegionalFormula
from pet_conversion.regional_pib_to_cl import convert_PiBSUVR_to_CL_withRegionalFormula

# Convert Fluorinated table directly to Centiloids
convert_SUVR_to_CL_withRegionalFormula(
    SUVRtab_input="examples/Regional/InputTables/FBB-SUVRSFlu-PETREG-standard.csv",
    output_fp="examples/Regional/OutTables/FBB-CLFlu-PETREG-standard_tool.csv",
    drop_unconverted_rois=True
)

# Convert PiB table to Centiloids
convert_PiBSUVR_to_CL_withRegionalFormula(
    SUVRtab_input="examples/Regional/InputTables/FBB-SUVRSPiB-PETREG-standard.csv",
    output_fp="examples/Regional/OutTables/FBB-CLPiB-PETREG-standard_tool.csv",
    drop_unconverted_rois=True
)
2. Voxel-wise NIfTI Conversion (CLI)Fluorinated Tracers:Bashpython -m pet_conversion.voxelwise_suvr_to_cl \
    -i /path/to/ADavg_NAV_2_MNI.nii.gz \
    -t NAV \
    -o /path/to/output/ADavg_NAVcl_2_MNI
11C-PiB:Bashpython -m pet_conversion.voxelwise_pib_to_cl \
    -i /path/to/ADavg_PIB_2_MNI.nii.gz \
    -o /path/to/output/ADavg_PIBcl_2_MNI
Running Batch ValidationRun the provided validation scripts to test conversions across all example cohorts:Bash# Test all regional tabular conversions
python scripts/batch_run_regional.py

# Test all voxel-wise conversions
python scripts/batch_run_voxelwise.py
CitationIf you use this repository or these calibration equations in your research, please cite:Code snippet@article{CentiloidConversion2026,
  title   = {Regional and Voxel-wise SUVR-to-Centiloid Calibration for Amyloid PET Tracers},
  author  = {[Author List]},
  journal = {[Journal Name]},
  year    = {2026},
  doi     = {[Insert DOI]}
}
LicenseThis project and its calibration assets are licensed under the Creative Commons Attribution-NonCommercial-NoDerivatives 4.0 International (CC BY-NC-ND 4.0) license.See LICENSE for full details.