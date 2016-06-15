import math
from mantid.api import MatrixWorkspace
from abc import (ABCMeta, abstractmethod)
from State.SANSStateMoveWorkspace import (SANSStateMoveWorkspace, SANSStateMoveWorkspaceLOQ)
from Common.SANSConstants import (SANSInstrument, convert_string_to_sans_instrument,
                                  CanonicalCoordinates, SANSConstants)
from Common.SANSFunctions import create_unmanaged_algorithm


# -------------------------------------------------
# Free functions
# -------------------------------------------------

def move_component(workspace, offsets, component_to_move):
    move_name = "MoveInstrumentComponent"
    move_options = {"Workspace": workspace,
                    "ComponentName": component_to_move,
                    "RelativePosition": True}
    for key, value in offsets.iteritems():
        if key is CanonicalCoordinates.X:
            move_options.update({"X", value})
        elif key is CanonicalCoordinates.Y:
            move_options.update({"Y", value})
        elif key is CanonicalCoordinates.Z:
            move_options.update({"Z", value})
        else:
            raise RuntimeError("SANSMove: Trying to move the components along an unknown direction. "
                               "See here: {}".format(str(component_to_move)))
    alg = create_unmanaged_algorithm(move_name, move_options)
    alg.execute()


def rotate_component(workspace, angle, direction, component_to_move):
    rotate_name = "RotateInstrumentComponent"
    rotate_options = {"Workspace": workspace,
                      "ComponentName": component_to_move,
                      "RelativePosition": True}
    for key, value in direction.iteritems():
        if key is CanonicalCoordinates.X:
            rotate_options.update({"X", value})
        elif key is CanonicalCoordinates.Y:
            rotate_options.update({"Y", value})
        elif key is CanonicalCoordinates.Z:
            rotate_options.update({"Z", value})
        else:
            raise RuntimeError("SANSMove: Trying to rotate the components along an unknown direction. "
                               "See here: {}".format(str(component_to_move)))
    rotate_options.update({"Angle": angle})
    alg = create_unmanaged_algorithm(rotate_name, rotate_options)
    alg.execute()


def move_sample_holder(workspace, sample_offset, sample_offset_direction):
    offset = {sample_offset_direction: sample_offset}
    move_component(workspace, offset, 'some-sample-holder')


# -------------------------------------------------
# Move classes
# -------------------------------------------------
class SANSMove(object):
    __metaclass__ = ABCMeta

    def __init__(self):
        super(SANSMove, self).__init__()

    @abstractmethod
    def do_move_initial(self, move_info, workspace, coordinates, component):
        pass

    @abstractmethod
    def do_move_with_elementary_displacement(self, move_info, workspace, coordinates, component):
        pass

    @staticmethod
    @abstractmethod
    def is_correct(instrument_type, run_number, **kwargs):
        pass

    def move_initial(self, move_info, workspace, coordinates, component):
        SANSMove._validate(move_info, workspace, coordinates, component)
        return self.do_move_initial(move_info, workspace, coordinates, component)

    def move_with_elementary_displacement(self, move_info, workspace, coordinates, component):
        SANSMove._validate(move_info, workspace, coordinates, component)
        return self.do_move_initial(move_info, workspace, coordinates, component)

    @staticmethod
    def _validate(move_info, workspace, coordinates, component):
        if not coordinates:
            raise ValueError("SANSMove: The provided coordinates cannot be empty.")
        if not isinstance(workspace, MatrixWorkspace):
            raise ValueError("SANSMove: The input workspace has to be a MatrixWorkspace")
        if component not in move_info.detectors:
            raise ValueError("SANSMove: The component to be moved {} cannot be found in the"
                             " state inforamtion of type {}".format(str(component), str(type(move_info))))
        if not isinstance(move_info, SANSStateMoveWorkspace):
            raise ValueError("SANSMove: The provided state information is of the wrong type. It must be"
                             " of type SANSStateMoveWorkspace, but was {}".format(str(type(move_info))))
        move_info.validate()


