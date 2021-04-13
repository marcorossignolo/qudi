"""
FoM class. Here are present all the problem I need for my thesis
"""
import time

from qtpy import QtCore
from qudi.core.module import LogicBase
from quocslib.figureofmeritevaluation.AbstractFom import AbstractFom
#  TODO implement the file update communication part


class ReceiveMeasurement(LogicBase):
    """

    """
    send_controls_signal = QtCore.Signal(list, list, list)
    is_computed: bool = False
    fom: float = None

    def __init__(self, config, **kwargs):
        """Initialize the base class"""
        super().__init__(config=config, **kwargs)
        return

    def on_activate(self):
        pass

    def on_deactivate(self):
        pass

    def test(self):
        print("It is just a test")

    @QtCore.Slot(float)
    def update_FoM(self, fom) -> None:
        self.fom = fom
        self.is_computed = True

    def get_FoM(self, pulses, parameters, timegrids) -> dict:
        """
        Module for figure of merit evaluation

        Returns
        -------

        """
        self.send_controls_signal.emit(pulses, parameters, timegrids)
        while not self.is_computed:
            time.sleep(0.01)
        self.is_computed = False

        return {"FoM": self.fom}
