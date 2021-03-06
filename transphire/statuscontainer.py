"""
    TranSPHIRE is supposed to help with the cryo-EM data collection
    Copyright (C) 2017 Markus Stabrin

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
try:
    from PyQt4.QtGui import QHBoxLayout, QVBoxLayout, QWidget, QLabel
    from PyQt4.QtCore import pyqtSlot, pyqtSignal
except ImportError:
    from PyQt5.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget, QLabel
    from PyQt5.QtCore import pyqtSlot, pyqtSignal
from transphire.statuswidget import StatusWidget
from transphire.separator import Separator
from transphire import transphire_utils as tu


class StatusContainer(QWidget):
    """
    Container for status widgets

    Inherits:
    QWidget

    Signals:
    sig_refresh_quota - Connected to change the quota text (no object)
    """
    sig_refresh_quota = pyqtSignal()

    def __init__(self, content, content_mount, content_pipeline, mount_worker, process_worker, parent=None, **kwargs):
        """
        Layout for the status container.

        Arguments:
        content - Content to fill the statuscontainer
        content_mount - Content for the mount points
        content_pipeline - Content for the pipeline settings
        mount_worker - MountWorker object
        process_worker - ProcessWorker object
        parent - Parent widget (default None)

        Returns:
        None
        """
        super(StatusContainer, self).__init__(parent)

        # Layout
        layout_v1 = QVBoxLayout(self)
        layout_v1.setContentsMargins(0, 0, 0, 0)

        for entry in content:
            for widget in entry:
                for key in widget:
                    if key == 'Image':
                        image = widget[key][0]

        # Global content
        self.content = {}

        # Add em-transfer quota
        self.content['scratch'] = StatusWidget(name='scratch', default_name='Connected', default_quota='-- / --')
        layout_v1.addWidget(self.content['scratch'])

        # Add em-transfer quota
        self.content['project'] = StatusWidget(name='project', default_name='Connected', default_quota='-- / --')
        layout_v1.addWidget(self.content['project'])

        content_temp = []
        for entry in content_mount:
            content = {}
            for widget in entry:
                for key in widget:
                    content[key] = widget[key]
            content_temp.append(content)

        # Content
        for entry in content_temp:
            key = entry['Mount name'][0]
            if not key:
                continue
            elif key == 'HDD':
                max_iter = 6
            else:
                max_iter = 1
            for i in range(max_iter):
                if max_iter == 1:
                    key_name = key
                    key_device = key.replace(' ', '_')
                else:
                    key_name = '{0} {1}'.format(key, i)
                    key_device = key_name.replace(' ', '_')

                mount_worker.sig_add_save.emit(
                    key_device,
                    entry['SSH address'][0],
                    entry['Quota command'][0],
                    entry['Is df giving the right quota?'][0],
                    entry['Quota / TB'][0]
                    )

                self.content[key_device] = StatusWidget(
                    name=key_name, default_name='Not connected', default_quota='-- / --'
                    )
                layout_v1.addWidget(self.content[key_device])

        # Add a visual separator
        layout_v1.addWidget(Separator(typ='horizontal', color='grey', parent=self))

        # Add process status widgets
        for entry in content_pipeline[0]:
            for key in entry:
                basename = key
                number = int(entry[key][0])
                if number == 1:
                    name = basename
                    self.content[name] = StatusWidget(name=name, default_name='Not running', default_quota='')
                    layout_v1.addWidget(self.content[name])
                else:
                    for idx in range(number):
                        name = '{0}_{1}'.format(basename, idx+1)
                        self.content[name] = StatusWidget(name=name, default_name='Not running', default_quota='')
                        layout_v1.addWidget(self.content[name])

        # Add picture
        pic_label = QLabel(self)
        pic_label.setObjectName('picture')
        pic_label.setStyleSheet('border-image: url("{0}")'.format(image))
        pic_label.setMinimumSize(100, 100)

        small_layout = QHBoxLayout()
        small_layout.addStretch(1)
        small_layout.addWidget(pic_label)
        layout_v1.addStretch(1)
        layout_v1.addLayout(small_layout)

        # Reset quota warning
        mount_worker.quota_warning = True

        # Events
        mount_worker.sig_success.connect(self._mount_success)
        mount_worker.sig_error.connect(self._mount_error)
        mount_worker.sig_info.connect(self._mount_info)
        mount_worker.sig_quota.connect(self.refresh_quota)

        process_worker.sig_status.connect(self._process_success)
        process_worker.sig_error.connect(self._process_error)

        self.sig_refresh_quota.connect(mount_worker.refresh_quota)

    @pyqtSlot(str, str, str)
    def _mount_success(self, text, device, color):
        """
        Mount was successfull.

        Arguments:
        text - Text to show
        device - Device name
        color - Color of the text

        Returns:
        None
        """
        self.content[device].sig_change_info_name.emit(text, color)
        if device != 'scratch' and device != 'project':
            tu.message('{0} Mount/Unmount successfull!'.format(device))
        else:
            pass

    @pyqtSlot(str, str)
    def _mount_error(self, text, device):
        """
        Mount was not successfull

        Arguments:
        text - Text to show
        device - Device name

        Returns:
        None
        """
        if device != 'None':
            self.content[device].sig_change_info_name.emit('Not connected', 'red')
        tu.message(text)

    @staticmethod
    @pyqtSlot(str)
    def _mount_info(text):
        """
        Information for the user

        Arguments:
        text - Text to show

        Returns:
        None
        """
        tu.message(text)

    @pyqtSlot(str, str, str)
    def _process_success(self, text, device, color):
        """
        Success in a process

        Arguments:
        text - Text to show
        device - Device name
        color - Color of the text

        Returns:
        None
        """
        self.content[device].sig_change_info_name.emit(text, color)
        self.sig_refresh_quota.emit()

    @pyqtSlot(str)
    def _process_error(self, text):
        """
        Error in a process

        Arguments:
        text - Text to show

        Returns:
        None
        """
        tu.message(text)
        self.sig_refresh_quota.emit()

    @pyqtSlot(str, str, str)
    def refresh_quota(self, text, device, color):
        """
        Refresh the quota

        Arguments:
        text - Text to show
        device - Device name
        color - Color of the text

        Returns:
        None
        """
        self.content[device].sig_change_info_quota.emit(text, color)
