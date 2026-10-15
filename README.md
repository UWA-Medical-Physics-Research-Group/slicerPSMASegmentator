# PSMASegmentator
3D Slicer extension implementing the PSMASegmentator model, a tool for the automatic segmentation of PSMA PET/CT images using deep learning. This extension will automatically create a segmentation file using the PSMASegmentator model.

The segmentation model uses the <u>nUNetv2 framework<u>, along with the DKFZ LesionTracer team's winning <u>autoPET-III methodology<u>. The training dataset is across multiple institutions and scanner types, with 597 patients from the <u>autoPET-III dataset<u> and 438 from Western Australian institutions, for a total of 1035 patients.

It supports both DICOM and NIfTI inputs and automatically handles pre-processing, inference, and post-processing. This includes lesion classification and biomarker extraction, utilizing TotalSegmentator and a complimentary liver metastases classifier model.

NB: This software is intended for research purposes only, not clinical diagnosis or treatment, and comes with absolutely no warranty.

![Screenshot displaying the PSMASegmentator GUI and resulting segmentations](https://github.com/UWA-Medical-Physics-Research-Group/slicerPSMASegmentator/blob/main/Segments_Screenshot.png)

## Manual Installation
#### (To be removed once PSMASegmentator is available in 3D Slicer Extension manager)
For manually installing this Extension, download or clone the repository to your local device. 

Open 3D Slicer and in the modules drop-down navigate to Developer Tools -> Extension Wizard.

From Extension Wizard, click Select Extension and navigate to the folder you cloned the repository to.

A popup will appear with the text "The following module canbe loaded. Would you like to load it now?

Tick the boxes for the PSMASegmentator module and 'Add selected module to "Additional module paths"' and hit OK

The file tree for the folder should then appear in the Extension Wizard GUI.

Restart Slicer and the module should then become available int he modules header under Segmentation -> PSMASegmentator

## Usage

- Start 3D Slicer
- Go to the `Add Data` icon and load two volumes, a `CT image` and a `PET image`
- Go to `PSMASegmentator` module
- Select `Input CT` -> `<your CT volume>`
- Select `Input PET` -> `<your PET volume>`
- Select any desired options to modify the segmentation process (or leave the values as default)
- Click `Apply`
  - When this module is used the first time:
    - It needs to download and install PyTorch and TotalSegmentator, and PSMASegmentator Python packages which can take some time. (~5 minutes)
  - Expected computation time:
    - With CUDA-capable GPU: 20-30 seconds in fast mode, 40-50 seconds in full-resolution mode.
    - Without GPU: 10-15 minutes in fast mode, up to an hour in full-resolution mode.
- The segmentation will automatically be added to the Slicer display and the name of the file can be found in the `Output Segmentation` field
- If you'd like to save the generated segmentation to your computer, go to the `Save Data` icon and select the file name of the segmentation
    - You can also select the file location in your device to save the file to by selecting `Change Directory for selected files` before hitting `Save`

## Options
#### The following options are available in the PSMASegmentator GUI to adjust the function of the program

- `SUV Threshold`: Apply an SUV threshold to the lesion segmentation output.
- `Processing device` : Select which device to use when processing the segmentations
    - `CPU`: use your device's CPU to process the segmentation
    - `CUDA`: use your device's Graphics Card to process the segmentation. Only available with NVIDIA CUDA capable devices
    - `CUDA - custom`: select the specific GPU Index when using CUDA processing
- `Expand Segmentations`: Expand output segmentations during post-processing. Shown to improve voxel-level DSC, although may introduce segmentation artefacts. 
- `Verbose`: Enable detailed logging and progress messages. (This wil require the console logs to be visible in your Slicer window)
- `Fast`: Use fast mode for inference. This uses the Fast (lightweight) version of PSMASegmentator, disables Test-Time Augmentation (TTA), and uses the --fast flag in TotalSegmentator for faster organ segmentation generation. Note that only the weights for the Fast model are downloaded/accessed from the given GitHub release when this option is selected. Highly recommended for non-GPU accelerated inference

## License
This tool is released under the GPL-3.0 License. See the LICENSE file for more details.

## Citation
If you use PSMASegmentator, please cite the software as:

> Noble, J., Kendrick, J., et al. *PSMASegmentator: Open-source, AI-based software tool for automatic segmentation and biomarker extraction from PSMA PET/CT* GitHub repository: https://github.com/UWA-Medical-Physics-Research-Group/PSMASegmentator




