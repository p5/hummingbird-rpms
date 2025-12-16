# Author: Josef Zila <jzila@redhat.com>

# Description:  Zip did not honor umask setting when creating archives.

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

UMASK = "Running umask"

sys.path.append("..")

from tests import BaseZipTests
from tests import decorated_message

PURPOSE = '''
Test Name: umask-when-creating
Author: Josef Zila <jzila@redhat.com>

Short Description:
zip does not honor umaks setting when creating archive

Long Description:

zip appears to have a built-in umask of 0022 regardless of the global umask.
With umask set to 0000, zip-2.3-27 creates zip files with permissions of
0644 instead of 0666.  Previous versions created files with correct permissions.


TEST UPDATED (esakaiev)
'''


class TestUmaskWhenCreating(BaseZipTests):
    """
        This class is used for providing functionality
        for TestUmaskWhenCreating test case
    """
    def __init__(self):
        self._purpose = PURPOSE
        super(TestUmaskWhenCreating, self).__init__()

        self._tmpdir = "/tmp/{}".format(uuid.uuid4())
        self._mask_list = ["777", "000", "027"]
        self._expected_results = ["----------", "-rw-rw-rw-", "-rw-r-----"]
        self._package_ver = ""
        self._package_release = ""

    @decorated_message("Prepare setup")
    def prepare_setup(self):
        self.check_package()

        self.run_cmd("mkdir {}".format(self._tmpdir), 0, "Creating tmp directory {}".format(self._tmpdir))
        self._package_ver = self.execute_cmd("rpm -q zip --queryformat %{version}")
        self._package_release = self.execute_cmd("rpm -q zip --queryformat %{version}")

        self.logger.debug("Running zip.{0}.{1} package".format(self._package_ver, self._package_release))

    @decorated_message("Starting Test cases")
    def start_test(self):
        for i, mask in enumerate(self._mask_list):
            self.logger.debug("Running umask and zipping file {0}".format(mask))
            self.execute_cmd("umask -S {0} >> /dev/null; zip test /etc/services >> /dev/null".format(mask),
                             cwd=self._tmpdir)

            result = self.execute_cmd("ls -l test.zip | cut -b 1-10", cwd=self._tmpdir).replace("\n", "")

            if result == self._expected_results[i]:
                self.logger.debug(
                    "PASS ] :: [ file permissions match to {0}".format(self._expected_results[i]))
            else:
                self.logger.debug(
                    "FAIL ] :: [ file permissions don't match to {0}".format(self._expected_results[i]))

            self.remove_file(self._tmpdir + "/" + "test.zip")

    @decorated_message("Cleaning up")
    def cleanup(self):
        self.remove_file(self._tmpdir, True)


if __name__ == "__main__":
    test = TestUmaskWhenCreating()
    try:
        test.prepare_setup()
        test.start_test()
    except AssertionError, exp:
        test.logger.debug("FAIL ] :: [ Assertion occurred {0}".format(exp))
    except Exception, exp:
        test.logger.debug("FAIL ] :: [ Exception occurred {0}".format(exp))
    finally:
        test.cleanup()
