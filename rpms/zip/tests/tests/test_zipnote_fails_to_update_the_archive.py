# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   Description: zipnote fails to update the archive
#   Author: Karel Volny <kvolny@redhat.com>
#
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   Copyright (c) 2015 Red Hat, Inc.
#
#   This copyrighted material is made available to anyone wishing
#   to use, modify, copy, or redistribute it subject to the terms
#   and conditions of the GNU General Public License version 2.
#
#   This program is distributed in the hope that it will be
#   useful, but WITHOUT ANY WARRANTY; without even the implied
#   warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR
#   PURPOSE. See the GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public
#   License along with this program; if not, write to the Free
#   Software Foundation, Inc., 51 Franklin Street, Fifth Floor,
#   Boston, MA 02110-1301, USA.
#
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

import sys
import uuid

sys.path.append("..")

from tests import BaseZipTests
from tests import decorated_message

PURPOSE = '''
PURPOSE of zipnote-fails-to-update-the-archive
Description: zipnote fails to update the archive
Author: Karel Volny <kvolny@redhat.com>


TEST UPDATED (esakaiev)
'''


class TestZipnoteFailsToUpdateTheArchive(BaseZipTests):
    """
        This class is used for providing functionality
        for TestZipnoteFailsToUpdateTheArchive test case
    """
    def __init__(self):
        self._purpose = PURPOSE
        super(TestZipnoteFailsToUpdateTheArchive, self).__init__()

        self._tmpdir = '/tmp/tmp.{}'.format(uuid.uuid4())

    @decorated_message("Preparing setup")
    def prepare_setup(self):
        """

        :return:
        """
        self.check_package()
        self.run_cmd("mkdir {}".format(self._tmpdir), 0, "Creating tmp directory {}".format(self._tmpdir))

    @decorated_message("Starting Test")
    def start_test(self):
        """

        :return:
        """
        self.run_cmd("touch file", 0, "Creating the Demo file", cwd=self._tmpdir)
        self.run_cmd("zip archive.zip file", 0, "Creating the archive including the file", cwd=self._tmpdir)
        self.run_cmd("zipnote archive.zip > info.txt", 0, "Reading the archive comments", cwd=self._tmpdir)
        ## bad - e.g. zip-3.0-1.el6.i686:
        # zipnote error: Interrupted (aborting)
        # Segmentation fault
        ## good: no output
        self.run_cmd("zipnote -w archive.zip < info.txt > output_file.txt 2>&1", 0, "Writing comments to the archive",
                     cwd=self._tmpdir)

        if 'error' in open(self._tmpdir + '/output_file.txt').read():
            self.logger.debug("FAIL ] :: [ File shouldn't contain an error pattern")
        else:
            self.logger.debug("PASS ] :: [ File doesn't contain an error pattern")

    @decorated_message("Cleaning up")
    def cleanup(self):
        """

        :return:
        """
        self.run_cmd("rm -r {}".format(self._tmpdir), 0,
                     "Removing tmp directory")


if __name__ == "__main__":
    test = TestZipnoteFailsToUpdateTheArchive()
    try:
        test.prepare_setup()
        test.start_test()
    except AssertionError, exp:
        test.logger.debug("FAIL ] :: [ Assertion occurred {0}".format(exp))
    except Exception, exp:
        test.logger.debug("FAIL ] :: [ Exception occurred {0}".format(exp))
    finally:
        test.cleanup()
