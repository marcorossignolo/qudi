"""
TODO QUDI License here
Gui class for the optimization suite
"""

# from qudi.gui.guibase import GUIBase
from qudi.core.module import GuiBase
from qudi.core.connector import Connector

from quocspyside2interface.gui.OptimizationBasicGui import OptimizationBasicGui


class OptimizationGUI(GuiBase, OptimizationBasicGui):
    """
    TODO Explain what happens here
    """
    # Optimal Control
    optimizationlogic = Connector(interface="OptimizationLogic")

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

    def on_activate(self):
        """Creates all the ui elements"""
        # Redefine the optimizationlogic variable to be recognized by the OptimizationBasicGUI class
        self.optimizationlogic = self.optimizationlogic()

        self.handle_ui_elements()
        return 0


    def on_deactivate(self):
        ## TODO Disconnect signals?
        self._mw.close()
        return 0

    def show(self):
        self._mw.show()
        self._mw.activateWindow()
        self._mw.raise_()
