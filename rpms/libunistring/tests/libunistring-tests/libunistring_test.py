# -*- coding: utf-8 -*-

import sys
import os
import subprocess
import logging

"""
Creating a result.log file for saving logs
"""
logging.basicConfig(level=logging.INFO)

logging.info("TEST RESULTS FOR <uniconv.h> FUNCTION\n\n")

data = []

TESTTEXT = 'Viele Grüße\n日本語\n'

def create_testfiles():
    dummy = subprocess.run("./test '" + TESTTEXT + "'", shell=True)

def test(path='', encoding=''):
    """
    Read the file at path using the specified encoding and check
    whether the TESTTEXT can be read back correctly.
    """
    logging.info('Testing file %s using encoding %s', path, encoding)
    try:
        with open(path, mode='rt', encoding=encoding) as testfile:
            text = testfile.read()
        logging.info('TESTTEXT="%s", text read ="%s"\n', TESTTEXT, text)
        if text == TESTTEXT:
            logging.info(
                'testfile: %s testencoding: %s Read test: SUCCESS',
                path, encoding)
        else:
            logging.info(
                'testfile: %s testencoding: %s Read test: ERROR',
                path, encoding)
    except UnicodeError:
        logging.error("UTF-8 Conversion Test: UnicodeError")

if __name__ == "__main__":
    if sys.byteorder == 'little':
        endianness = 'le'
    else:
        endianness = 'be'
    testfiles = {
        'testfile.utf-8': 'utf-8',
        'testfile.utf-16': 'utf-16' + endianness,
        'testfile.utf-32': 'utf-32' + endianness,
    }
    for testfile in testfiles:
        if os.path.isfile(testfile):
            os.unlink(testfile)
    create_testfiles()
    for testfile in testfiles:
        test(path=testfile, encoding=testfiles[testfile])
