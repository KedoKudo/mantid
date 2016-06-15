from abc import (ABCMeta, abstractmethod)
from mantid.api import (WorkspaceGroup, AnalysisDataService)
from SANSFileInformation import (SANSFileInformationFactory, SANSFileType, get_extension_for_file_type)
from State.SANSStateData import (SANSStateData, SANSDataType)
from Common.SANSConstants import (SANSConstants, SANSInstrument)
from Common.SANSFunctions import (create_unmanaged_algorithm)
from SANSCalibration import apply_calibration


# -------------------
# Free functions
# -------------------
def update_file_information(file_information_dict, factory, data_type, file_name):
    info = factory.create_sans_file_information(file_name)
    file_information_dict.update({data_type: info})


def get_file_and_period_information_from_data(data):
    file_information_factory = SANSFileInformationFactory()
    file_information = dict()
    period_information = dict()
    if data.sample_scatter is not None:
        update_file_information(file_information, file_information_factory,
                                SANSDataType.SampleScatter, data.sample_scatter)
        period_information.update({SANSDataType.SampleScatter: data.sample_scatter_period})
    if data.sample_transmission is not None:
        update_file_information(file_information, file_information_factory,
                                SANSDataType.SampleTransmission, data.sample_transmission)
        period_information.update({SANSDataType.SampleTransmission: data.sample_transmission_period})
    if data.sample_direct is not None:
        update_file_information(file_information, file_information_factory,
                                SANSDataType.SampleDirect, data.sample_direct)
        period_information.update({SANSDataType.SampleDirect: data.sample_direct_period})
    if data.can_scatter is not None:
        update_file_information(file_information, file_information_factory,
                                SANSDataType.CanScatter, data.can_scatter)
        period_information.update({SANSDataType.CanScatter: data.can_scatter_period})
    if data.can_transmission is not None:
        update_file_information(file_information, file_information_factory,
                                SANSDataType.CanTransmission, data.can_transmission)
        period_information.update({SANSDataType.CanTransmission: data.can_transmission})
    if data.can_direct is not None:
        update_file_information(file_information, file_information_factory,
                                SANSDataType.CanDirect, data.can_direct)
        period_information.update({SANSDataType.CanDirect: data.can_direct})
    return file_information, period_information


def is_transmission_type(to_check):
    if ((to_check is SANSDataType.SampleTransmission) or (to_check is SANSDataType.SampleDirect) or
       (to_check is SANSDataType.CanTransmission) or (to_check is SANSDataType.CanDirect)):
        is_transmission = True
    else:
        is_transmission = False
    return is_transmission


def get_expected_workspace_names(file_information, is_transmission, period):
    suffix_file_type = get_extension_for_file_type(file_information)
    if is_transmission:
        suffix_data = SANSConstants.trans_suffix
    else:
        suffix_data = SANSConstants.sans_suffix

    run_number = file_information.get_run_number()

    # Three possibilities:
    #  1. No period data => 22024_sans_nxs
    #  2. Period data, but wants all => 22025p1_sans_nxs,  22025p2_sans_nxs, ...
    #  3. Period data, select particular period => 22025p3_sans_nxs
    if file_information.get_number_of_periods() == 1:
        workspace_name = "{}_{}_{}".format(run_number, suffix_data, suffix_file_type)
        names = [workspace_name]
    elif file_information.get_number_of_periods() > 1 and period is SANSStateData.ALL_PERIODS:
        workspace_names = []
        for period in range(1, file_information.get_number_of_periods() + 1):
            workspace_names.append("{}p{}_{}_{}".format(run_number, period, suffix_data, suffix_file_type))
        names = workspace_names
    elif file_information.get_number_of_periods() > 1 and period is not SANSStateData.ALL_PERIODS:
        workspace_name = "{}p{}_{}_{}".format(run_number, period, suffix_data, suffix_file_type)
        names = [workspace_name]
    else:
        raise RuntimeError("SANSLoad: Cannot create workspace names.")
    return names


def get_loader_info_for_isis_nexus(file_information, period):
    loader_options = {"Filename": file_information.get_file_name()}
    if file_information.is_event_mode():
        loader_name = "LoadEventNexus"
        # TODO: Multiperiod event files
        loader_options.update({"LoadMonitors": True})
    else:
        loader_name = "LoadISISNexus"
        loader_options.update({"LoadMonitors": "Separate"})
        if period is not SANSStateData.ALL_PERIODS:
            loader_options.update({"EntryNumber": period})
    return loader_name, loader_options


def get_loader_info_for_isis_nexus_transmission(file_information, period):
    loader_name = "LoadNexusMonitors"
    # TODO how to load period
    loader_options = {"Filename": file_information.get_file_name()}
    loader_options.update({"LoadEventMonitors": True,
                           "LoadHistoMonitors": True})
    return loader_name, loader_options


