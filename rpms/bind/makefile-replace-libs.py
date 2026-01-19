#!/usr/bin/python3
#
# Makefile modificator
#
# Should help in building bin/tests/system tests standalone,
# linked to libraries installed into the system.
# TODO:
# - Fix top_srcdir, because dyndb/driver/Makefile uses $TOPSRC/mkinstalldirs
# - Fix conf.sh to contain paths to system tools
# - Export $TOP/version somewhere, where it would be used
# - system tests needs bin/tests code. Do not include just bin/tests/system
#
# Possible solution:
#
# sed -e 's/$TOP\/s\?bin\/\(delv\|confgen\|named\|nsupdate\|pkcs11\|python\|rndc\|check\|dig\|dnssec\|tools\)\/\([[:alnum:]-]\+\)/`type -p \2`/' conf.sh
# sed -e 's,../../../../\(isc-config.sh\),\1,' builtin/tests.sh
# or use: $NAMED -V | head -1 | cut -d ' ' -f 2

import re
import argparse

"""
Script for replacing Makefile ISC_INCLUDES with runtime flags.

Should translate part of Makefile to use isc-config.sh instead static linked sources.
ISC_INCLUDES = -I/home/pemensik/rhel/bind/bind-9.11.12/build/lib/isc/include \
        -I${top_srcdir}/lib/isc \
        -I${top_srcdir}/lib/isc/include \
        -I${top_srcdir}/lib/isc/unix/include \
        -I${top_srcdir}/lib/isc/pthreads/include \
        -I${top_srcdir}/lib/isc/x86_32/include

Should be translated to:
ISC_INCLUDES = $(shell isc-config.sh --cflags isc)
"""

def isc_config(mode, lib):
    if mode:
        return '$(shell isc-config.sh {mode} {lib})'.format(mode=mode, lib=lib)
    else:
        return ''

def check_match(match, debug=False):
    """
    Check this definition is handled by internal library
    """
    if not match:
        return False
    lib = match.group(2).lower()
    ok = not lib_filter or lib in lib_filter
    if debug:
        print('{status} {lib}: {text}'.format(status=ok, lib=lib, text=match.group(1)))
    return ok

def fix_line(match, mode):
    lib = match.group(2).lower()
    return match.group(1)+isc_config(mode, lib)+"\n"

def fix_file_lines(path, debug=False):
    """
    Opens file and scans fixes selected parameters

    Returns list of lines if something should be changed,
    None if no action is required
    """
    fixed = []
    changed = False
    with open(path, 'r') as fin:
        fout = None

        line = next(fin, None)
        while line:
            appended = False
            while line.endswith("\\\n"):
                line += next(fin, None)

            inc = re_includes.match(line)
            deplibs = re_deplibs.match(line)
            libs = re_libs.match(line)
            newline = None
            if check_match(inc, debug=debug):
                newline = fix_line(inc, '--cflags')
            elif check_match(deplibs, debug=debug):
                newline = fix_line(libs, None)
            elif check_match(libs, debug=debug):
                newline = fix_line(libs, '--libs')

            if newline and line != newline:
                changed = True
                line = newline

            fixed.append(line)
            line = next(fin, None)

    if not changed:
        return None
    else:
        return fixed

def write_lines(path, lines):
    fout = open(path, 'w')
    for line in lines:
        fout.write(line)
    fout.close()

def print_lines(lines):
    for line in lines:
        print(line, end='')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Makefile multiline include replacer')
    parser.add_argument('files', nargs='+')
    parser.add_argument('--filter', type=str,
            default='isc isccc isccfg dns lwres bind9 irs',
            help='List of libraries supported by isc-config.sh')
    parser.add_argument('--check', action='store_true',
            help='Test file only')
    parser.add_argument('--print', action='store_true',
            help='Print changed file only')
    parser.add_argument('--debug', action='store_true',
            help='Enable debug outputs')

    args = parser.parse_args()
    lib_filter = None

    re_includes = re.compile(r'^\s*((\w+)_INCLUDES\s+=\s*).*')
    re_deplibs = re.compile(r'^\s*((\w+)DEPLIBS\s*=).*')
    re_libs = re.compile(r'^\s*((\w+)LIBS\s*=).*')

    if args.filter:
        lib_filter = set(args.filter.split(' '))
        pass

    for path in args.files:
        lines = fix_file_lines(path, debug=args.debug)
        if lines:
            if args.print:
                print_lines(lines)
            elif not args.check:
                write_lines(path, lines)
                print('File {path} was fixed'.format(path=path))
        else:
            print('File {path} does not need fixing'.format(path=path))
