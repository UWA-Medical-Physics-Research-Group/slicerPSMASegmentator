# PSMASegmentator
3D Slicer extension implementing the PSMASegmentator model, a tool for the automatic segmentation of PSMA PET/CT images using deep learning. This extension will automatically create a segmentation file using the PSMASegmentator model.

![Screenshot displaying the PSMASegmentator GUI and resulting segmentations](https://github.com/UWA-Medical-Physics-Research-Group/slicerPSMASegmentator/blob/main/Segments_Screenshot.png)

## Manual Installation
#### (To be removed once PSMASegmentator is available in 3D Slicer Extension manager)
For manually installing this Extension, download or clone the repository to your local device. 

Open 3D Slicer and in the modules drop-down navigate to Developer Tools -> Extension Wizard.

From Extension Wizard, click Select Extension and navigate to the folder you cloned the repository to.

A popup will appear witht he text "The following module canbe loaded. Would you like to load it now?

Tick the boxes for the PSMASegmentator module and 'Add selected module to "Additional module paths"' and hit OK

The file tree for the folder should then appear in the Extension Wizard GUI.

Restart Slicer and the module should then become available int he modules header under Segmentation -> PSMASegmentator

## License
This tool is released under the GPL-3.0 License. See the LICENSE file for more details.

## Citation
If you use PSMASegmentator, please cite the software as:

> Noble, J., Kendrick, J., et al. *PSMASegmentator: Open-source, AI-based software tool for automatic segmentation and biomarker extraction from PSMA PET/CT* GitHub repository: https://github.com/UWA-Medical-Physics-Research-Group/PSMASegmentator