class SANSMoveSANS2D(SANSMove):
    def __init__(self):
        super(SANSMoveSANS2D, self).__init__()

    @staticmethod
    def perform_x_and_y_tilts(workspace, detector):
        detector_name = detector.detector_name
        # Perform rotation a y tilt correction. This tilt rotates around the instrument axis / around the X-AXIS!
        y_tilt_correction = detector.y_tilt_correction
        if y_tilt_correction != 0.0:
            y_tilt_correction_direction = {CanonicalCoordinates.X: 1.0,
                                           CanonicalCoordinates.Y: 0.0,
                                           CanonicalCoordinates.Z: 0.0}
            rotate_component(workspace, y_tilt_correction, y_tilt_correction_direction, detector_name)

        # Perform rotation a x tilt correction. This tilt rotates around the instrument axis / around the Z-AXIS!
        x_tilt_correction = detector.x_tilt_correction
        if x_tilt_correction != 0.0:
            x_tilt_correction_direction = {CanonicalCoordinates.X: 0.0,
                                           CanonicalCoordinates.Y: 0.0,
                                           CanonicalCoordinates.Z: 1.0}
            rotate_component(workspace, x_tilt_correction, x_tilt_correction_direction, detector_name)

    @staticmethod
    def _move_high_angle_bank(move_info, workspace, coordinates):
        hab_detector_x = move_info.hab_detector_x
        hab_detector_z = move_info.hab_detector_z
        hab_detector_rotation = move_info.hab_detector_rotation
        hab_detector_radius = move_info.hab_detector_radius

        hab_detector_default_x_m = move_info.hab_detector_default_x_m
        hab_detector_default_sd_m = move_info.hab_detector_default_sd_m

        lab_detector_x = move_info.lab_detector_x

        # Detector and name
        hab_detector = move_info.detectors[SANSConstants.high_angle_bank]
        detector_name = hab_detector.detector_name

        # Perform x and y tilt
        SANSMoveSANS2D.perform_x_and_y_tilts(workspace, hab_detector)

        # Perform rotation of around the Y-AXIS. This is more complicated as the high angle bank detector is
        # offset.
        rotation_angle = (-hab_detector_rotation - hab_detector.rotation_correction)
        rotation_direction = {CanonicalCoordinates.X: 0.0,
                              CanonicalCoordinates.Y: 1.0,
                              CanonicalCoordinates.Z: 0.0}
        rotate_component(workspace, rotation_angle, rotation_direction, detector_name)

        # Add translational corrections
        x = coordinates[0]
        y = coordinates[1]
        lab_detector = move_info.detectors[SANSConstants.low_angle_bank]
        rotation_in_radians = math.pi * (hab_detector_rotation + hab_detector.rotation_correction)/180.

        x_shift = ((lab_detector_x + lab_detector.x_translation_correction -
                   hab_detector_x - hab_detector.x_translation_correction -
                   hab_detector.side_correction*(1.0 - math.cos(rotation_in_radians)) +
                   (hab_detector_radius + hab_detector.radius_correction)*(math.sin(rotation_in_radians)))/1000. -
                   hab_detector_default_x_m - x)

        y_shift = hab_detector.y_translation_correction/1000. - y

        z_shift = (hab_detector_z + hab_detector.z_translation_correction +
                   (hab_detector_radius + hab_detector.radius_correction) * (1.0 - math.cos(rotation_in_radians)) -
                   hab_detector.side_correction * math.sin(rotation_in_radians)) / 1000. - hab_detector_default_sd_m
        offset = {CanonicalCoordinates.X: x_shift,
                  CanonicalCoordinates.Y: y_shift,
                  CanonicalCoordinates.Z: z_shift}
        move_component(workspace, offset, detector_name)

    @staticmethod
    def _move_low_angle_bank(move_info, workspace, coordinates):
        # Perform x and y tilt
        lab_detector = move_info.detectors[SANSConstants.low_angle_bank]

        SANSMoveSANS2D.perform_x_and_y_tilts(workspace, lab_detector)

        lab_detector_z = move_info.lab_detector_z
        lab_detector_default_sd_m = move_info.lab_detector_default_sd_m

        x_shift = -coordinates[0]
        y_shift = -coordinates[1]
        z_shift = (lab_detector_z + lab_detector.z_translation_correction) / 1000. - lab_detector_default_sd_m
        detector_name = lab_detector.detector_name
        offset = {CanonicalCoordinates.X: x_shift,
                  CanonicalCoordinates.Y: y_shift,
                  CanonicalCoordinates.Z: z_shift}
        move_component(workspace, offset, detector_name)

    @staticmethod
    def _move_monitor_4(workspace, move_info):
        if move_info.monitor_4_offset != 0.0:
            monitor_4_name = move_info.monitors[4]
            instrument = workspace.getInstrument()
            monitor_4 = instrument.getComponentByName(monitor_4_name)

            # Get position of monitor 4
            monitor_position = monitor_4.getPos()
            z_position_monitor = monitor_position.getZ()

            # The location is relative to the rear-detector, get this position
            lab_detector = move_info.detectors[SANSConstants.low_angle_bank]
            detector_name = lab_detector.detector_name
            lab_detector_component = instrument.getComponentByName(detector_name)
            detector_position = lab_detector_component.getPos()
            z_position_detector = detector_position.getZ()

            monitor_4_offset = move_info.monitor_4_offset / 1000.
            z_new = z_position_detector + monitor_4_offset
            z_move = z_new - z_position_monitor
            offset = {CanonicalCoordinates.X: z_move}
            move_component(workspace, offset, monitor_4_name)

    def do_move_initial(self, move_info, workspace, coordinates, component):
        # For LOQ we only have to coordinates
        assert(len(coordinates) == 2)

        # Move the high angle bank
        self._move_high_angle_bank(move_info, workspace, coordinates)

        # Move the low angle bank
        self._move_low_angle_bank(move_info, workspace, coordinates)

        # Move the sample holder
        move_sample_holder(workspace, move_info.sample_offset, move_info.sample_offset_direction)

        # Move monitor 4
        self._move_monitor_4(workspace, move_info)

    def do_move_with_elementary_displacement(self, move_info, workspace, coordinates, component):
        # For LOQ we only have to coordinates
        assert(len(coordinates) == 2)

    @staticmethod
    def is_correct(instrument_type, run_number, **kwargs):
        return True if instrument_type is SANSInstrument.SANS2D else False


