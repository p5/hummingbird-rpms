# -*- coding: utf-8 -*-

import logging
import os
import subprocess


# Saving logs
logging.basicConfig(level=logging.INFO)

DECORATE_STR = "************************************"
logging.info("TEST RESULTS FOR GETTEXT\n{0}".format(DECORATE_STR))

# CONSTANTS
PACKAGE_TO_TEST = "gettext"
DOMAIN_TO_BIND = "testdomain"
PYTHON_INTERPRETER = "python3"
TEST_I18N_FILE = "test_i18n.py"

LOG_INFO_PASS = "[ PASS ]"
LOG_INFO_FAIL = "[ FAIL ]"
LOG_INFO_OS_ERROR = "[ OS Error ]"

# Test Data
TEST_DATA = {"fr_FR": '''msgstr "Bonjour le monde!"''',
             "de_DE": '''msgstr "Hallo Welt!"''',
             "es_ES": '''msgstr "Hola Mundo!"''',
             "it_IT": '''msgstr "Ciao mondo!"''',
             "pt_BR": '''msgstr "Olá Mundo!"''',
             "ja_JP": '''msgstr "「こんにちは世界」"''',
             "ko_KR": '''msgstr "안녕하세요!"''',
             "ru_RU": '''msgstr "Привет мир!"''',
             "zh_CN": '''msgstr "你好，世界！"''',
             "zh_TW": '''msgstr "你好，世界！"'''}


def test_locale():
    """
    Check common files for locale support
    """

    subject = "Locale Support Test"

    try:
        all_locales = subprocess.Popen(["locale", "-a"], stdout=subprocess.PIPE)
        all_locales_data = all_locales.communicate()

        if all_locales_data:
            actual = all_locales_data[0].decode().split('\n')
        else:
            logging.error("{0}: ERROR\n".format(subject))
            return

        expected_locales = ['en_US', 'en_US.iso88591',
                            'en_US.iso885915', 'en_US.utf8']
        if set(expected_locales).issubset(set(actual)):
            logging.info("{0}: {1}\n".format(subject, LOG_INFO_PASS))
        else:
            logging.error("{0}: {1}\n".format(subject, LOG_INFO_FAIL))

    except OSError as e:
        logging.error("{0}: {1}\n".format(subject, LOG_INFO_OS_ERROR))


def test_gettext():
    """
    Check if gettext is present
    """

    subject = "GNU Internationalization Utilities Test"

    try:
        cmd_check_gettext = ['rpm', '-q', PACKAGE_TO_TEST]
        p1 = subprocess.Popen(cmd_check_gettext, stdout=subprocess.PIPE)
        std_data, stderr = p1.communicate()
        std_data = std_data.decode()
        logging.info("Found {0} NVR: {1}".format(PACKAGE_TO_TEST, std_data))
        if PACKAGE_TO_TEST in std_data:
            logging.info("{0}: {1}\n".format(subject, LOG_INFO_PASS))
        else:
            logging.error("{0}: {1}\n".format(subject, LOG_INFO_FAIL))
    except OSError as e:
        logging.error("{0}: {1}\n".format(subject, LOG_INFO_OS_ERROR))


def test_pot_creation():
    """
    Creates hello.pot file using test_i18n.py file
    """

    subject = "POT file Creation Test"

    try:
        pot_file = subprocess.Popen(
            "xgettext -d '{0}' -o {1}.pot {2}".format(DOMAIN_TO_BIND,
                                                      DOMAIN_TO_BIND,
                                                      TEST_I18N_FILE),
            shell=True
        )
        pot_file.communicate()
    except OSError as e:
        logging.error("{0}: {1}\n".format(subject, LOG_INFO_OS_ERROR))
    else:
        logging.info("{0}: {1}\n".format(subject, LOG_INFO_PASS))


def make_dir(locale_dir):
    path = "./locale/{0}/LC_MESSAGES".format(locale_dir)
    os.makedirs(path)


def create_po_files(active_locale):
    """
    creates .po file using POT file
    """

    subject = "PO file Creation"

    try:
        cmd_po_files = subprocess.Popen(
            "msginit --no-translator -l {0} -i {1}.pot -o ./locale/{2}/LC_MESSAGES/{3}.po".format(
                active_locale, DOMAIN_TO_BIND, active_locale, active_locale), shell=True
        )
        cmd_po_files.communicate()
    except OSError as e:
        logging.error("{0} failed: {1}\n".format(subject, LOG_INFO_OS_ERROR))
    else:
        logging.info("{0} Succeed.".format(subject))


def translate(active_locale):
    """
    Updates .po file with the translations for respective language
    """

    data = TEST_DATA.get(active_locale)
    if not data:
        return
    with open('./locale/{0}/LC_MESSAGES/{1}.po'.format(active_locale,
                                                       active_locale),
              'r', encoding='latin-1') as f1:
        data1 = f1.readlines()
        data1.pop()
        data1.append(data)
        for index, data in enumerate(data1):
            if "Content-Type" in data:
                data1[index] = '"Content-Type: text/plain; charset=UTF-8\\n"\n'

    with open('./locale/{0}/LC_MESSAGES/{1}'.format(active_locale,
                                                    active_locale) + ".po", 'w') as f2:
        for line in data1:
            f2.write(line)


def create_mo_files(active_locale):
    """
    Creates .mo file for different locale form .po file
    """

    subject = "MO file Creation"

    try:
        mo_files = subprocess.Popen(
            "msgfmt ./locale/{0}/LC_MESSAGES/{1}.po --output-file ./locale/{2}/LC_MESSAGES/{3}.mo".format(
                active_locale, active_locale, active_locale, active_locale
            ), shell=True
        )
        mo_files.communicate()
    except OSError as e:
        logging.error("{0} failed: {1}\n".format(subject, LOG_INFO_OS_ERROR))
    else:
        logging.info("{0} Succeed.".format(subject))


def test_translations(active_locale):
    """
    Verify if the output is correct for different language
    """

    subject = "Translation Test"

    try:
        cmd_translation_test = subprocess.check_output(
            'LANGUAGE={0} {1} {2} {3}'.format(active_locale,
                                              PYTHON_INTERPRETER,
                                              TEST_I18N_FILE,
                                              active_locale),
            encoding='UTF-8', shell=True
        )
        if cmd_translation_test.strip() == TEST_DATA[active_locale].strip('msgstr "'):
            logging.info("{0} for {1}: {2}\n".format(subject, active_locale, LOG_INFO_PASS))
        else:
            logging.error("{0} for {1}: {2}\n".format(subject, active_locale, LOG_INFO_FAIL))
    except OSError as e:
        logging.error("{0} for {1}: {2}\n".format(subject, active_locale, LOG_INFO_OS_ERROR))


def tear_off():
    try:
        subprocess.call(['rm', '-rf', './locale', '{0}.pot'.format(DOMAIN_TO_BIND)])
    except OSError as e:
        logging.error("OSError\n")


if __name__ == "__main__":
    """
    Gettext Tests
    """

    # Prepare tests
    env_tests = [test_locale,
                 test_gettext,
                 test_pot_creation]

    translation_tests = [make_dir,
                         create_po_files,
                         translate,
                         create_mo_files,
                         test_translations]

    # Execute tests
    [env_test() for env_test in env_tests]

    for locale in TEST_DATA.keys():
        [test(locale) for test in translation_tests]

    tear_off()
