# python2 test_big_file_in_archive.py
# Author: Josef Zila <jzila@redhat.com>
# Location: CoreOS/zip/Functionality/stress-tests/big-file-in-archive/runtest.sh
# Description: zip - tests handling large files (2GB,3MB,4GB)

# Copyright (c) 2008 Red Hat, Inc. All rights reserved. This copyrighted material
# is made available to anyone wishing to use, modify, copy, or
# redistribute it subject to the terms and conditions of the GNU General
# Public License v.2.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
# PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.

# Include rhts and rhtslib environment
# rpm -q --quiet rhtslib || rpm -Uvh http://nest.test.redhat.com/mnt/qa/scratch/pmuller/rhtslib/rhtslib.rpm

import sys
import uuid
import platform

sys.path.append("..")

from tests import BaseZipTests
from tests import decorated_message

PURPOSE = '''
Test Name: Big file in archive
Author: Josef Zila <jzila@redhat.com>
Location: CoreOS/zip/Functionality/stress-tests/big-file-in-archive/PURPOSE

Short Description:
Tests handling large files (2GB,3GB,4GB)

Long Description:
Test creates three files (2GB, 3GB and 4GB large) and attempts to archive each of them using zip. Then original files are deleted
and archives are unpacked, to check size of unpacked files. Current version of zip on all archs and distros in time of
writing(2.31-1) passes test. Note: 4GB file is too large for zip to handle, so it is not supposed to be successfully archived
or unpacked, test just checks for correct return codes.


how to run it:
python2 test_big_file_in_archive.py

TEST UPDATED (esakaiev)
------------------------
After rebase to zip-3.0-1 there is no 4GB limit. Patching the test accordingly.
'''


class TestBigFileInArchive(BaseZipTests):
    """
        This class is used for providing functionality
        for TestBigFileInArchive test case
    """
    def __init__(self):
        """

        """
        self._purpose = PURPOSE
        super(TestBigFileInArchive, self).__init__()

        self._files = ['/tmp/tmp.{}'.format(uuid.uuid4()) for x in xrange(3)]
        self._files_sizes = [2048, 3056, 4096]
        self._os_distribution = platform.linux_distribution()

    @decorated_message("Preparing Setup")
    def prepare_setup(self):
        """

        :return:
        """
        self.check_package()
        for i, file_name in enumerate(self._files):
            size = self._files_sizes[i]
            assert self.run_cmd("dd if=/dev/zero of={0} bs=1M count={1}".format(file_name, size), 0,
                                "Creating {0} GB file".format(size / 1000), cwd="/tmp/") == 0

    @decorated_message("Starting Test")
    def start_test(self):
        """

        :return:
        """
        for i, file_name in enumerate(self._files):
            error_code = 0

            self.remove_file(file_name + ".zip")  # #remove archive temp files, we just need unused temp names
            size = self._files_sizes[i]

            self.run_cmd("zip {0} {1}".format(file_name + ".zip", file_name), error_code,
                         "Archiving {} Gb file".format(size / 1000), cwd="/tmp/")

            self.remove_file(file_name)  # Removing original files

            self.run_cmd("unzip {0} -d /".format(file_name + ".zip"), error_code,
                         "Unpacking {} Gb file".format(size / 1000), cwd="/tmp/")

        # Checking new 2GB file size
        self.check_output("stat -c %s {0}".format(self._files[0]), "2147483648\n", "Checking new 2GB file size")

    @decorated_message("Cleaning up")
    def cleanup(self):
        """

        :return:
        """
        for file_name in self._files:
            self.remove_file(file_name)
            self.remove_file(file_name + ".zip")


if __name__ == "__main__":
    test = TestBigFileInArchive()
    try:
        test.prepare_setup()
        test.start_test()
    except AssertionError, exp:
        test.logger.debug("FAIL ] :: [ Assertion occurred {0}".format(exp))
    except Exception, exp:
        test.logger.debug("FAIL ] :: [ Exception occurred {0}".format(exp))
    finally:
        test.cleanup()
