import logging
import os
from typing import Annotated

import vtk

import slicer
from slicer.i18n import tr as _
from slicer.i18n import translate
from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin
from slicer.util import launchConsoleProcess
from slicer.parameterNodeWrapper import (
    parameterNodeWrapper,
    WithinRange,
)
import qt
from slicer import vtkMRMLScalarVolumeNode, vtkMRMLSegmentationNode


#
# PSMASegmentator
#


class PSMASegmentator(ScriptedLoadableModule):
    """Uses ScriptedLoadableModule base class, available at:
    https://github.com/Slicer/Slicer/blob/main/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = _("PSMA Segmentator")
        self.parent.categories = [translate("qSlicerAbstractCoreModule", "Segmentation")]
        self.parent.dependencies = []  # TODO: add here list of module names that this module requires
        self.parent.contributors = ["Logan Frost (University of Western Australia)", "Joel Noble (University of Western Australia)", "Jake Kendrick (University of Western Australia)"]
        # _() function marks text as translatable to other languages
        self.parent.helpText = _("""
3D Slicer extension for automatic segmentation of PSMA CT/PET scans using the PSMASegmentator nnU-net model. For more information see the <a href="https://github.com/Smiley260/SlicerPSMASegmentator">module documentation</a>.
""")
        # TODO: replace with organization, grant and thanks
        self.parent.acknowledgementText = _("""
