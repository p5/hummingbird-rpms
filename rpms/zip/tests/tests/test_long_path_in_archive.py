# Author: Josef Zila <jzila@redhat.com>
# Location: CoreOS/zip/Functionality/stress-tests/long-path-in-archive/runtest.sh
# Description: zip - tests handling very long paths within archive (15*256 characters long path)

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

import sys
import uuid
import os
from shutil import copyfile

sys.path.append("..")

from tests import BaseZipTests
from tests import decorated_message

PURPOSE = '''
Test Name: 
Author: Josef Zila <jzila@redhat.com>
Location: CoreOS/zip/Functionality/stress-tests/long-path-in-archive/PURPOSE

Short Description:
Tests handling very long paths within archive (15*256 characters long path)

Long Description:
This test creates file with very long path of 15 directories, each 255 characters. This whole directory structure is then zipped and unzipped
to determine if zip program handles paths this long correctly. Current version of zip on all archs and distros in time of writing(2.31-1) passes test.


how to run it:
choose arch and distro


TEST UPDATED (esakaiev)
'''


class TestLongPathInArchive(BaseZipTests):
    """
        This class is used for providing functionality
        for TestLongPathInArchive test case
    """
    def __init__(self):
        self._purpose = PURPOSE
        super(TestLongPathInArchive, self).__init__()

        self._tmpdir = "/tmp/{}".format(uuid.uuid4())
        self._file_under_test = "/proc/version"

        self._long_name = "".join(["aaaaa" for i in xrange(51)])
        self._long_path = "/".join([self._long_name for x in xrange(15)])
        self._test_file_path = self._tmpdir + "/" + self._long_path + "/" + "testfile"
        self._package_ver = ""
        self._package_release = ""

    @decorated_message("Prepare setup")
    def prepare_setup(self):
        """

        :return:
        """
        self.check_package()

        self.run_cmd("mkdir {}".format(self._tmpdir), 0, "Creating tmp directory {}".format(self._tmpdir))
        self._package_ver = self.execute_cmd("rpm -q zip --queryformat %{version}")
        self._package_release = self.execute_cmd("rpm -q zip --queryformat %{version}")

        self.logger.debug("Running zip.{0}.{1} package".format(self._package_ver, self._package_release))
        # creating folders structure:
        try:

            os.makedirs(self._tmpdir + "/" + self._long_path)
            self.logger.debug("PASS ] :: [ Test directory with long path has been successfully created")
        except OSError, exp:
            self.logger.debug("FAIL ] :: [ Could not create directories by path, e: {}".format(exp))
            raise

        copyfile(self._file_under_test, self._test_file_path)

    @decorated_message("Starting Test cases")
    def start_test(self):
        """

        :return:
        """

        self.run_cmd("zip -r test {0} -q".format(self._long_name), 0,
                     "Zipping test file",
                     cwd=self._tmpdir)

        self.remove_file(self._tmpdir + "/" + self._long_name, True)
        self.run_cmd("unzip -qq test.zip", 0,
                     "Unzipping test file",
                     cwd=self._tmpdir)

        content_init = None
        with open(self._file_under_test) as fp_init:
            content_init = fp_init.read().replace('\n', '')

        content_fut = None
        with open(self._test_file_path) as fp_fut:
            content_fut = fp_fut.read().replace('\n', '')

        if content_init == content_fut:
            self.logger.debug("PASS ] :: [ {}".format("Content of the initial file and file under test was matched"))
        else:
            self.logger.debug("FAIL ] :: [ {}".format("Content of the initial file and file under test wasn't matched"))

    @decorated_message("Cleaning up")
    def cleanup(self):
        """

        :return:
        """
        self.remove_file(self._tmpdir, True)


if __name__ == "__main__":
    test = TestLongPathInArchive()
    try:
        test.prepare_setup()
        test.start_test()
    except AssertionError, exp:
        test.logger.debug("FAIL ] :: [ Assertion occurred {0}".format(exp))
    except Exception, exp:
        test.logger.debug("FAIL ] :: [ Exception occurred {0}".format(exp))
    finally:
        test.cleanup()
