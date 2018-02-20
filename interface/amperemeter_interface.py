# -*- coding: utf-8 -*-

"""
Interface file for simple data acquisition.

Qudi is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Qudi is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Qudi. If not, see <http://www.gnu.org/licenses/>.

Copyright (c) the Qudi Developers. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at <https://github.com/Ulm-IQO/qudi/>
"""

import abc
from core.util.interfaces import InterfaceMetaclass


class AmperemeterInterface(metaclass=InterfaceMetaclass):

    _modtype = 'AmperemeterInterface'
    _modclass = 'interface'

    @abc.abstractmethod
    def get_value(self):
        """ Return a measured value """
        pass

    @abc.abstractmethod
    def get_device_status(self):
        """ Returns if the device is ready """
        pass