This file was originally developed by Logan Frost, Masters student at the University of Western Australia, under the supervision of Jake Kendrick
and is an implementation of the PSMA Segmentator model developed by Joel Noble, University of Western Australia.
""")

        # Additional initialization step after application startup is complete
        slicer.app.connect("startupCompleted()", registerSampleData)


#
# Register sample data sets in Sample Data module
#


def registerSampleData():
    """Add data sets to Sample Data module."""
    # It is always recommended to provide sample data for users to make it easy to try the module,
    # but if no sample data is available then this method (and associated startupCompeted signal connection) can be removed.

    import SampleData

    iconsPath = os.path.join(os.path.dirname(__file__), "Resources/Icons")


#
# PSMASegmentatorParameterNode
#


@parameterNodeWrapper
class PSMASegmentatorParameterNode:
    """
    The parameters needed by module.

        inputSelectorOne: The CT scan volume
        inputSelectorTwo: the PET scan volume
        suvSlider: SUV threshold for the segmenattion (defaults to 0)
        defaultDeviceSelector: Selected if the device selection is to be made by the cli module. selected by default
        cpuSelector: Selected if the model should be run on the CPU
        cudaSelector: Selected if the model should be run using CUDA
        cudaCustomSelector: Selected if the model should be run using CUDA with a custom GPU index
        gpuIndexSelector: GPU Index for custom CUDA processing. defaults to 0
        expandBox: Togglable option for expanded segmentation results
        verboseBox: Togglable option for Verbose outputs
        fastBox: Togglable option for funn the fast version of the model
    """

    inputSelectorOne: vtkMRMLScalarVolumeNode
    inputSelectorTwo: vtkMRMLScalarVolumeNode
    suvSlider: Annotated[float, WithinRange(0, 5)] = 0
    defaultDeviceSelector: bool = True
    cpuSelector: bool = False
    cudaSelector: bool = False
    cudaCustomSelector: bool = False
    gpuIndexSelector: Annotated[int, WithinRange(0, 99)] = 0
    expandBox: bool = False
    verboseBox: bool = False
    fastBox: bool = True

    outputSegmentation: vtkMRMLSegmentationNode


#
# PSMASegmentatorWidget
#


class PSMASegmentatorWidget(ScriptedLoadableModuleWidget, VTKObservationMixin):
    """Uses ScriptedLoadableModuleWidget base class, available at:
    https://github.com/Slicer/Slicer/blob/main/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def __init__(self, parent=None) -> None:
        """Called when the user opens the module the first time and the widget is initialized."""
        ScriptedLoadableModuleWidget.__init__(self, parent)
        VTKObservationMixin.__init__(self)  # needed for parameter node observation
        self.logic = None
        self._parameterNode = None
        self._parameterNodeGuiTag = None

    def setup(self) -> None:
        """Called when the user opens the module the first time and the widget is initialized."""
        ScriptedLoadableModuleWidget.setup(self)

        # Load widget from .ui file (created by Qt Designer).
        # Additional widgets can be instantiated manually and added to self.layout.
        uiWidget = slicer.util.loadUI(self.resourcePath("UI/PSMASegmentator.ui"))
        self.layout.addWidget(uiWidget)
        self.ui = slicer.util.childWidgetVariables(uiWidget)

        # Set scene in MRML widgets. Make sure that in Qt designer the top-level qMRMLWidget's
        # "mrmlSceneChanged(vtkMRMLScene*)" signal in is connected to each MRML widget's.
        # "setMRMLScene(vtkMRMLScene*)" slot.
        uiWidget.setMRMLScene(slicer.mrmlScene)

        # Create logic class. Logic implements all computations that should be possible to run
        # in batch mode, without a graphical user interface.
        self.logic = PSMASegmentatorLogic()

        # Connections

        # These connections ensure that we update parameter node when scene is closed
        self.addObserver(slicer.mrmlScene, slicer.mrmlScene.StartCloseEvent, self.onSceneStartClose)
        self.addObserver(slicer.mrmlScene, slicer.mrmlScene.EndCloseEvent, self.onSceneEndClose)

        # Buttons
        self.ui.applyButton.connect("clicked(bool)", self.onApplyButton)

        # Make sure parameter node is initialized (needed for module reload)
        self.initializeParameterNode()

    def cleanup(self) -> None:
        """Called when the application closes and the module widget is destroyed."""
        self.removeObservers()

    def enter(self) -> None:
        """Called each time the user opens this module."""
        # Make sure parameter node exists and observed
        self.initializeParameterNode()

    def exit(self) -> None:
        """Called each time the user opens a different module."""
        # Do not react to parameter node changes (GUI will be updated when the user enters into the module)
        if self._parameterNode:
            self._parameterNode.disconnectGui(self._parameterNodeGuiTag)
            self._parameterNodeGuiTag = None
            self.removeObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self._checkCanApply)

    def onSceneStartClose(self, caller, event) -> None:
        """Called just before the scene is closed."""
        # Parameter node will be reset, do not use it anymore
        self.setParameterNode(None)

    def onSceneEndClose(self, caller, event) -> None:
        """Called just after the scene is closed."""
        # If this module is shown while the scene is closed then recreate a new parameter node immediately
        if self.parent.isEntered:
            self.initializeParameterNode()

    def initializeParameterNode(self) -> None:
        """Ensure parameter node exists and observed."""
        # Parameter node stores all user choices in parameter values, node selections, etc.
        # so that when the scene is saved and reloaded, these settings are restored.

        self.setParameterNode(self.logic.getParameterNode())

    def setParameterNode(self, inputParameterNode: PSMASegmentatorParameterNode | None) -> None:
        """
        Set and observe parameter node.
        Observation is needed because when the parameter node is changed then the GUI must be updated immediately.
        """

        if self._parameterNode:
            self._parameterNode.disconnectGui(self._parameterNodeGuiTag)
            self.removeObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self._checkCanApply)
        self._parameterNode = inputParameterNode
        if self._parameterNode:
            # Note: in the .ui file, a Qt dynamic property called "SlicerParameterName" is set on each
            # ui element that needs connection.
            self._parameterNodeGuiTag = self._parameterNode.connectGui(self.ui)
            self.addObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self._checkCanApply)
            self._checkCanApply()

    def _checkCanApply(self, caller=None, event=None) -> None:
        if self._parameterNode and self._parameterNode.inputSelectorOne and self._parameterNode.inputSelectorTwo:
            self.ui.applyButton.toolTip = _("Predict PSMA Segmentation")
            self.ui.applyButton.enabled = True
        else:
            self.ui.applyButton.toolTip = _("Select input and output volume nodes")
            self.ui.applyButton.enabled = False

    def onApplyButton(self) -> None:
        """Run processing when user clicks "Apply" button."""
        import qt
        import time

        #track whole extention duration
        startTime = time.time()

        # TODO: remove temp comments
        try:
            slicer.app.setOverrideCursor(qt.Qt.WaitCursor)
            self.logic.setupPythonRequirements()
            self.logic.log(_('Successfully installed PSMA Segmentator and required packages'))
            slicer.app.restoreOverrideCursor()
        except Exception as e:
            slicer.util.errorDisplay(_("Failed to install required packages.\n\n{exception}").format(exception=e))
            slicer.app.restoreOverrideCursor()
        
        with slicer.util.tryWithErrorDisplay(_("Failed to compute results."), waitCursor=True):
        # TODO pre-process inputs and process outputs
            #Compute output
            lesion_vals = [self.ui.Number_of_lesions, self.ui.TTV, self.ui.Tumour_SUVmean, self.ui.Tumour_SUVmax, self.ui.TLU, self.ui.TLQ, self.ui.Bone_mets, self.ui.Visceral_mets, self.ui.Liver_mets]
            self.logic.process(self.ui.inputSelectorOne.currentNode(), self.ui.inputSelectorTwo.currentNode(), self.ui.outputSegmentation, self.ui.suvSlider.value, self.ui.defaultDeviceSelector.checked,  self.ui.cpuSelector.checked, self.ui.cudaSelector.checked, self.ui.cudaCustomSelector.checked, self.ui.gpuIndexSelector.value, self.ui.expandBox.checked, self.ui.verboseBox.checked, self.ui.fastBox.checked, lesion_vals)
            
        
        stopTime = time.time()
        logging.info(f"Extension completed in {stopTime-startTime:.2f} seconds")


