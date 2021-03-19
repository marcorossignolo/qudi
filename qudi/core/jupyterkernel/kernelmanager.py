# -*- coding: utf-8 -*-
"""
IPython compatible kernel launcher module

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

import weakref
import logging
import numpy as np
import IPython

from PySide2 import QtCore

from qudi.util.mutex import RecursiveMutex
from qudi.util.network import netobtain

from traitlets.config import Config
from qudi.core.jupyterkernel.qzmqkernel import QZMQKernel


class JupyterKernelManager(QtCore.QObject):
    """ Singleton class providing Jupyter-compatible kernels connected via ZMQ.
    """
    _instance = None
    _lock = RecursiveMutex()

    # _kernel_shutdown_timeout = 5

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None or cls._instance() is None:
                obj = super().__new__(cls, *args, **kwargs)
                cls._instance = weakref.ref(obj)
                return obj
            raise RuntimeError(
                'Only one JupyterKernelManager instance per process possible (Singleton). Please '
                'use JupyterKernelManager.instance() to get a reference to the already created '
                'instance.'
            )

    def __init__(self, *args, qudi_main, **kwargs):
        """ Create logic object
        """
        super().__init__(*args, **kwargs)
        self.log = logging.getLogger('jupyter-kernel-manager')
        self.kernels = dict()
        self.namespace_modules = set()
        self._qudi_main = weakref.ref(qudi_main, self.terminate)
        qudi_main.module_manager.sigManagedModulesChanged.connect(self.update_module_namespace)
        qudi_main.module_manager.sigModuleStateChanged.connect(
            self.update_namespace_on_module_state_change)

    @classmethod
    def instance(cls):
        with cls._lock:
            if cls._instance is None:
                return None
            return cls._instance()

    def terminate(self):
        with self._lock:
            JupyterKernelManager._instance = None
            # Stop kernels and wait for them to shut down
            for k in tuple(self.kernels):
                self.stop_kernel(k, blocking=True)
            # start = time.time()
            # while self.kernels:
            #     if time.time() - start > self._kernel_shutdown_timeout:
            #         self.log.warning('Shutting down all qudi kernels timed out.')
            #         break
            #     # QtCore.QCoreApplication.processEvents()
            #     time.sleep(0.1)
            # Disconnect signals
            try:
                qudi_main = self._qudi_main()
                if qudi_main is None:
                    return
                qudi_main.module_manager.sigManagedModulesChanged.disconnect(
                    self.update_module_namespace)
                qudi_main.module_manager.sigModuleStateChanged.disconnect(
                    self.update_namespace_on_module_state_change)
            except:
                pass

    def start_kernel(self, config, external=None):
        """ Start a qudi inprocess jupyter kernel.

        @param dict config: connection information for kernel
        @param callable external: function to call on exit of kernel

        @return str: uuid of the started kernel
        """
        with self._lock:
            qudi_main = self._qudi_main()
            if qudi_main is None:
                self.log.critical('Unexpected Qudi main instance weakref.')
                return
            config = netobtain(config)
            self.log.debug('Starting new kernel with config: {0}'.format(config))

            # First create a config object from the traitlets library
            c = Config()

            # Now we can set options as we would in a config file:
            #   c.Class.config_value = value

            c.ConnectionFileMixin.control_port = config.get('control_port', 0)
            c.ConnectionFileMixin.hb_port = config.get('hb_port', 0)
            c.ConnectionFileMixin.shell_port = config.get('shell_port', 0)
            c.ConnectionFileMixin.iopub_port = config.get('iopub_port', 0)
            c.ConnectionFileMixin.stdin_port = config.get('stdin_port', 0)
            c.ConnectionFileMixin.transport = config.get('transport', 'tcp')
            c.Session.key = config.get('stdin_port', 0)
            c.Session.signature_scheme = config.get('signature_scheme', 0)

            # c.InteractiveShellApp.exec_lines = [
            #     'print("importing numpy")',
            #     'import numpy as np',
            # ]
            # c.InteractiveShell.colors = 'LightBG'
            # c.InteractiveShell.confirm_exit = False
            # c.TerminalIPythonApp.display_banner = False

            kernel = IPython.embed_kernel(config=c)
            print('IPython kernel', kernel.engine_id, kernel)
            return kernel.engine_id
            # kernel = QZMQKernel(config)
            if kernel.engine_id in self.kernels:
                self.log.error('Kernel with ID {0} already created in QudiKernelLogic. '
                               'Ignoring call to start_kernel.')
                return
            kernel_thread = qudi_main.thread_manager.get_new_thread(
                'kernel-{0}'.format(kernel.engine_id))
            kernel.moveToThread(kernel_thread)
            kernel.user_global_ns.update({'np': np,
                                          'config': qudi_main.configuration.config_dict,
                                          'qudi': qudi_main})
            kernel.sigShutdownFinished.connect(self.cleanup_kernel)
            kernel_thread.start()
            QtCore.QMetaObject.invokeMethod(
                kernel, 'connect_kernel', QtCore.Qt.BlockingQueuedConnection)
            self.kernels[kernel.engine_id] = kernel
            self.update_module_namespace()
            self.log.info('Finished starting Kernel {0}'.format(kernel.engine_id))
            return kernel.engine_id

    def stop_kernel(self, kernel_id, blocking=False):
        """ Tell kernel to close all sockets and stop heartbeat thread.

        @param str kernel_id: uuid of kernel to be stopped
        @param bool blocking: Whether this method should wait until the kernel is stopped or not
        """
        with self._lock:
            kernel_id = netobtain(kernel_id)
            kernel = self.kernels.get(kernel_id, None)
            if kernel is None:
                self.log.error('No kernel with ID {0} registered.'.format(kernel_id))
                return
            self.log.info('Stopping kernel {0}'.format(kernel_id))
            if blocking:
                kernel.sigShutdownFinished.disconnect(self.cleanup_kernel)
                QtCore.QMetaObject.invokeMethod(
                    kernel, 'shutdown', QtCore.Qt.BlockingQueuedConnection)
                self.cleanup_kernel(kernel_id)
            else:
                QtCore.QMetaObject.invokeMethod(kernel, 'shutdown')

    def cleanup_kernel(self, kernel_id, external=None):
        """Remove kernel reference and tell rpyc client for that kernel to exit.

        @param str kernel_id: uuid of kernel reference to remove
        @param callable external: reference to rpyc client exit function
        """
        self.log.info('Cleaning up kernel {0}'.format(kernel_id))
        self.kernels.pop(kernel_id, None)
        qudi_main = self._qudi_main()
        if qudi_main is not None:
            qudi_main.thread_manager.quit_thread('kernel-{0}'.format(kernel_id))
        if external is not None:
            try:
                external.exit()
            except:
                self.log.warning('External qudikernel starter did not exit')

    @QtCore.Slot()
    @QtCore.Slot(dict)
    def update_module_namespace(self, managed_modules=None):
        """ Remove non-existing modules from namespace, add new modules to namespace, update
        reloaded modules

        @param dict managed_modules: configured module names with their respective ManagedModule
                                     instances
        """
        with self._lock:
            if managed_modules is None:
                managed_modules = self._qudi_main().module_manager.modules

            # Collect all active module instances in a dict with their respective configured names
            new_namespace = {mod_name: mod.instance for mod_name, mod in managed_modules.items() if
                             mod.is_active}
            new_namespace_set = set(new_namespace)
            # Determine modules to discard from namespace
            discard = self.namespace_modules - new_namespace_set
            if not new_namespace_set and not discard:
                return
            # iterate through all kernels and update namespace
            for kernel_id in self.kernels:
                self._update_kernel_module_namespace(kernel_id, new_namespace, discard)
            # Remember module names of new namespace
            self.namespace_modules = new_namespace_set

    def _update_kernel_module_namespace(self, kernel_id, new_namespace, discard=None):
        """ Helper method to update the namespace of a single kernel
        """
        if discard is None:
            discard = tuple()
        kernel = self.kernels.get(kernel_id, None)
        if kernel is None:
            self.log.error('No kernel with ID {0} registered.'.format(kernel_id))
            return

        kernel.user_global_ns.update(new_namespace)
        for name in discard:
            kernel.user_global_ns.pop(name, None)
        return

    @QtCore.Slot(str, str, str)
    def update_namespace_on_module_state_change(self, base, name, state):
        with self._lock:
            if state in ('deactivated', 'BROKEN'):
                instance = None
                if name in self.namespace_modules:
                    self.namespace_modules.remove(name)
            else:
                qudi_main = self._qudi_main()
                if qudi_main is None:
                    return
                instance = qudi_main.module_manager[name].instance
                self.namespace_modules.add(name)
            for kernel_id in self.kernels:
                self._update_kernel_module_state(kernel_id, name, instance)

    def _update_kernel_module_state(self, kernel_id, module_name, instance):
        """ Helper method to update the namespace of a single kernel
        """
        kernel = self.kernels.get(kernel_id, None)
        if kernel is None:
            self.log.error('No kernel with ID {0} registered.'.format(kernel_id))
            return
        if instance is None:
            kernel.user_global_ns.pop(module_name, None)
        else:
            kernel.user_global_ns[module_name] = instance
