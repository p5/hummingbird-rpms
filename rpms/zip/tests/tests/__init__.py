'''
    author = esakaiev@redhat.com
'''
import logging
import sys
import subprocess
import os
import shutil


def decorated_message(message):
    """
        This decorator is used for providing logging header for different sections in the scripts
        :param message: (`STRING`)
        :return: decorated_function
    """

    def decorated_function(func):
        """

        :param func:
        :return:
        """

        def wrapper(self):
            """

            :param self:
            :return:
            """
            print " "
            print ("::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::")
            print (":: {0}".format(message))
            print ("::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::")

            func(self)

        return wrapper

    return decorated_function


class BaseZipTests(object):
    """
        This is a Base class for zip tests
    """

    def __init__(self):
        self._set_logger()
        self._purpose = ""
        self.print_test_purpose()

    def _set_logger(self):
        """
        This method is used for instantiating of logger
        :return:
        - None
        """
        self.logger = logging.getLogger()
        self.logger.setLevel(logging.DEBUG)

        self.handler = logging.StreamHandler(sys.stdout)
        self.handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('[ %(asctime)s ] :: [ %(message)s ]')
        self.handler.setFormatter(formatter)
        self.logger.addHandler(self.handler)

    @decorated_message("PURPOSE")
    def print_test_purpose(self):
        """

        :return:
        """
        print self._purpose

    def run_cmd(self, cmd, exp_err_code, message, cwd=None):
        """
        This method is used for executing cmd, check output error code and
        add result in the logger
        :param cmd: ('STRING') - some command to execute
        :param exp_err_code: ('INTEGER') - expected error code
        :param message: ('STRING') - command description
        :param cwd: ('STRING') - path to directory, where need to execute cmd
        :return:
         - errcode ('INTEGER')
        """
        try:
            errcode = subprocess.call(cmd, shell=True, cwd=cwd, stdout=sys.stderr.fileno())
            if errcode != exp_err_code:
                self.logger.debug("FAIL :: {0}".format(message))
            else:
                self.logger.debug("PASS ] :: [ {0}".format(message))
            return errcode
        except subprocess.CalledProcessError as exp:
            self.logger.error("Could not execute command {0}, e: {1}".format(cmd, exp))

    def check_package(self):
        """
        This method is used for checking, if zip package is installed
        :return: None
        """
        assert self.run_cmd("dnf list installed zip", 0, "Dnf package should be installed") == 0

    def check_output(self, cmd, exp_output, message, cwd=None):
        """
        This method is used for executing cmd and compare output result with expected message
        :param cmd: (`STRING`) - some command to execute
        :param exp_err_code: (`INTEGER`) - expected error code
        :param message: (`STRING`) - command description
        :param cwd: (`STRING`) - path to directory, where need to execute cmd
        :return:
        - output message (`STRING`)
        """
        try:
            output = self.execute_cmd(cmd, cwd)
            if output != exp_output:
                self.logger.debug("FAIL ]:: [ {}".format(message))
            else:
                self.logger.debug("PASS ] :: [ {}".format(message))
            return output
        except subprocess.CalledProcessError as exp:
            self.logger.error(r'FAIL ] :: [ Could not execute command: "{0}",\
             ex: {1}'.format(cmd, exp))

    def execute_cmd(self, cmd, cwd=None):
        """
        This method is used for executing cmd and return output message
        :param cmd: (`STRING`) - some command to execute
        :param cwd: (`STRING`) - path to directory, where need to execute cmd
        :return:
        - output message (`STRING`)
        """
        try:
            output = subprocess.check_output(cmd, shell=True, cwd=cwd)
            return output
        except subprocess.CalledProcessError as exp:
            self.logger.error(r'FAIL ] :: [ Could not execute command: "{0}",\
                               ex: {1}'.format(cmd, exp))

    def remove_file(self, file_path, is_directory=False):
        """
        This method is used for removing files or directories after execution of test cases
        :param file_path:(`STRING`) - path to file/folder
        :param is_directory: (`BOOLEAN`) - True for directories
        :return: None
        """
        try:
            if is_directory:
                shutil.rmtree(file_path)
            else:
                os.remove(file_path)
            self.logger.debug("File {0} has been successfully removed".format(file_path))
        except OSError, exp:
            self.logger.debug("File {0} doesn't exists, e: {1}".format(file_path, exp))