#
# PSMASegmentatorLogic
#


class InstallError(Exception):
    def __init__(self, message, restartRequired=False):
        # Call the base class constructor with the parameters it needs
        super().__init__(message)
        self.message = message
        self.restartRequired = restartRequired
    def __str__(self):
        return self.message

class PSMASegmentatorLogic(ScriptedLoadableModuleLogic):
    """
    Uses ScriptedLoadableModuleLogic base class, available at:
    https://github.com/Slicer/Slicer/blob/main/Base/Python/slicer/ScriptedLoadableModule.py
    """



    def __init__(self) -> None:
        """Called when the logic class is instantiated. Can be used for initializing member variables."""
        ScriptedLoadableModuleLogic.__init__(self)
        self.logCallback = None

    @staticmethod
    def executableName(name):
        return name + ".exe" if os.name == "nt" else name

    @staticmethod
    def executablePath():
        import sysconfig
        return os.path.join(sysconfig.get_path('scripts'), PSMASegmentatorLogic.executableName("psma_segmentator"))

    @staticmethod
    def getDownloadURL():
        return "git+https://github.com/UWA-Medical-Physics-Research-Group/PSMASegmentator@nnunet-repackage"

    def log(self, text):
        logging.info(text)
        if self.logCallback:
            self.logCallback(text)

    def logProcessOutput(self, proc, returnOutput=False):
        # Wait for the process to end and forward output to the log
        output = ""
        from subprocess import CalledProcessError
        killedAfterSaving = False
        while True:
            try:
                line = proc.stdout.readline()
                if not line:
                    break
                if returnOutput:
                    output += line
                self.log(line.rstrip())
            except UnicodeDecodeError:
                # Code page conversion happens because `universal_newlines=True` sets process output to text mode,
                # and it fails because probably system locale is not UTF8. We just ignore the error and discard the string,
                # as we only guarantee correct behavior if an UTF8 locale is used.
                pass

        proc.wait()
        retcode = proc.returncode
        if retcode != 0 and not killedAfterSaving:
            raise CalledProcessError(retcode, proc.args, output=proc.stdout, stderr=proc.stderr)
        return output if returnOutput else None

    def getParameterNode(self):
        return PSMASegmentatorParameterNode(super().getParameterNode())

    def setupPythonRequirements(self, upgrade=False):
        import importlib.metadata
        import importlib.util
        import packaging

        # PSMA Segmentator requires dicom2nifti
        # but latest dicom2nifti is broken on Python-3.9. We need to install an older version.
        # (dicom2nifti was recently updated to version 2.6. This version needs pydicom >= 3.0.0, which requires python >= 3.10)
        try:
            import dicom2nifti
        except ModuleNotFoundError as e:
            slicer.util.pip_install("dicom2nifti<=2.5.1")

        # These packages come preinstalled with Slicer and should remain unchanged
        packagesToSkip = [
            'SimpleITK',  # Slicer's SimpleITK uses a special IO class, which should not be replaced
            'torch',  # needs special installation using SlicerPyTorch
            'requests',  # PSMA Segmentator would want to force a specific version of requests, which would require a restart of Slicer and it is unnecessary
            'rt_utils',  # Only needed for RTSTRUCT export, which is not needed in Slicer; rt_utils depends on opencv-python which is hard to build
            'dicom2nifti', # We already installed a known working version, do not let PSMA Segmentator to upgrade to a newer version that may not work on Python-3.9
            'TotalSegmentator' #TotalSegmentator has a specific Slicer implementation
            ]

        # Ask for confirmation before installing PyTorch and TotalSegmentator
        confirmPackagesToInstall = []
    
        try:
            import PyTorchUtils
        except ModuleNotFoundError as e:
            raise InstallError("This module requires PyTorch extension. Install it from the Extensions Manager.")

        minimumTorchVersion = "2.1.2"  # match the requirements of PSMA Segmentator
        torchLogic = PyTorchUtils.PyTorchUtilsLogic()
        if not torchLogic.torchInstalled():
            confirmPackagesToInstall.append("PyTorch")

        try:
            import TotalSegmentator
        except ModuleNotFoundError as e:
            raise InstallError("This module requires TotalSegmentator extension. Install it from the Extensions Manager.")

        confirmPackagesToInstall.append("TotalSegmentator")

        if confirmPackagesToInstall:
            if not slicer.util.confirmOkCancelDisplay(
                _("The PSMA Segmentator module requires installation of additional Python packages. Installation needs network connection and may take several minutes. You may be asked to confirm this more than once. Click OK to proceed."),
                _("Confirm Python package installation"),
                detailedText=_("Python packages that will be installed: {package_list}").format(package_list=', '.join(confirmPackagesToInstall))
                ):
                raise InstallError("User cancelled.")

        
        # Install PyTorch
        if "PyTorch" in confirmPackagesToInstall:
            self.log(_('PyTorch Python package is required. Installing... (it may take several minutes)'))
            torch = torchLogic.installTorch(askConfirmation=False, torchVersionRequirement = f">={minimumTorchVersion}")
            if torch is None:
                raise InstallError("This module requires PyTorch extension. Install it from the Extensions Manager.")
        else:
            # torch is installed, check version
            from packaging import version
            if version.parse(torchLogic.torch.__version__) < version.parse(minimumTorchVersion):
                raise InstallError(f'PyTorch version {torchLogic.torch.__version__} is not compatible with this module.'
                                 + f' Minimum required version is {minimumTorchVersion}. You can use "PyTorch Util" module to install PyTorch'
                                 + f' with version requirement set to: >={minimumTorchVersion}')


        # Install TotalSegmentator
        if "TotalSegmentator" in confirmPackagesToInstall:
            self.log(_('TotalSegmentator Python package is required. Installing... (it may take several minutes)'))

            TotalSegmentator.TotalSegmentatorLogic.setupPythonRequirements(TotalSegmentator.TotalSegmentatorLogic())
        
        try:
            import PSMASegmentator
        except ModuleNotFoundError as e:
            self.log(_('PSMASegmentator Python package is required. Installing... (it may take several minutes)'))
            #Use Total Segmentator's package installer to install psma Segmentator
            skipped_output = TotalSegmentator.TotalSegmentatorLogic.pipInstallSelective(TotalSegmentator.TotalSegmentatorLogic(),
                    "psma_segmentator",
                    PSMASegmentatorLogic.getDownloadURL(),
                    packagesToSkip)

        

        return

            
    def process(self,
                inputSelectorOne: vtkMRMLScalarVolumeNode,
                inputSelectorTwo: vtkMRMLScalarVolumeNode,
                outputSegmentation: vtkMRMLScalarVolumeNode,
                suvSlider: float,
                defaultDeviceSelector: bool,
                cpuSelector: bool,
                cudaSelector: bool,
                cudaCustomSelector: bool,
                gpuIndexSelector: int,
                expandBox: bool,
                verboseBox: bool,
                fastBox: bool,
                lesion_vals: list[qt.QLabel]) -> None:

        """
        Run the processing algorithm.
        Can be used without GUI widget.
        :param inputVolume: volume to be thresholded
        :param outputVolume: thresholding result
        :param imageThreshold: values above/below this threshold will be set to 0
        :param invert: if True then values above the threshold will be set to 0, otherwise values below are set to 0
        :param showResult: show output volume in slice viewers
        """

        if not inputSelectorOne or not inputSelectorTwo:
            raise ValueError("Input or output volume is invalid")

        import time
        import qt

        #  Create new empty folder
        tempFolder = slicer.util.tempDirectory()

        inputFolder = tempFolder+"/PSMA_Inputs"
        inputFile1 = inputFolder + "/psma-result_0000.nii.gz"
        inputFile2 = inputFolder + "/psma-result_0001.nii.gz"
        outputSegmentationFolder = tempFolder + "/segmentation"
        outputLesionFolder = tempFolder + "/segmentation_lesion_classification"

        options = []
        if suvSlider > 0:
            options.append("--suv_threshold")
            options.append(f"{suvSlider}")

        if not defaultDeviceSelector:
            options.append("--device")
            if cpuSelector:
                options.append("cpu")
            elif cudaSelector:
                options.append("cuda")
            elif cudaCustomSelector:
                options.append(f"cuda:{gpuIndexSelector}")

        if expandBox:
            options.append("--expand_segmentations")

        if verboseBox:
            options.append("--verbose")

        if fastBox:
            options.append("--fast")
        
        startTime = time.time()
        logging.info("Processing started")

        slicer.util.exportNode(inputSelectorOne, inputFile1)
        slicer.util.exportNode(inputSelectorTwo, inputFile2)



        import sysconfig
        psmaSegmentatorExecutablePath = PSMASegmentatorLogic.executablePath()
        # Get Python executable path
        import shutil
        pythonSlicerExecutablePath = shutil.which('PythonSlicer')
        if not pythonSlicerExecutablePath:
            raise RuntimeError("Python was not found")
        psmaSegmentatorCommand = [ pythonSlicerExecutablePath, psmaSegmentatorExecutablePath]

        self.log(_('Creating segmentations with PSMA Segmentator AI...'))
        self.log(f"The following command is being run: {psmaSegmentatorCommand + ["-i", inputFolder, "-o", outputSegmentationFolder] + options}")
        
        slicer.app.setOverrideCursor(qt.Qt.WaitCursor)

        try:
            proc = slicer.util.launchConsoleProcess(psmaSegmentatorCommand + ["-i", inputFolder, "-o", outputSegmentationFolder] + options)
            slicer.app.restoreOverrideCursor()
        except Exception as e:
            slicer.app.restoreOverrideCursor()
            slicer.util.errorDisplay(_("Failed to process segmentation results.\n\n{exception}").format(exception=e))

        self.logProcessOutput(proc)
        

        stopTime = time.time()
        logging.info(f"Processing completed in {stopTime-startTime:.2f} seconds")

        
        segmentationResult = ""
        for outFile in os.listdir(outputSegmentationFolder):
            if(outFile.endswith(".nii.gz")):
                segmentationResult = outputSegmentationFolder +"/"+ outFile

        self.log(f"Output folder: {outputSegmentationFolder}")
        self.log(f"Output file: {segmentationResult}")

        loadedSegmentation = slicer.util.loadSegmentation(segmentationResult)
        outputSegmentation.setCurrentNode(loadedSegmentation)

        lesionResult = ""
        for outFile in os.listdir(outputLesionFolder):
            if(outFile.endswith(".csv")):
                lesionResult = outputLesionFolder +"/"+ outFile

        import csv
        lesion_data = {}
        with open(lesionResult) as f:
            data = csv.DictReader(f)
            for line in data:
                lesion_data = line
                break

        for label in lesion_vals:
            if label.objectName in lesion_data:
                label.setText(f"{lesion_data[label.objectName]}")
            else:
                label.setText(f"No Value Generated")
        

        self.log(_("Cleaning up temporary folder..."))
        if os.path.isdir(tempFolder):
            import shutil
            shutil.rmtree(tempFolder)
        


