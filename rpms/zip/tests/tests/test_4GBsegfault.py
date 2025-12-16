# Copyright (c) 2018 Red Hat, Inc. All rights reserved. This copyrighted material
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
# Author: Eduard Sakaiev <esakaiev@redhat.com>

import sys
import uuid

sys.path.append("..")

from tests import BaseZipTests
from tests import decorated_message

PURPOSE = '''zip mustn't segfault when packing files larger than 4 GB.

Note: this test can't run on RHEL 2.1 since the utilities used here
in the test don't work there as expected. This test can't run on
RHEL 5 either, but in this case, the reason is reworked zip which
can't work with files larger than 4 GB at all.'''


class Test4GBsegfault(BaseZipTests):
    """
        This class is used for providing functionality
        for Test4GBsegfault test case
    """

    def __init__(self):
        """

        """
        self._purpose = PURPOSE
        super(Test4GBsegfault, self).__init__()

        self._tmpdir = "/tmp/{}".format(uuid.uuid4())

    @decorated_message("SETUP")
    def prepare_setup(self):
        """

        :return:
        """
        self.check_package()

        self.run_cmd("mkdir {}".format(self._tmpdir), 0,
                     "Creating tmp directory {}".format(self._tmpdir))

    @decorated_message("TEST")
    def start_test(self):
        """

        :return:
        """
        self.run_cmd("dd if=/dev/zero of=testfile bs=1M count=4097", 0,
                     "Creating of 4Gb file", self._tmpdir + "/")
        self.run_cmd("zip testfile.zip testfile", 0,
                     "Archiving file with zip", self._tmpdir + "/")

    @decorated_message("CLEANUP")
    def cleanup(self):
        """

        :return:
        """
        self.run_cmd("rm -r {}".format(self._tmpdir), 0,
                     "Removing tmp directory")


if __name__ == "__main__":
    test_4gb = Test4GBsegfault()
    try:
        test_4gb.prepare_setup()
        test_4gb.start_test()
    except AssertionError, exp:
        test_4gb.logger.debug("FAIL ] :: [ Assertion occurred {0}".format(exp))
    except Exception, exp:
        test_4gb.logger.debug("FAIL ] :: [ Exception occurred {0}".format(exp))
    finally:
        test_4gb.cleanup()
