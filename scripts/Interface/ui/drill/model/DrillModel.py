# Mantid Repository : https://github.com/mantidproject/mantid
#
# Copyright &copy; 2018 ISIS Rutherford Appleton Laboratory UKRI,
#     NScD Oak Ridge National Laboratory, European Spallation Source
#     & Institut Laue - Langevin
# SPDX - License - Identifier: GPL - 3.0 +

import os
import sys
import numpy

from qtpy.QtCore import QObject, Signal, QThread

import mantid.simpleapi as sapi
from mantid.kernel import *
from mantid.api import *

from .configurations import RundexSettings
from .DrillAlgorithmPool import DrillAlgorithmPool
from .DrillTask import DrillTask
from .DrillParameterController import DrillParameter, DrillParameterController
from .DrillIOModel import DrillIOModel


class DrillModel(QObject):

    """
    Data directory on Linux.
    """
    LINUX_BASE_DATA_PATH = "/net/serdon/illdata/"

    """
    Data directory on MacOS.
    """
    MACOS_BASE_DATA_PATH = "/Volumes/illdata/"

    """
    Data directory on Windows.
    """
    WIN_BASE_DATA_PATH = "Z:\\"

    """
    Raw data directory name.
    """
    RAW_DATA_DIR = "rawdata"

    """
    Processed data directory name.
    """
    PROCESSED_DATA_DIR = "processed"

    ###########################################################################
    # signals                                                                 #
    ###########################################################################

    """
    Raised when a process is started.
    Args:
        (int): sample index
    """
    processStarted = Signal(int)

    """
    Raised when a process finished with success.
    Args:
        (int): sample index
    """
    processSuccess = Signal(int)

    """
    Raised when a process failed.
    Args:
        (int): sample index
    """
    processError = Signal(int)

    """
    Raised when all the processing are done.
    """
    processingDone = Signal()

    """
    Raised each time the processing progress is updated.
    Args:
        (int): sample index
    """
    progressUpdate = Signal(int)

    """
    Raised when a new param is ok.
    Args:
        (int): sample index
        (str): parameter name
    """
    paramOk = Signal(int, str)

    """
    Raised when a new parameter is wrong.
    Args:
        (int): sample index
        (str): parameter name
    """
    paramError = Signal(int, str, str)

    def __init__(self):
        super(DrillModel, self).__init__()
        self.instrument = None
        self.acquisitionMode = None
        self.cycleNumber = None
        self.experimentId = None
        self.algorithm = None
        self.samples = list()
        self.groups = dict()
        self.masterSamples = dict()
        self.settings = dict()
        self.controller = None
        self.visualSettings = dict()
        self.ioModel = None

        # set the instrument and default acquisition mode
        self.tasksPool = DrillAlgorithmPool()
        self.setInstrument(config['default.instrument'], log=False)

        # setup the thread pool
        self.tasksPool.signals.taskStarted.connect(self._onTaskStarted)
        self.tasksPool.signals.taskSuccess.connect(self._onTaskSuccess)
        self.tasksPool.signals.taskError.connect(self._onTaskError)
        self.tasksPool.signals.progressUpdate.connect(self._onProcessingProgress)
        self.tasksPool.signals.processingDone.connect(self._onProcessingDone)

    def setInstrument(self, instrument, log=True):
        """
        Set the instrument. This methods change the current instrument and all
        the associated parameters (acquisition mode, algorithm, parameters). It
        also empty the sample list and the settings.

        Args:
            instrument (str): instrument name
        """
        self.samples = list()
        self.groups = dict()
        self.masterSamples = dict()
        self.settings = dict()
        self.columns = list()
        self.visualSettings = dict()
        self.instrument = None
        self.acquisitionMode = None
        self.algorithm = None

        # When the user changes the facility after DrILL has been started
        if config['default.facility'] != 'ILL':
            logger.error('Drill is enabled only if the facility is set to ILL.')
            return

        if (instrument in RundexSettings.ACQUISITION_MODES):
            config['default.instrument'] = instrument
            self.instrument = instrument
            self.setAcquisitionMode(RundexSettings.ACQUISITION_MODES[instrument][0])
        else:
            if log:
                logger.error('Instrument {0} is not supported yet.'
                             .format(instrument))

    def getInstrument(self):
        """
        Get the current instrument.

        Returns:
            str: the instrument name
        """
        return self.instrument

    def setAcquisitionMode(self, mode):
        """
        Set the acquisition mode. The acquisition mode is modified only if it
        corresponds to the current used instrument. If success, the parameters
        controller is also setup.

        Args:
            mode (str): aquisition mode name
        """
        if ((self.instrument is None)
                or (mode not in RundexSettings.ACQUISITION_MODES[
                    self.instrument])):
            return
        self.samples = list()
        self.groups = dict()
        self.masterSamples = dict()
        self.visualSettings = dict()
        self.acquisitionMode = mode
        self.columns = RundexSettings.COLUMNS[self.acquisitionMode]
        self.algorithm = RundexSettings.ALGORITHM[self.acquisitionMode]
        if self.acquisitionMode in RundexSettings.THREADS_NUMBER:
            nThreads = RundexSettings.THREADS_NUMBER[self.acquisitionMode]
        else:
            nThreads = QThread.idealThreadCount()
        self.tasksPool.setMaxThreadCount(nThreads)
        self.settings = dict.fromkeys(
                RundexSettings.SETTINGS[self.acquisitionMode])
        self._setDefaultSettings()
        self._initController()

    def getAcquisitionMode(self):
        """
        Get the current acquisition mode.

        Returns:
            str: the acquisition mode
        """
        return self.acquisitionMode

    def getAvailableAcquisitionModes(self):
        """
        Get the list of acquisition mode available for the current instrument.
        """
        if (self.instrument is None):
            return list()
        return RundexSettings.ACQUISITION_MODES[self.instrument]

    def setCycleAndExperiment(self, cycle, experiment):
        """
        Set the cycle number and the experiment ID. This method tries to add the
        usual data directory to the user directories list if it exists.

        Args:
            cycle (str): cycle number
            experiment (str): experiment ID
        """
        self.cycleNumber = cycle
        self.experimentId = experiment

        # platform
        if sys.platform.startswith("linux"):
            baseDir = self.LINUX_BASE_DATA_PATH
        elif sys.platform.startswith("darwin"):
            baseDir = self.MACOS_BASE_DATA_PATH
        elif sys.platform.startswith("win32"):
            baseDir = self.WIN_BASE_DATA_PATH
        else:
            return

        if not os.path.isdir(baseDir):
            return

        # data
        dataDir = os.path.join(baseDir, "{0}/{1}/{2}"
                                        .format(cycle,
                                                self.instrument.lower(),
                                                experiment))
        rawDataDir = os.path.join(dataDir, self.RAW_DATA_DIR)
        processedDataDir = os.path.join(dataDir, self.PROCESSED_DATA_DIR)
        if not os.path.isdir(dataDir):
            logger.warning("Cycle number and experiment ID do not lead to a "
                           "valid directory in the usual data directory ({0}): "
                           "{1} does not exist."
                           .format(baseDir, dataDir))
            return

        # add in user directories if needed
        userDirs = ConfigService.getDataSearchDirs()
        if ((os.path.isdir(rawDataDir)) and (rawDataDir not in userDirs)):
            ConfigService.appendDataSearchDir(rawDataDir)
        if ((os.path.isdir(processedDataDir))
                and (processedDataDir not in userDirs)):
            ConfigService.appendDataSearchDir(processedDataDir)

    def getCycleAndExperiment(self):
        """
        Get the cycle number and the experiment ID.

        Returns:
            str, str: cycle number, experiment ID
        """
        return self.cycleNumber, self.experimentId

    def _initController(self):
        """
        Initialize the parameter controller.
        """
        def onParamOk(p):
            if ((p.sample != -1) and (p.name not in self.columns)):
                self.paramOk.emit(p.sample, RundexSettings.CUSTOM_OPT_JSON_KEY)
            elif ((p.name in self.columns) or (p.name in self.settings)):
                self.paramOk.emit(p.sample, p.name)

        def onParamError(p):
            if ((p.sample != -1) and (p.name not in self.columns)):
                self.paramError.emit(p.sample,
                                     RundexSettings.CUSTOM_OPT_JSON_KEY,
                                     p.errorMsg)
            elif ((p.name in self.columns) or (p.name in self.settings)):
                self.paramError.emit(p.sample, p.name, p.errorMsg)

        if (self.algorithm is None):
            return
        self.controller = DrillParameterController(self.algorithm)
        self.controller.signals.okParam.connect(onParamOk)
        self.controller.signals.wrongParam.connect(onParamError)
        self.controller.start()

    def setSettings(self, settings):
        """
        Update the settings from a dictionnary.

        Args:
            settings (dict(str: any)): settings key,value pairs. Value can be
                                       str, int, float or bool
        """
        for (k, v) in settings.items():
            if k in self.settings:
                self.settings[k] = v

    def getSettings(self):
        """
        Get the settings.

        Returns:
            dict(str, any): the settings. Value can be str, int, float or bool
        """
        return self.settings

    def getSettingsTypes(self):
        """
        Get informations about the algorithm settings. For all settings that
        should appear in the settings dialog, the function will return their
        type, allowed values and documentation. This method is used to generate
        the settings dialog automatically.

        Returns:
            tuple(dict(str: str), dict(str: list(str)), dict(str: str)): three
                dictionnaries for type, allowed values and documentation. Each
                of them uses the setting name as key. The type is a str:
                "file", "workspace", "combobox", "bool" or "string".
        """
        types = dict()
        values = dict()
        docs = dict()
        if not self.algorithm:
            return types, values, docs

        alg = sapi.AlgorithmManager.createUnmanaged(self.algorithm)
        alg.initialize()
        for s in self.settings:
            p = alg.getProperty(s)
            if (isinstance(p, FileProperty)):
                t = "file"
            elif (isinstance(p, MultipleFileProperty)):
                t = "files"
            elif (isinstance(p, (WorkspaceGroupProperty,
                                 MatrixWorkspaceProperty))):
                t = "workspace"
            elif (isinstance(p, StringPropertyWithValue)):
                if (p.allowedValues):
                    t = "combobox"
                else:
                    t = "string"
            elif (isinstance(p, BoolPropertyWithValue)):
                t = "bool"
            elif (isinstance(p, FloatArrayProperty)):
                t = "floatArray"
            elif (isinstance(p, IntArrayProperty)):
                t = "intArray"
            else:
                t = "string"

            types[s] = t
            values[s] = p.allowedValues
            docs[s] = p.documentation

        return (types, values, docs)

    def _setDefaultSettings(self):
        """
        Set the settings to their defautl values. This method takes the default
        values directly from the algorithm.
        """
        if not self.algorithm:
            return
        alg = sapi.AlgorithmManager.createUnmanaged(self.algorithm)
        alg.initialize()

        for s in self.settings:
            p = alg.getProperty(s)
            v = p.value
            if (isinstance(v, numpy.ndarray)):
                self.settings[s] = v.tolist()
            else:
                self.settings[s] = v

    def checkParameter(self, param, value, sample=-1):
        """
        Check a parameter by giving it name and value. The sample index is a
        facultative parameter. This method pushes the parameter on the
        controller queue.

        Args:
            param (str): parameter name
            value (any): parameter value. Can be str, bool
            sample (int): sample index if it is a sample specific parameter
        """
        self.controller.addParameter(DrillParameter(param, value, sample))

    def checkAllParameters(self):
        """
        Check all the parameters.
        """
        for i in range(len(self.samples)):
            for (n, v) in self.samples[i].items():
                if n == "CustomOptions":
                    for (nn, vv) in v.items():
                        self.controller.addParameter(DrillParameter(nn, vv, i))
                else:
                    self.controller.addParameter(DrillParameter(n, v, i))
        for (n, v) in self.settings.items():
            self.controller.addParameter(DrillParameter(n, v, -1))

    def changeParameter(self, row, column, contents):
        """
        Change parameter value and update the model samples. The method is able
        to parse usual parameters (present in self.columns) and those coming
        from the custom options. It submits the new value to the parameters
        controller to check it. In case of empty value, the paramOk signal is
        sent without any submission to the controller.

        Args:
            row (int): index of the sample in self.samples
            column (int): index of the parameter in self.columns
            contents (str): new value
        """
        if (not contents):
            self.paramOk.emit(row, self.columns[column])
            if (self.columns[column] in self.samples[row]):
                del self.samples[row][self.columns[column]]
            return

        if (self.columns[column] == RundexSettings.CUSTOM_OPT_JSON_KEY):
            options = dict()
            for option in contents.split(';'):
                if ('=' not in option):
                    self.paramError.emit(row, self.columns[column],
                                         "Badly formatted custom options")
                    return
                name = option.split("=")[0]
                value = option.split("=")[1]
                # everything is a str, we try to find bool
                if value in ['true', 'True', 'TRUE']:
                    value = True
                if value in ['false', 'False', 'FALSE']:
                    value = False
                options[name] = value
            for (k, v) in options.items():
                self.checkParameter(k, v, row)
            self.samples[row][RundexSettings.CUSTOM_OPT_JSON_KEY] = options
        else:
            self.samples[row][self.columns[column]] = contents
            self.checkParameter(self.columns[column], contents, row)

    def groupSamples(self, samples, groupName=None):
        """
        Group samples.

        Args:
            samples (list(int)): sample indexes

        Returns:
            str: name of the created group
        """
        for sample in samples:
            for group in self.groups:
                if sample in self.groups[group]:
                    self.groups[group].remove(sample)
                if ((group in self.masterSamples)
                        and (self.masterSamples[group] == sample)):
                    del self.masterSamples[group]

        self.groups = {k:v for k,v in self.groups.items() if v}

        if not groupName:
            groupName = 'A'
            while groupName in self.groups:
                groupName = chr(ord(groupName) + 1)
        self.groups[groupName] = samples

        return groupName

    def ungroupSamples(self, samples):
        """
        Ungroup samples.

        Args:
            samples (list(int)): sample indexes
        """
        for sample in samples:
            for group in self.groups:
                if sample in self.groups[group]:
                    self.groups[group].remove(sample)
                if ((group in self.masterSamples)
                        and (self.masterSamples[group] == sample)):
                    del self.masterSamples[group]

        self.groups = {k:v for k,v in self.groups.items() if v}

    def setSamplesGroups(self, groups):
        """
        Set the dictionnary of samples groups.

        Args:
            groups (dict(str:list(int))): samples groups
        """
        self.groups = {k:v for k,v in groups.items()}

    def getSamplesGroups(self):
        """
        Get the samples groups.

        Returns:
            dict(str, list(int)): groups of samples
        """
        return {k:v for k,v in self.groups.items()}

    def setMasterSamples(self, masterSamples):
        """
        Set the dictionnary of master samples.

        Args:
            masterSamples (dict(str:int)): master samples
        """
        self.masterSamples = {k:v for k,v in masterSamples.items()}

    def getMasterSamples(self):
        """
        Get the master samples of each groups.

        Returns:
            dict(str, int): master samples for each group.
        """
        return {k:v for k,v in self.masterSamples.items()}

    def setGroupMaster(self, sample):
        """
        Set the sample as master for its group.

        Args:
            sample (int): sample index

        Returns:
            str: name of the group, None if the row is not in a group
        """
        for group in self.groups:
            if sample in self.groups[group]:
                self.masterSamples[group] = sample
                return group
        return None

    def getProcessingParameters(self, sample):
        """
        Get the keyword arguments to be provided to an algorithm. This will
        merge the global settings and the row specific settings in a single
        dictionnary. It will also remove all the empty parameters.

        Args:
            sample (int): sample index

        Returns:
            dict(str, any): key, value pairs of parameters. Value can be str,
                            int, float, bool
        """
        params = dict()
        if self.acquisitionMode in RundexSettings.FLAGS:
            params.update(RundexSettings.FLAGS[self.acquisitionMode])
        params.update(self.settings)

        # search for master sample
        master = None
        for group in self.groups:
            if sample in self.groups[group]:
                master = None
                if group in self.masterSamples:
                    master = self.masterSamples[group]
                if master is not None:
                    params.update(self.samples[master])

        params.update(self.samples[sample])
        # override global params with custom ones
        if "CustomOptions" in params:
            params.update(params["CustomOptions"])
            del params["CustomOptions"]
        # remove empty params
        for (k, v) in list(params.items()):
            if v is None:
                del params[k]
        # add the output workspace param
        if "OutputWorkspace" not in params:
            params["OutputWorkspace"] = "sample_" + str(sample + 1)
        return params

    def process(self, elements):
        """
        Start samples processing.

        Args:
            elements (list(int)): list of sample indexes to be processed
        """
        tasks = list()
        for e in elements:
            if (e >= len(self.samples)) or (not self.samples[e]):
                continue
            kwargs = self.getProcessingParameters(e)
            tasks.append(DrillTask(e, self.algorithm, **kwargs))
        self.tasksPool.addProcesses(tasks)

    def _onTaskStarted(self, ref):
        """
        Called each time a task starts.

        Args:
            ref (int): sample index
        """
        name = str(ref + 1)
        logger.information("Starting of sample {0} processing"
                           .format(name))
        self.processStarted.emit(ref)

    def _onTaskSuccess(self, ref):
        """
        Called when a task finished with success.

        Args:
            ref (int): sample index
        """
        name = str(ref + 1)
        logger.information("Processing of sample {0} finished with sucess"
                           .format(name))
        self.processSuccess.emit(ref)

    def _onTaskError(self, ref, msg):
        """
        Called when a processing fails. This method logs a message and fires the
        corresponding signal.

        Args:
            ref (int): sample index
            msg (str): error msg
        """
        name = str(ref + 1)
        logger.error("Error while processing sample {0}: {1}"
                     .format(name, msg))
        self.processError.emit(ref)

    def _onProcessingProgress(self, progress):
        """
        Called each time a processing updates its progress.

        Args:
            ref (int): sample index
            progress (float): progress value (between 0.0 and 1.0)
        """
        self.progressUpdate.emit(progress)

    def _onProcessingDone(self):
        """
        Called when the processing is done.
        """
        self.processingDone.emit()

    def stopProcess(self):
        """
        Stop current processing.
        """
        self.tasksPool.abortProcessing()

    def setIOFile(self, filename):
        """
        Setup the io service on a provided filename.

        Args:
            filename (str): the filename
        """
        self.ioModel = DrillIOModel(filename, self)

    def resetIOFile(self):
        """
        Reset the IO service.
        """
        self.ioModel = None

    def getIOFile(self):
        """
        Get the filename used by the IO service.
        """
        if self.ioModel:
            return self.ioModel.getFilename()
        return None

    def importRundexData(self):
        """
        Import data.
        """
        if self.ioModel:
            self.ioModel.load()

    def exportRundexData(self):
        """
        Export data.
        """
        if self.ioModel:
            self.ioModel.save()

    def setVisualSettings(self, vs):
        """
        Set the visual settings.

        Args:
            vs (dict(str:str)): visual settings
        """
        if vs:
            self.visualSettings = {k:v for k,v in vs.items()}
        else:
            self.visualSettings = dict()

    def getVisualSettings(self):
        """
        Get the saved visual settings

        Returns:
            dict: visual settings that the view understands
        """
        return {k:v for k,v in self.visualSettings.items()}

    def getColumnHeaderData(self):
        """
        Get the column names and tooltips in two lists with same length.

        Returns:
            list(str): list of column names
            list(str): list of column tooltips
        """
        if not self.columns:
            return [], []

        alg = sapi.AlgorithmManager.createUnmanaged(self.algorithm)
        alg.initialize()

        tooltips = list()
        for c in self.columns:
            try:
                p = alg.getProperty(c)
                tooltips.append(p.documentation)
            except:
                tooltips.append(c)

        return self.columns, tooltips

    def setSamples(self, samples):
        self.samples = [s for s in samples]

    def addSample(self, ref):
        """
        Add a sample.

        Args:
            ref (int): sample index; if -1 the sample is added to the end
            contents (dict(str:str)): sample parameters
        """
        self.samples.insert(ref, dict())

    def deleteSample(self, ref):
        """
        Remove a sample.

        Args:
            ref (int): sample index
        """
        del self.samples[ref]
        # remove from groups if needed
        for group in self.groups:
            if ref in self.groups[group]:
                self.groups[group].remove(ref)
                if ((group in self.masterSamples)
                        and (self.masterSamples[group] == ref)):
                    del self.masterSamples[group]

    def getSamples(self):
        """
        Get the list of all the samples.

        Return:
            list(dict(str:str)): samples
        """
        return [s for s in self.samples]

    def getRowsContents(self):
        """
        Get all the samples as a table, 1 sample per row.

        Returns:
            list(list(str)): table contents
        """
        rows = list()
        for sample in self.samples:
            row = list()
            for column in self.columns[:-1]:
                if column in sample:
                    row.append(str(sample[column]))
                else:
                    row.append("")
            if self.columns[-1] in sample:
                options = list()
                for (k, v) in sample[self.columns[-1]].items():
                    options.append(str(k) + "=" + str(v))
                row.append(';'.join(options))
            rows.append(row)
        return rows
