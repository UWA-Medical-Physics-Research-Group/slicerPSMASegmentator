cmake_minimum_required(VERSION 3.20.6...3.22.6 FATAL_ERROR)

project(PSMASegmentator)

#-----------------------------------------------------------------------------
# Extension meta-information
set(EXTENSION_HOMEPAGE "https://github.com/UWA-Medical-Physics-Research-Group/slicerPSMASegmentator.git")
set(EXTENSION_CATEGORY "Segmentation")
set(EXTENSION_CONTRIBUTORS "Logan Frost (University of Western Australia), Jake Kendrick (University of Western Australia), Joel Noble (University of Western Australia)")
set(EXTENSION_DESCRIPTION "3D Slicer extension implementing the PSMASegmentator model, a tool for the automatic segmentation of PSMA PET/CT images using deep learning. This extension will automatically create a segmentation file using the PSMASegmentator model.")
set(EXTENSION_ICONURL "https://www.example.com/Slicer/Extensions/PSMA_PIP_Test.png")
set(EXTENSION_SCREENSHOTURLS "https://raw.githubusercontent.com/UWA-Medical-Physics-Research-Group/slicerPSMASegmentator/main/Segments_Screenshot.png")
set(EXTENSION_DEPENDS "PyTorch NNUNet TotalSegmentator") # Specified as a list or "NA" if no dependencies

#-----------------------------------------------------------------------------
# Extension dependencies
find_package(Slicer REQUIRED)
include(${Slicer_USE_FILE})

#-----------------------------------------------------------------------------
# Extension modules
add_subdirectory(PSMASegmentator)
## NEXT_MODULE

#-----------------------------------------------------------------------------
include(${Slicer_EXTENSION_GENERATE_CONFIG})
include(${Slicer_EXTENSION_CPACK})
