# Author: Josef Zila <jzila@redhat.com>
# Location: CoreOS/zip/Functionality/stress-tests/many-files-in-archive/runtest.sh
# Description: zip - Tests behaviour with many files in archive (1048578 files)

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

sys.path.append("..")

from tests import BaseZipTests
from tests import decorated_message

PURPOSE = '''
Test Name: 
Author: Josef Zila <jzila@redhat.com>
Location: CoreOS/zip/Functionality/stress-tests/many-files-in-archive/PURPOSE

Short Description:
Tests behaviour with many files in archive (1048577 files)

Long Description:
This test creates 1048576 empty files and one non-empty file. Then zips and unzips directory containing all those files and tests content of 
non-empty file and count of unzipped files. This test is very time-consuming. Current version of zip on all archs and distros in time of writing
(2.31-1) passes test.


how to run it:
choose arch and distro


TEST UPDATED (esakaiev)
'''


class TestManyFilesInArchive(BaseZipTests):
    """
        This class is used for providing functionality
        for TestManyFilesInArchive test case
    """

    def __init__(self):
        self._purpose = PURPOSE
        super(TestManyFilesInArchive, self).__init__()

        self._tmpdir = "/tmp/{}".format(uuid.uuid4())
        self._files_number = 1048576
        self._package_ver = ""
        self._package_release = ""

    @decorated_message("Prepare setup")
    def prepare_setup(self):
        """

        :return:
        """
        self.check_package()

        self.run_cmd("mkdir {}".format(self._tmpdir), 0,
                     "Creating tmp directory {}".format(self._tmpdir))
        self._package_ver = self.execute_cmd("rpm -q zip --queryformat %{version}")
        self._package_release = self.execute_cmd("rpm -q zip --queryformat %{version}")

        self.logger.debug("Running zip.{0}.{1} package".format(self._package_ver, self._package_release))
        self.logger.debug("Creating {0} files".format(self._files_number))

        [open("{0}/{1}".format(self._tmpdir, i), "w").close() for i in xrange(self._files_number)]
        self.logger.debug("Creating test file")
        with open("{0}/test.txt".format(self._tmpdir), "w") as fp:
            fp.write("12345")

    @decorated_message("Starting Test cases")
    def start_test(self):
        """

        :return:
        """

        self.run_cmd("zip -r test {0} -q".format(self._tmpdir.split('/')[-1]), 0,
                     "Zipping test files",
                     cwd='/tmp')

        self.remove_file(self._tmpdir, True)
        self.run_cmd("unzip -qq test.zip", 0,
                     "Unzipping test files",
                     cwd='/tmp')

        test_file_content = None
        with open("{0}/test.txt".format(self._tmpdir)) as fp:
            test_file_content = fp.read().replace('/n', '')

        if test_file_content == "12345":
            self.logger.debug("PASS ] :: [ {}".format("Unpacked content matches original"))
        else:
            self.logger.debug("FAIL ] :: [ {}".format("Unpacked content does not match original!"))

        files_count = self.execute_cmd("ls {0} | wc -l".format(self._tmpdir)).replace("\n", "")

        if files_count == str(self._files_number + 1):
            self.logger.debug(
                "PASS ] :: [ {}".format("All {0} files present after unpacking".format(self._files_number + 1)))
        else:
            self.logger.debug(r"FAIL ] :: [ File count changed after unpacking! \
                                           Before zipping there was {0} files. \
                                           After unzip there is {1} files.".format(self._files_number + 1, files_count))

    @decorated_message("Cleaning up")
    def cleanup(self):
        """

        :return:
        """
        self.remove_file(self._tmpdir, True)
        self.remove_file("/tmp/test.zip")


if __name__ == "__main__":
    test = TestManyFilesInArchive()
    try:
        test.prepare_setup()
        test.start_test()
    except AssertionError, exp:
        test.logger.debug("FAIL ] :: [ Assertion occurred {0}".format(exp))
    except Exception, exp:
        test.logger.debug("FAIL ] :: [ Exception occurred {0}".format(exp))
    finally:
        test.cleanup()