def get_loader_info_for_raw(file_information, period):
    loader_name = "LoadRaw"
    loader_options = {"Filename": file_information.get_file_name()}
    loader_options.update({"LoadMonitors": "Separate"})
    if period is not SANSStateData.ALL_PERIODS:
        loader_options.update({"PeriodList": period})
    return loader_name, loader_options


def get_loading_strategy(file_information, period, is_transmission):
    if is_transmission and file_information.get_type() == SANSFileType.ISISNexus:
        loader_name, loader_options = get_loader_info_for_isis_nexus_transmission(file_information, period)
    elif file_information.get_type() == SANSFileType.ISISNexus:
        loader_name, loader_options = get_loader_info_for_isis_nexus(file_information, period)
    elif file_information.get_type() == SANSFileType.ISISRaw:
        loader_name, loader_options = get_loader_info_for_raw(file_information, period)
    elif file_information.get_type() == SANSFileType.ISISNexusAdded:
        loader_name = None
        loader_options = {}
        pass
        # TODO: Add loader for added
    else:
        raise RuntimeError("SANSLoad: Cannot load SANS file of type {}".format(str(file_information.get_type())))
    loader = create_unmanaged_algorithm(loader_name, **loader_options)
    return loader


def add_workspaces_to_analysis_data_service(workspaces, workspace_names, is_monitor):
    if is_monitor:
        workspace_names = [workspace_name + SANSConstants.monitor_suffix for workspace_name in workspace_names]

    if len(workspaces) != len(workspace_names):
        raise RuntimeError("SANSLoad: There is a mismatch between the generated names and the length of"
                           " the WorkspaceGroup. The workspace has {} entries and there are {} "
                           "workspace names".format(len(workspaces), len(workspace_names)))

    for index in range(0, len(workspaces)):
        if not AnalysisDataService.doesExist(workspace_names[index]):
            AnalysisDataService.addOrReplace(workspace_names[index], workspaces[index])


def publish_workspaces_to_analysis_data_service(workspaces, workspace_monitors, workspace_names):
    add_workspaces_to_analysis_data_service(workspaces, workspace_names, is_monitor=False)

    # If the workspace monitor exists, then add it to the ADS as well
    if workspace_monitors is not None:
        add_workspaces_to_analysis_data_service(workspace_monitors, workspace_names, is_monitor=True)


def has_loaded_correctly_from_ads(file_information, workspaces, period):
    number_of_workspaces = len(workspaces)
    number_of_periods = file_information.get_number_of_periods()

    # Different cases: single-period, multi-period, multi-period with one period selected
    if number_of_periods == 1:
        is_valid = True if number_of_workspaces == 1 else False
    elif number_of_periods > 1 and period is not SANSStateData.ALL_PERIODS:
        is_valid = True if number_of_workspaces == 1 else False
    elif number_of_periods > 1 and period is SANSStateData.ALL_PERIODS:
        is_valid = True if number_of_workspaces == number_of_periods else False
    else:
        raise RuntimeError("SANSLoad: Loading data from the ADS has resulted in the a mismatch between the number of "
                           "period information and the number of loaded workspaces")
    return is_valid


def use_loaded_workspaces_from_ads(file_information, workspace_names, is_transmission,  period):
    workspaces = []
    workspace_monitors = []

    for workspace_name in workspace_names:
        if AnalysisDataService.doesExist(workspace_name):
            workspaces.append(AnalysisDataService.retrieve(workspace_name))

    if not is_transmission:
        monitor_names = [workspace_name + SANSConstants.monitor_suffix for workspace_name in workspace_names]
        for monitor_name in monitor_names:
            if AnalysisDataService.doesExist(monitor_name):
                workspace_monitors.append(AnalysisDataService.retrieve(monitor_name))

    # Check if all required workspaces could be found on the ADS. For now, we allow only full loading, ie we don't
    # allow picking up some child workspaces of a multi-period file from the ADS and having to load others. Either
    # all are found in the ADS or we have to reload again. If we are loading a scatter workspace and the monitors
    # are not complete, then we have to load the regular workspaces as well
    if not has_loaded_correctly_from_ads(file_information, workspaces, period):
        workspaces = []
    if not has_loaded_correctly_from_ads(file_information, workspace_monitors, period):
        workspaces = []
        workspace_monitors = []

    return workspaces, workspace_monitors