class SANSMoveLOQ(SANSMove):
    def __init__(self):
        super(SANSMoveLOQ, self).__init__()

    def do_move_initial(self, move_info, workspace, coordinates, component):
        # For LOQ we only have to coordinates
        assert(len(coordinates) == 2)
        # First move the sample holder
        move_sample_holder(workspace, move_info.sample_offset, move_info.sample_offset_direction)

        x = coordinates[0]
        y = coordinates[1]
        center_position = move_info.center_position

        x_shift = center_position - x
        y_shift = center_position - y

        # Get the detector name
        component_name = move_info.detectors[component].detector_name

        # Shift the detector by the the input amount
        offset = {CanonicalCoordinates.X: x_shift,
                  CanonicalCoordinates.Y: y_shift}
        move_component(workspace, offset, component_name)

        # Shift the detector according to the corrections of the detector under investigation
        offset_from_corrections = {CanonicalCoordinates.X: move_info.detectors[component].x_translation_correction,
                                   CanonicalCoordinates.Y: move_info.detectors[component].y_translation_correction,
                                   CanonicalCoordinates.Z: move_info.detectors[component].z_translation_correction}
        move_component(workspace, offset_from_corrections, component_name)

    def do_move_with_elementary_displacement(self, move_info, workspace, coordinates, component):
        # For LOQ we only have to coordinates
        assert(len(coordinates) == 2)

        # Get the detector name
        component_name = move_info.detectors[component].detector_name

        # Offset
        offset = {CanonicalCoordinates.X: coordinates[0],
                  CanonicalCoordinates.Y: coordinates[1]}
        move_component(workspace, offset, component_name)

    @staticmethod
    def is_correct(instrument_type, run_number, **kwargs):
        return True if instrument_type is SANSInstrument.LOQ else False


class SANSMoveFactory(object):
    def __init__(self):
        super(SANSMoveFactory, self).__init__()

    @staticmethod
    def create_mover(workspace):
        # Get selection
        run_number = workspace.getRunNumber()
        instrument = workspace.getInstrument()
        instrument_type = convert_string_to_sans_instrument(instrument.getName())

        if SANSMoveLOQ.is_correct(instrument_type, run_number):
            mover = SANSMoveLOQ()
        else:
            mover = None
            NotImplementedError("SANSLoaderFactory: Other instruments are not implemented yet.")
        return mover