#
# PSMASegmentatorTest
#


class PSMASegmentatorTest(ScriptedLoadableModuleTest):
    """
    This is the test case for your scripted module.
    Uses ScriptedLoadableModuleTest base class, available at:
    https://github.com/Slicer/Slicer/blob/main/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def setUp(self):
        """Do whatever is needed to reset the state - typically a scene clear will be enough."""
        slicer.mrmlScene.Clear()

    def runTest(self):
        """Run as few or as many tests as needed here."""
        self.setUp()
        self.test_PSMASegmentator1()

    def test_PSMASegmentator1(self):
        """Ideally you should have several levels of tests.  At the lowest level
        tests should exercise the functionality of the logic with different inputs
        (both valid and invalid).  At higher levels your tests should emulate the
        way the user would interact with your code and confirm that it still works
        the way you intended.
        One of the most important features of the tests is that it should alert other
        developers when their changes will have an impact on the behavior of your
        module.  For example, if a developer removes a feature that you depend on,
        your test should break so they know that the feature is needed.
        """

        self.delayDisplay("Starting the test")

        # Get/create input data

        import SampleData

        registerSampleData()
        inputVolume = SampleData.downloadSample("PSMASegmentator1")
        self.delayDisplay("Loaded test data set")

        inputScalarRange = inputVolume.GetImageData().GetScalarRange()
        self.assertEqual(inputScalarRange[0], 0)
        self.assertEqual(inputScalarRange[1], 695)

        outputVolume = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeNode")
        threshold = 100

        # Test the module logic

        logic = PSMASegmentatorLogic()

        # Test algorithm with non-inverted threshold
        logic.process(inputVolume, outputVolume, threshold, True)
        outputScalarRange = outputVolume.GetImageData().GetScalarRange()
        self.assertEqual(outputScalarRange[0], inputScalarRange[0])
        self.assertEqual(outputScalarRange[1], threshold)

        # Test algorithm with inverted threshold
        logic.process(inputVolume, outputVolume, threshold, False)
        outputScalarRange = outputVolume.GetImageData().GetScalarRange()
        self.assertEqual(outputScalarRange[0], inputScalarRange[0])
        self.assertEqual(outputScalarRange[1], inputScalarRange[1])

        self.delayDisplay("Test passed")
