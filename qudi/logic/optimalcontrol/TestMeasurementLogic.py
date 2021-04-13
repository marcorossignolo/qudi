"""
Test Problems for Optimal Control Suite
"""

from qudi.core.module import LogicBase
from quocslib.optimalcontrolproblems.OneQubitProblem import OneQubit
from quocslib.optimalcontrolproblems.RosenbrockProblem import Rosenbrock
from qtpy import QtCore

import time


class TestMeasurementLogic(LogicBase):

    fom_signal = QtCore.Signal(float)

    is_active = False

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)
        print("Figure of merit logic initialization")
        self.control_problem = OneQubit()
        return

    def on_activate(self):
        self.log.info("Starting the TestMeasurement Logic")
        return 0

    def on_deactivate(self):
        self.log.info("Close the TestMeasurement logic")
        return 0

    @QtCore.Slot(bool)
    def set_is_active(self, is_active):
        if is_active:
            self.log.info("The setup is activated")
        else:
            self.log.info("The setup is deactivated")
        self.is_active = is_active

    @QtCore.Slot(list, list, list)
    def get_measurement(self, pulses, parameters, timegrids):
        """ """
        if not self.is_active:
            self.log.warn("Activate the experimental logic wih testmeasurement.set_is_active(True)")

        while not self.is_active:
            time.sleep(2.0)

        self.fom_signal.emit(self.control_problem.get_FoM(pulses, parameters, timegrids)["FoM"])