def run_loader(loader, file_information, is_transmission, period):
    loader.setProperty(SANSConstants.output_workspace, "dummy")
    loader.execute()

    # Get all output workspaces
    number_of_periods = file_information.get_number_of_periods()
    workspaces = []
    # Either we have a single-period workspace or we want a single period from a multi-period workspace in which case
    # we extract it via OutputWorkspace or we want all child workspaces of a multi-period workspace in which case we
    # need to extract it via OutputWorkspace_1, OutputWorkspace_2, ...
    if number_of_periods == 1 or (number_of_periods > 1 and period is not SANSStateData.ALL_PERIODS):
        for index in range(1, number_of_periods + 1):
            workspaces.append(loader.getProperty(SANSConstants.output_workspace).value)
    else:
        for index in range(1, number_of_periods + 1):
            workspaces.append(loader.getProperty(SANSConstants.output_workspace_group + str(index)).value)

    workspace_monitors = []
    if not is_transmission:
        if number_of_periods == 1 or (number_of_periods > 1 and period is not SANSStateData.ALL_PERIODS):
            for index in range(1, number_of_periods + 1):
                workspace_monitors.append(loader.getProperty(SANSConstants.output_monitor_workspace).value)
        else:
            for index in range(1, number_of_periods + 1):
                workspace_monitors.append(loader.getProperty(SANSConstants.output_monitor_workspace_group +
                                                             str(index)).value)
    return workspaces, workspace_monitors


def load_isis(data_type, file_information, period, use_loaded, publish_to_ads):
    workspace = None
    workspace_monitor = None

    is_transmission = is_transmission_type(data_type)

    # Get the workspace name
    workspace_names = get_expected_workspace_names(file_information, is_transmission, period)

    # Make potentially use of loaded workspaces. For now we can only identify them by their name
    # TODO: Add tag into sample logs
    if use_loaded:
        workspace, workspace_monitor = use_loaded_workspaces_from_ads(file_information, workspace_names,
                                                                      is_transmission, period)

    # Load the workspace if required.
    if workspace is None or workspace_monitor is None:
        # Get the loading strategy
        loader = get_loading_strategy(file_information, period, is_transmission)
        workspace, workspace_monitor = run_loader(loader, file_information, is_transmission, period)

    # Publish to ADS if required
    if publish_to_ads:
        publish_workspaces_to_analysis_data_service(workspace, workspace_monitor, workspace_names)

    # Associate the data type with the workspace
    workspace_pack = {data_type: workspace}
    workspace_monitor_pack = {data_type: workspace_monitor} if len(workspace_monitor) > 0 else None

    return workspace_pack, workspace_monitor_pack

# --------------------------------------------
# Put functions for other implementations here:
# --------------------------------------------


# -------------------------------------------------
# Load classes
# -------------------------------------------------
class SANSLoad(object):
    __metaclass__ = ABCMeta

    @abstractmethod
    def do_execute(self, data_info, use_loaded, publish_to_ads):
        pass

    def execute(self, data_info, use_loaded, publish_to_ads):
        SANSLoad._validate(data_info)
        return self.do_execute(data_info, use_loaded, publish_to_ads)

    @staticmethod
    def _validate(data_info):
        if not isinstance(data_info, SANSStateData):
            raise ValueError("SANSLoad: The provided state information is of the wrong type. It must be"
                             " of type SANSStateData,but was {}".format(str(type(data_info))))
        data_info.validate()


class SANSLoadISIS(SANSLoad):
    def do_execute(self, data_info, use_loaded, publish_to_ads):
        # Get all entries from the state file
        file_info, period_info = get_file_and_period_information_from_data(data_info)

        # Scatter files and Transmission/Direct files have to be loaded slightly differently,
        # hence we separate the loading process.
        # TODO: make parallel with multiprocessing (check how ws_handle is being passed)
        workspaces = dict()
        workspace_monitors = dict()
        for key, value in file_info.iteritems():
            workspace_pack, workspace_monitors_pack = load_isis(key, value, period_info[key],
                                                                use_loaded, publish_to_ads)
            workspaces.update(workspace_pack)
            if workspace_monitors_pack is not None:
                workspace_monitors.update(workspace_monitors_pack)

        # Apply the calibration if any exists.
        if data_info.calibration is not None:
            apply_calibration(workspaces, workspace_monitors, use_loaded, publish_to_ads)

        return workspaces, workspace_monitors


class SANSLoadFactory(object):
    def __init__(self):
        super(SANSLoadFactory, self).__init__()

    @staticmethod
    def _get_instrument_type(data):
        # Get the correct loader based on the sample scatter file
        data.validate()
        file_info, _ = get_file_and_period_information_from_data(data)
        sample_scatter_info = file_info[SANSDataType.SampleScatter]
        return sample_scatter_info.get_instrument()

    @staticmethod
    def create_loader(data):
        instrument_type = SANSLoadFactory._get_instrument_type(data)
        if instrument_type is SANSInstrument.LARMOR or instrument_type is SANSInstrument.LOQ or\
           instrument_type is SANSInstrument.SANS2D:
            loader = SANSLoadISIS()
        else:
            loader = None
            NotImplementedError("SANSLoaderFactory: Other instruments are not implemented yet.")
        return loader
