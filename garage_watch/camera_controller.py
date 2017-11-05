"""
Contains classes related to the control of a surveillance camera reacting
to sensors to start or stop recording
"""
import logging

from transitions import Machine


logger = logging.getLogger(__name__)


class CameraController(object):
    """
    Class containing the state machine to manage triggers to garage
    door opening and closing, and scheduling recording. Uses
    transitions library to implement a Finite State Machine (FSM).

    The states are:

    on_hold (initial):
        The system is dormant waiting for door to be opene
    prepare:
        The system is activated waiting for certain time to start recording
    recording:
        The system camera is recording video

    The events:

    door_open:
        Triggered when the door sensor goes from closed to open
    door_closed:
        Triggered when the door sensor goes from open to closed
    prepare_finished:
        Triggered when preparations to record video are completed
    cancel_requested:
        Triggered to cancel ongoing recording or its preparations

    """

    states = ('on_hold', 'prepare', 'record')

    def __init__(self):

        # Define the transitions.Machine state machine.
        # ignore_invalid_triggers=True to avoid exceptions
        self.machine = Machine(
            model=self,
            states=CameraController.states,
            initial='on_hold',
            ignore_invalid_triggers=True)

        # transition on door opening while on_hold
        self.machine.add_transition(trigger='door_open', source='on_hold', dest='prepare')
        # do nothing on door closing while on_hold, defined to hook logging
        self.machine.add_transition(trigger='door_closed', source='on_hold', dest='on_hold')

        # transtion from recording preparations to record
        self.machine.add_transition(trigger='prepare_finished', source='prepare', dest='record')

        # transitions happening when door closes while recording or preparing
        self.machine.add_transition(trigger='door_closed', source='record', dest='on_hold')
        self.machine.add_transition(trigger='door_closed', source='prepare', dest='on_hold',
                                    before=['_log_preparation_cancelled'])

        # transitions for cancellation requested
        self.machine.add_transition(trigger='cancel_requested', source='prepare', dest='on_hold',
                                    before=['_log_preparation_cancelled'])
        self.machine.add_transition(trigger='cancel_requested', source='record', dest='on_hold',
                                    before=['_log_record_cancelled'])

        # not documented in transitions API but it is possible to add
        # a prepare callback when an event is triggered on a state accepting it
        # it will
        for event in self.machine.events:
            if hasattr(self, 'on_event_' + event):
                self.machine.events[event].add_callback('prepare', 'on_event_' + event)

    def on_event_door_open(self):
        """
        Callback when door_open event happens in a valid state
        """
        logger.info("Door openened", extra=dict(event='door_open'))

    def on_event_door_closed(self):
        """
        Callback when door_closed event happens in a valid state
        """
        logger.info("Door closed", extra=dict(event='door_closed'))

    def on_event_cancel_requested(self):
        """
        Callback when cancel_requested event happens in a valid state
        """
        logger.info("Cancel requested", extra=dict(event='cancel_requested'))

    def on_event_prepare_finished(self):
        """
        Callback when prepare_finished event happens in a valid state
        """
        logger.info("Preparations finished", extra=dict(event='prepare_finished'))

    def on_enter_prepare(self):
        """
        Callback happening when the `prepare` state is entered. Calls
        the abstract method `prepare_recording` to perform whatever
        task needed before starting video recording, for example wait
        for some time until delay is finally open or perform any other
        checks
        """
        logger.info("Preparing to record", extra=dict(event='record_prepare_start'))
        self.prepare_recording()

    def on_enter_record(self):
        """
        Callback happening when the `record` state is entered. Calls
        the abstract method `start_recording` to start the recording of
        video
        """
        logger.info("Recording started", extra=dict(event='record_start'))
        self.start_recording()

    def on_exit_record(self):
        """
        Callback happening when the `record` state is exited. Calls
        the abstract method `stop_recording` to stop the recording of
        video
        """
        logger.info("Recording finished", extra=dict(event='record_end'))
        self.stop_recording()

    def prepare_recording(self):
        """
        Abstract method for defining preparations for recording
        after the preparations are done, call `self.prepare_finished()`
        to move to recording state
        """
        raise NotImplementedError()

    def start_recording(self):
        """
        Abstract method to execute start of video recording
        """
        raise NotImplementedError()

    def stop_recording(self):
        """
        Abstract method to manage stop of video recording
        """
        raise NotImplementedError()

    def _log_preparation_cancelled(self):
        """
        Logs that preparations for recording have been cancelled
        """
        logger.info("Preparations for recording cancelled", extra=dict(event='record_prepare_cancel'))

    def _log_record_cancelled(self):
        """
        Logs that recording recording has been cancelled
        """
        logger.info("Recording cancelled", extra=dict(event='record_cancel'))
