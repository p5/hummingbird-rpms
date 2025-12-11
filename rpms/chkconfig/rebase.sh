#!/bin/bash
set -e
curl https://raw.githubusercontent.com/fedora-sysv/chkconfig/master/chkconfig.spec -o chkconfig.spec
git add chkconfig.spec
spectool -g chkconfig.spec
fedpkg new-sources $(basename $(spectool -S -l chkconfig.spec | awk '{print $2;}'))
git commit -m $(grep Version chkconfig.spec | awk '{print $2;}')


