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
import os
try:
    from PyQt4.QtGui import QWidget, QHBoxLayout, QPushButton, QInputDialog, QLineEdit
    from PyQt4.QtCore import pyqtSlot
except ImportError:
    from PyQt5.QtWidgets import QWidget, QHBoxLayout, QPushButton, QInputDialog, QLineEdit
    from PyQt5.QtCore import pyqtSlot
from transphire.passworddialog import PasswordDialog
from transphire import transphire_utils as tu


class MountWidget(QWidget):
    """
    MountWidget widget.

    Inherits from:
    QWidget

    Buttons:
    mount_button - Mount mount point
    umount_button - Umount mount point

    Signals:
    None
    """

    def __init__(self, content, mount_worker, parent=None):
        """
        Setup the layout for the widget

        Arguments:
        content - Mount content
        mount_worker - Worker thread instance.
        parent - Parent widget (default None)

        Return:
        None
        """
        super(MountWidget, self).__init__(parent)

        # Global content
        self.content = content
        self.name = content['Mount name'][0]
        self.ip_adress = content['IP'][0]
        self.typ = content['Typ'][0]
        self.default_user = content['Default user'][0]
        self.sec = content['sec'][0]
        self.gid = content['gid'][0]
        self.domain = content['Domain'][0]
        self.protocol = content['Protocol'][0]
        self.folder = content['Folder'][0]
        self.extension = bool(content['Need folder extension?'][0] == 'True')
        self.version = content['Protocol version'][0]
        self.ssh_address = content['SSH address'][0]
        self.quota_command = content['Quota command'][0]
        self.right_quota = content['Is df giving the right quota?'][0]
        self.quota = content['Quota / TB'][0]
        self.login = content['Target UID exists here and on target?'][0]
        self.mount_folder = self.name.replace(' ', '_')
        self.mount_worker = mount_worker
        self.thread_object = None

        # Content
        self.mount_button = QPushButton('{0}'.format(self.name), self)
        self.mount_button.setObjectName('mount')
        self.umount_button = QPushButton('{0}'.format(self.name), self)
        self.umount_button.setObjectName('mount')

        # Layout
        layout = QHBoxLayout(self)
        layout.addWidget(self.mount_button)
        layout.addWidget(self.umount_button)
        layout.setContentsMargins(0, 0, 0, 0)

        # events
        self.mount_button.clicked.connect(self.mount)
        self.umount_button.clicked.connect(self.umount)

    def set_thread_object(self, thread_object):
        """
        Set the thread object.

        thread_object - Thread object to set.

        Returns:
        None
        """
        self.thread_object = thread_object

    def get_settings(self):
        """
        Return settings of the content.

        Arguments:
        None

        Returns:
        Settings as dictionary
        """
        settings = {}
        for key in self.content:
            settings[key] = self.content[key][0]
        return settings

    @pyqtSlot()
    def mount(self):
        """
        Mount device preparation

        Arguments:
        None

        Return:
        None
        """
        # Mount external hdd
        if self.typ == 'Copy_hdd':
            self.mount_worker.sig_mount_hdd.emit(self.mount_folder)
        else:
            user, password, folder = self._check_user(
                login=bool(self.login == 'True')
                )
            if user:
                self.mount_worker.sig_mount.emit(
                    self.mount_folder,
                    user,
                    password,
                    folder,
                    self.ip_adress,
                    self.protocol,
                    self.domain,
                    self.version,
                    self.sec,
                    self.gid,
                    )
            else:
                print('Wrong identity')
                tu.message('Wrong identity, check command line for more information')

    @pyqtSlot()
    def umount(self):
        """
        Umount device signal preparation

        Arguments:
        None

        Return:
        None
        """
        if self.typ == 'Copy_hdd':
            hdd_folder = '{0}/{1}'.format(
                self.mount_worker.mount_directory,
                self.mount_folder
                )
            if not os.path.exists(hdd_folder):
                self.mount_worker.sig_info.emit(
                    'First mount {0}'.format(self.mount_folder)
                    )
                return None
            else:
                pass

            folders = os.listdir(hdd_folder)
            hdd_name = self._specify_hdd()
            if hdd_name is None:
                return None
            else:
                hdd_name = hdd_name.replace(' ', '_').upper()

            if hdd_name == 'ALL':
                for entry in folders:
                    self.mount_worker.sig_umount.emit(
                        self.mount_folder,
                        entry,
                        self.thread_object
                        )
            elif hdd_name.startswith('HDD_'):
                if hdd_name in folders:
                    self.mount_worker.sig_umount.emit(
                        self.mount_folder,
                        hdd_name,
                        self.thread_object
                        )
                else:
                    tu.message('{0} is not mounted!'.format(hdd_name))
            else:
                print('Unmount hdd: Unreachable code')
                print(hdd_name, self.mount_folder, folders)

        else:
            self.mount_worker.sig_umount.emit(
                self.mount_folder,
                self.mount_folder,
                self.thread_object
                )

    def _check_user(self, login):
        """
        Check if the user is allowed to mount

        Arguments:
        login - Try to login as user on this machine

        Return:
        Username, User password, Mount folder
        """
        dialog = PasswordDialog(
            folder=self.folder,
            default=self.default_user,
            login=login,
            extension=self.extension,
            parent=self
            )
        dialog.exec_()
        if dialog.result():
            return dialog.username, dialog.password, dialog.folder
        else:
            return False, False, False

    def _specify_hdd(self):
        """
        Specify which HDD to unmount.

        Arguments:
        None

        Return:
        HDD text
        """
        text, result = QInputDialog().getText(
            self,
            'Specify hdd',
            'choose hdd to unmount,\n"all" will unmount all mounted hdd\'s',
            QLineEdit.Normal,
            'all'
            )
        if result:
            text = text.lower()
            if text.startswith('hdd_'):
                return text
            elif text.startswith('hdd '):
                return text
            elif text == 'all':
                return text
            else:
                tu.message('Input needs to be "all" or "hdd_{number}" or "hdd {number}')
                return None
        else:
            tu.message('Input needs to be "all" or "hdd_{number} or "hdd {number}"')
            return None
