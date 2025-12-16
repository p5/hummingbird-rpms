# Copyright (c) 2006 Red Hat, Inc. All rights reserved. This copyrighted material
# is made available to anyone wishing to use, modify, copy, or
# redistribute it subject to the terms and conditions of the GNU General
# Public License v.2.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
# PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# Author: Radek Biba <rbiba@redhat.com>

import sys
import uuid

UMASK = "Running umask"

sys.path.append("..")

from tests import BaseZipTests
from tests import decorated_message

PURPOSE = '''
zip is supposed to honor umask settings when creating archives.
This test case just checks if it really does

TEST UPDATED (esakaiev)
'''


class TestUmask(BaseZipTests):
    """
        This class is used for providing functionality
        for TestUmask test case
    """
    def __init__(self):
        self._purpose = PURPOSE
        super(TestUmask, self).__init__()

        self._tmpdir = "/tmp/{}".format(uuid.uuid4())
        self._mask_list = ["0", "2", "20", "22", "200", "202", "220", "222", "6", "60"]
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

    # Trying to verify that zip honors umask. Trying with various combinations
    # of 'w's and 'r's for User, Group, and Others.
    @decorated_message("Starting Test cases")
    def start_test(self):
        """

        :return:
        """
        for mask in self._mask_list:
            self.logger.debug("Running umask and zipping file {0}".format(mask))
            self.execute_cmd("umask {0}; touch {0}; zip -q {0}.zip {0}".format(mask), cwd=self._tmpdir)

            stat_test_zip = self.execute_cmd("stat -c %a {0}.zip".format(mask), cwd=self._tmpdir).replace("\n", "")
            stat_test = self.execute_cmd("stat -c %a {0}".format(mask), cwd=self._tmpdir).replace("\n", "")

            print stat_test_zip, stat_test
            if stat_test_zip == stat_test:
                self.logger.debug(
                    "PASS ] :: [ permissions for {0}.zip match to {0}, {1} == {2}".format(mask, stat_test_zip,
                                                                                          stat_test))
            else:
                self.logger.debug(
                    "FAIL ] :: [ permissions for {0}.zip doesn't match to {0}, {1} != {2}".format(mask, stat_test_zip,
                                                                                                  stat_test))

    @decorated_message("Cleaning up")
    def cleanup(self):
        """

        :return:
        """
        self.remove_file(self._tmpdir, True)


if __name__ == "__main__":
    test = TestUmask()
    try:
        test.prepare_setup()
        test.start_test()
    except AssertionError, exp:
        test.logger.debug("FAIL ] :: [ Assertion occurred {0}".format(exp))
    except Exception, exp:
        test.logger.debug("FAIL ] :: [ Exception occurred {0}".format(exp))
    finally:
        test.cleanup()
