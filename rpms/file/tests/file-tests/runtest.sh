#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh

compare() {
    IN="db/$1"
    OUT="$TMPDIR/out"
    ERR="$TMPDIR/err"
    rlRun "file '$IN' > '$OUT' 2> '$ERR'" "0" "Run file on $1"
    sed -i "s|^$IN: ||" "$OUT"
    REF="reference/$1.ref"
    if ! rlAssertNotDiffer "$REF" "$OUT"; then
        rlRun -l "diff -u '$REF' '$OUT'" 1
    fi
    rlRun "test ! -s '$ERR'" "0" "Check that stderr was empty"
}

PACKAGE="file"

rlJournalStart

    rlPhaseStartSetup
        rlAssertRpm "$PACKAGE"
        TMPDIR="$(mktemp -d)"
    rlPhaseEnd

    rlPhaseStartTest '3ds'
        compare '3ds/key.3DS'
    rlPhaseEnd

    rlPhaseStartTest '7z'
        compare '7z/spectrum.7z'
    rlPhaseEnd

    rlPhaseStartTest 'accdb'
        compare 'accdb/database.accdb'
    rlPhaseEnd

    rlPhaseStartTest 'ade'
        compare 'ade/ms_access_project_encoded.ade'
    rlPhaseEnd

    rlPhaseStartTest 'adp'
        compare 'adp/ms_access_project.adp'
    rlPhaseEnd

    rlPhaseStartTest 'ani'
        compare 'ani/animated_cursor.ani'
    rlPhaseEnd

    rlPhaseStartTest 'AppleDouble'
        compare 'AppleDouble/AppleDouble'
    rlPhaseEnd

    rlPhaseStartTest 'asa'
        compare 'asa/global.asa'
    rlPhaseEnd

    rlPhaseStartTest 'asp'
        compare 'asp/policies_part.asp'
    rlPhaseEnd

    rlPhaseStartTest 'bas'
        compare 'bas/PILES_START.bas'
    rlPhaseEnd

    rlPhaseStartTest 'bat'
        compare 'bat/build.bat'
    rlPhaseEnd

    rlPhaseStartTest 'bin'
        compare 'bin/vax'
    rlPhaseEnd

    rlPhaseStartTest 'bmp'
        compare 'bmp/4x2x24-win3.bmp'
        compare 'bmp/4x2x32-win95.bmp'
        compare 'bmp/4x2x32-win98.bmp'
        compare 'bmp/InstallerHeader.bmp'
    rlPhaseEnd

    rlPhaseStartTest 'bz2'
        compare 'bz2/test.txt.bz2'
    rlPhaseEnd

    rlPhaseStartTest 'cab'
    rlPhaseEnd

    rlPhaseStartTest 'chm'
        compare 'chm/index_start.chm'
    rlPhaseEnd

    rlPhaseStartTest 'cmd'
        compare 'cmd/wp_batch_example.cmd'
    rlPhaseEnd

    rlPhaseStartTest 'cnt'
        compare 'cnt/help-contents.cnt'
    rlPhaseEnd

    rlPhaseStartTest 'com'
        compare 'com/kssf.com'
    rlPhaseEnd

    rlPhaseStartTest 'cpl'
        compare 'cpl/ac3filter_first4k.cpl'
    rlPhaseEnd

    rlPhaseStartTest 'cpp'
        compare 'cpp/test.cpp'
    rlPhaseEnd

    rlPhaseStartTest 'crt'
        compare 'crt/server.crt'
    rlPhaseEnd

    rlPhaseStartTest 'cur'
        compare 'cur/cursor.cur'
    rlPhaseEnd

    rlPhaseStartTest 'dat'
        compare 'dat/winmail.dat'
    rlPhaseEnd

    rlPhaseStartTest 'db'
        compare 'db/sqlite3.db'
        compare 'db/thumbs.db'
    rlPhaseEnd

    rlPhaseStartTest 'dbf'
        compare 'dbf/biblio.dbf'
    rlPhaseEnd

    rlPhaseStartTest 'deb'
        compare 'deb/p.deb'
    rlPhaseEnd

    rlPhaseStartTest 'diso'
        compare 'diso/foo.diso'
    rlPhaseEnd

    rlPhaseStartTest 'dll'
        compare 'dll/SDL2.dll'
    rlPhaseEnd

    rlPhaseStartTest 'dmp'
        compare 'dmp/mdmp.dmp'
    rlPhaseEnd

    rlPhaseStartTest 'doc'
        compare 'doc/word_document.doc'
        compare 'doc/word_document_with_autostart_macro.doc'
    rlPhaseEnd

    rlPhaseStartTest 'docm'
        compare 'docm/encrypted.docm'
        compare 'docm/word_document.docm'
        compare 'docm/word_document_with_autostart_macro.docm'
    rlPhaseEnd

    rlPhaseStartTest 'docx'
        compare 'docx/encrypted.docx'
        compare 'docx/word_document.docx'
    rlPhaseEnd

    rlPhaseStartTest 'dot'
        compare 'dot/word_document.dot'
        compare 'dot/word_document_with_autostart_macro.dot'
    rlPhaseEnd

    rlPhaseStartTest 'dotm'
        compare 'dotm/word_document.dotm'
        compare 'dotm/word_document_with_autostart_macro.dotm'
    rlPhaseEnd

    rlPhaseStartTest 'dotx'
        compare 'dotx/word_document.dotx'
    rlPhaseEnd

    rlPhaseStartTest 'drpm'
        compare 'drpm/foo1.drpm'
        compare 'drpm/foo2.drpm'
    rlPhaseEnd

    rlPhaseStartTest 'DS_Store'
        compare 'DS_Store/DS_Store'
    rlPhaseEnd

    rlPhaseStartTest 'dump'
        compare 'dump/evolocal.odb'
    rlPhaseEnd

    rlPhaseStartTest 'elf'
        compare 'elf/a'
        compare 'elf/filter'
        compare 'elf/hello-aarch64-executable'
        compare 'elf/library-now.so'
        compare 'elf/new-keyctl.debug'
        compare 'elf/old-keyctl.debug'
        compare 'elf/pie-test'
        compare 'elf/ppm'
    rlPhaseEnd

    rlPhaseStartTest 'exe'
        compare 'exe/e5f5fdb10c8bb35d3219a87516147e15.exe'
    rlPhaseEnd

    rlPhaseStartTest 'filesystems'
        compare 'filesystems/bootsector'
        compare 'filesystems/ext4'
        compare 'filesystems/filetest'
        compare 'filesystems/lvm2'
        compare 'filesystems/ntfs'
        compare 'filesystems/swap-ia64'
        compare 'filesystems/swap-ppc'
    rlPhaseEnd

    rlPhaseStartTest 'frm'
        compare 'frm/help_relation.frm'
    rlPhaseEnd

    rlPhaseStartTest 'gif'
        compare 'gif/1.gif'
    rlPhaseEnd

    rlPhaseStartTest 'gz'
        compare 'gz/abc1.gz'
        compare 'gz/abc2.gz'
        compare 'gz/a.gz'
    rlPhaseEnd

    rlPhaseStartTest 'h'
        compare 'h/a.h'
        compare 'h/basic_string.h'
        compare 'h/gclosure.h'
        compare 'h/gfileattribute.h'
        compare 'h/gfile.h'
        compare 'h/gsocketaddressenumerator.h'
        compare 'h/gunixmounts.h'
        compare 'h/stl_map.h'
        compare 'h/stl_queue.h'
        compare 'h/stl_stack.h'
    rlPhaseEnd

    rlPhaseStartTest 'hlp'
        compare 'hlp/biochlr2.hlp'
    rlPhaseEnd

    rlPhaseStartTest 'hta'
        compare 'hta/access.hta'
        compare 'hta/hello_world.hta'
    rlPhaseEnd

    rlPhaseStartTest 'html'
        compare 'html/index_first4k.html'
    rlPhaseEnd

    rlPhaseStartTest 'icm'
        compare 'icm/bluish.icc'
        compare 'icm/sRGB.icm'
    rlPhaseEnd

    rlPhaseStartTest 'ico'
        compare 'ico/pixel-install.ico'
    rlPhaseEnd

    rlPhaseStartTest 'img'
        compare 'img/initrd1.img'
        compare 'img/qcow2_v2.qcow2'
        compare 'img/qcow2_v3.qcow2'
        compare 'img/qcow_v1.qcow'
        compare 'img/qed.img'
        compare 'img/vdi.img'
    rlPhaseEnd

    rlPhaseStartTest 'ins'
        compare 'ins/internet_connection_settings.ins'
        compare 'ins/setup.ins'
    rlPhaseEnd

    rlPhaseStartTest 'iso'
        compare 'iso/x.iso'
    rlPhaseEnd

    rlPhaseStartTest 'isp'
        compare 'isp/self-created.isp'
    rlPhaseEnd

    rlPhaseStartTest 'java'
        compare 'java/CreateMdb.java'
    rlPhaseEnd

    rlPhaseStartTest 'jpc'
        compare 'jpc/testing.jpc'
        compare 'jpc/test.jpc'
    rlPhaseEnd

    rlPhaseStartTest 'jpg'
        compare 'jpg/lime-cat.jpg'
    rlPhaseEnd

    rlPhaseStartTest 'js'
        compare 'js/smartmobile.js'
    rlPhaseEnd

    rlPhaseStartTest 'jse'
        compare 'jse/smartmobile.jse'
    rlPhaseEnd

    rlPhaseStartTest 'json'
        compare 'json/1.json-keep'
        compare 'json/2.json-keep'
        compare 'json/3.json-keep'
        compare 'json/4.json-keep'
        compare 'json/5.json-keep'
    rlPhaseEnd

    rlPhaseStartTest 'kernels'
        compare 'kernels/s390x'
        compare 'kernels/x86_64'
    rlPhaseEnd

    rlPhaseStartTest 'lnk'
    rlPhaseEnd

    rlPhaseStartTest 'locale'
        compare 'locale/LC_ADDRESS'
        compare 'locale/LC_COLLATE'
        compare 'locale/LC_CTYPE'
        compare 'locale/LC_IDENTIFICATION'
        compare 'locale/LC_MEASUREMENT'
        compare 'locale/LC_MONETARY'
        compare 'locale/LC_NAME'
        compare 'locale/LC_NUMERIC'
        compare 'locale/LC_PAPER'
        compare 'locale/LC_TELEPHONE'
        compare 'locale/LC_TIME'
    rlPhaseEnd

    rlPhaseStartTest 'lsm'
        compare 'lsm/sysstate.lsm'
    rlPhaseEnd

    rlPhaseStartTest 'lua'
        compare 'lua/mod_actions_http.lua'
    rlPhaseEnd

    rlPhaseStartTest 'mach-o'
    rlPhaseEnd

    rlPhaseStartTest 'mc'
        compare 'mc/submit.mc'
    rlPhaseEnd

    rlPhaseStartTest 'mdb'
        compare 'mdb/a.mdb'
        compare 'mdb/self-created.mdb'
    rlPhaseEnd

    rlPhaseStartTest 'mde'
        compare 'mde/encoded_db.mde'
    rlPhaseEnd

    rlPhaseStartTest 'mid'
        compare 'mid/notes.mid'
    rlPhaseEnd

    rlPhaseStartTest 'misc'
        compare 'misc/ansi2knr'
        compare 'misc/core'
        compare 'misc/core2'
        compare 'misc/mysql-bin-replication-log'
        compare 'misc/openvpn'
        compare 'misc/p_cert'
        compare 'misc/p_clear'
        compare 'misc/p_pass'
        compare 'misc/RPM-GPG-KEY-fedora-14-primary'
        compare 'misc/selinux_policy'
        compare 'misc/zeros'
    rlPhaseEnd

    rlPhaseStartTest 'mkv'
        compare 'mkv/matroska_test.mkv'
        compare 'mkv/sample.mkv'
    rlPhaseEnd

    rlPhaseStartTest 'mng'
        compare 'mng/jabber_connecting.mng'
    rlPhaseEnd

    rlPhaseStartTest 'mo'
        compare 'mo/a.mo'
    rlPhaseEnd

    rlPhaseStartTest 'mono'
        compare 'mono/Mono.TextTemplating.dll'
        compare 'mono/TextTransform.exe'
    rlPhaseEnd

    rlPhaseStartTest 'mp3'
        compare 'mp3/house_lo.mp3'
    rlPhaseEnd

    rlPhaseStartTest 'msc'
        compare 'msc/ms_management_console.msc'
    rlPhaseEnd

    rlPhaseStartTest 'msi'
        compare 'msi/SampleFirst_full.msi'
    rlPhaseEnd

    rlPhaseStartTest 'msp'
        compare 'msp/Patch_full.msp'
    rlPhaseEnd

    rlPhaseStartTest 'mst'
        compare 'mst/wix_transform_full.mst'
    rlPhaseEnd

    rlPhaseStartTest 'myi'
        compare 'myi/event.MYI'
    rlPhaseEnd

    rlPhaseStartTest 'ods'
        compare 'ods/test.ods'
    rlPhaseEnd

    rlPhaseStartTest 'ogg'
        compare 'ogg/fiba1.ogg'
    rlPhaseEnd

    rlPhaseStartTest 'one'
        compare 'one/NewSection2007.one'
        compare 'one/NewSection2010.one'
        compare 'one/NewSection2016.one'
    rlPhaseEnd

    rlPhaseStartTest 'onepkg'
        compare 'onepkg/minimal-sample-2007.onepkg'
    rlPhaseEnd

    rlPhaseStartTest 'onetoc2'
        compare 'onetoc2/OpenNote2007.onetoc2'
        compare 'onetoc2/OpenNote2016.onetoc2'
    rlPhaseEnd

    rlPhaseStartTest 'patch'
        compare 'patch/a.patch'
        compare 'patch/b.patch'
        compare 'patch/parser571033.patch'
    rlPhaseEnd

    rlPhaseStartTest 'pbm'
    rlPhaseEnd

    rlPhaseStartTest 'pcd'
    rlPhaseEnd

    rlPhaseStartTest 'pdf'
        compare 'pdf/mailman-admin.pdf'
    rlPhaseEnd

    rlPhaseStartTest 'pfa'
        compare 'pfa/bchb.pfa'
    rlPhaseEnd

    rlPhaseStartTest 'pfb'
        compare 'pfb/a010013l.pfb'
    rlPhaseEnd

    rlPhaseStartTest 'pif'
        compare 'pif/command.pif'
    rlPhaseEnd

    rlPhaseStartTest 'pl'
        compare 'pl/apxs'
        compare 'pl/arg_shebang.pl'
        compare 'pl/ConfigLocal_PM.pl'
        compare 'pl/enc2xs'
        compare 'pl/Makefile_PL.pl'
    rlPhaseEnd

    rlPhaseStartTest 'pm'
        compare 'pm/Find.pm'
        compare 'pm/Html.pm'
        compare 'pm/Select.pm'
    rlPhaseEnd

    rlPhaseStartTest 'png'
        compare 'png/adhoc1.png'
    rlPhaseEnd

    rlPhaseStartTest 'po'
        compare 'po/rev0.0.po'
        compare 'po/rev0.1.po'
        compare 'po/rev1.1.po'
        compare 'po/test.po'
    rlPhaseEnd

    rlPhaseStartTest 'pot'
        compare 'pot/presentation.pot'
        compare 'pot/presentation_with_autostart_macro.pot'
    rlPhaseEnd

    rlPhaseStartTest 'potm'
        compare 'potm/presentation.potm'
        compare 'potm/presentation_with_autostart_macro.potm'
    rlPhaseEnd

    rlPhaseStartTest 'potx'
        compare 'potx/presentation.potx'
    rlPhaseEnd

    rlPhaseStartTest 'ppa'
        compare 'ppa/presentation_non_auto_macros.ppa'
    rlPhaseEnd

    rlPhaseStartTest 'ppam'
        compare 'ppam/presentation_non_auto_macros.ppam'
    rlPhaseEnd

    rlPhaseStartTest 'ppc'
        compare 'ppc/coredump-ppc'
    rlPhaseEnd

    rlPhaseStartTest 'ppd'
        compare 'ppd/Generic-PDF_Printer-PDF.ppd'
    rlPhaseEnd

    rlPhaseStartTest 'ppm'
        compare 'ppm/a.ppm'
    rlPhaseEnd

    rlPhaseStartTest 'pps'
        compare 'pps/presentation.pps'
        compare 'pps/presentation_with_autostart_macro.pps'
    rlPhaseEnd

    rlPhaseStartTest 'ppsm'
        compare 'ppsm/presentation.ppsm'
        compare 'ppsm/presentation_with_autostart_macro.ppsm'
    rlPhaseEnd

    rlPhaseStartTest 'ppsx'
        compare 'ppsx/presentation.ppsx'
    rlPhaseEnd

    rlPhaseStartTest 'ppt'
        compare 'ppt/encrypted.ppt'
        compare 'ppt/presentation.ppt'
        compare 'ppt/presentation_with_autostart_macro.ppt'
    rlPhaseEnd

    rlPhaseStartTest 'pptm'
        compare 'pptm/encrypted.pptm'
        compare 'pptm/presentation.pptm'
        compare 'pptm/presentation_with_autostart_macro.pptm'
    rlPhaseEnd

    rlPhaseStartTest 'pptx'
        compare 'pptx/encrypted.pptx'
        compare 'pptx/presentation.pptx'
    rlPhaseEnd

    rlPhaseStartTest 'ps'
        compare 'ps/filtered-test.ps'
    rlPhaseEnd

    rlPhaseStartTest 'py'
        compare 'py/gtk_label_autowrap.py'
        compare 'py/music.py'
        compare 'py/p1.py'
        compare 'py/p2.py'
        compare 'py/p3.py'
        compare 'py/p4.py'
        compare 'py/p5.py'
        compare 'py/p6.py'
        compare 'py/Switchboard.py'
    rlPhaseEnd

    rlPhaseStartTest 'pyc'
        compare 'pyc/config.pyc'
        compare 'pyc/handle.pyc'
    rlPhaseEnd

    rlPhaseStartTest 'rar'
        compare 'rar/encrypted-hidden-filenames.rar'
        compare 'rar/encrypted.rar'
        compare 'rar/normal.rar'
        compare 'rar/rar-v4-archive.rar'
    rlPhaseEnd

    rlPhaseStartTest 'rb'
        compare 'rb/docbook.rb'
    rlPhaseEnd

    rlPhaseStartTest 'reg'
        compare 'reg/windows_registry.reg'
    rlPhaseEnd

    rlPhaseStartTest 'rpm'
        compare 'rpm/a.rpm'
        compare 'rpm/ppc64.rpm'
        compare 'rpm/ppc.rpm'
        compare 'rpm/s390.rpm'
        compare 'rpm/s390x.rpm'
        compare 'rpm/src.rpm'
    rlPhaseEnd

    rlPhaseStartTest 'rtf'
        compare 'rtf/word_document.rtf'
    rlPhaseEnd

    rlPhaseStartTest 's'
        compare 's/boring-asm.s'
    rlPhaseEnd

    rlPhaseStartTest 'scr'
        compare 'scr/SlideShow.scr'
    rlPhaseEnd

    rlPhaseStartTest 'sct'
        compare 'sct/editor_addin.sct'
    rlPhaseEnd

    rlPhaseStartTest 'shb'
        compare 'shb/win_document_shortcut_full.shb'
    rlPhaseEnd

    rlPhaseStartTest 'shs'
        compare 'shs/win_scrap_file_full.shs'
    rlPhaseEnd

    rlPhaseStartTest 'slk'
        compare 'slk/excel4_sample_macro.slk'
        compare 'slk/simple-slk-file.slk'
    rlPhaseEnd

    rlPhaseStartTest 'so'
        compare 'so/libtables.so'
    rlPhaseEnd

    rlPhaseStartTest 'svg'
        compare 'svg/esc.svg'
    rlPhaseEnd

    rlPhaseStartTest 'tar.gz'
    rlPhaseEnd

    rlPhaseStartTest 'tdb'
        compare 'tdb/test.tdb'
    rlPhaseEnd

    rlPhaseStartTest 'tex'
        compare 'tex/pl-refcard.tex'
        compare 'tex/sk-survival.tex'
        compare 'tex/test_latex.tex'
    rlPhaseEnd

    rlPhaseStartTest 'tga'
        compare 'tga/bloom.tga'
        compare 'tga/Font.tga'
    rlPhaseEnd

    rlPhaseStartTest 'tgz'
    rlPhaseEnd

    rlPhaseStartTest 'thmx'
        compare 'thmx/presentation.thmx'
    rlPhaseEnd

    rlPhaseStartTest 'tif'
        compare 'tif/note.tif'
    rlPhaseEnd

    rlPhaseStartTest 'timezone'
        compare 'timezone/localtime'
    rlPhaseEnd

    rlPhaseStartTest 'ts'
        compare 'ts/test1.ts'
        compare 'ts/test2.ts'
        compare 'ts/test3.ts'
    rlPhaseEnd

    rlPhaseStartTest 'ttf'
        compare 'ttf/NanumGothic.ttf'
    rlPhaseEnd

    rlPhaseStartTest 'txt'
        compare 'txt/dsn_15.txt'
        compare 'txt/magic-bug-sample.txt'
        compare 'txt/msg-6505-1.txt'
        compare 'txt/timestamp.txt'
    rlPhaseEnd

    rlPhaseStartTest 'ulaw'
        compare 'ulaw/star.ulaw'
    rlPhaseEnd

    rlPhaseStartTest 'vb'
        compare 'vb/HelloWorld.vb'
    rlPhaseEnd

    rlPhaseStartTest 'vbe'
        compare 'vbe/DateName.vbe'
    rlPhaseEnd

    rlPhaseStartTest 'vbs'
        compare 'vbs/DateName.vbs'
    rlPhaseEnd

    rlPhaseStartTest 'wav'
        compare 'wav/b0456.wav'
        compare 'wav/send.wav'
    rlPhaseEnd

    rlPhaseStartTest 'webm'
    rlPhaseEnd

    rlPhaseStartTest 'wmv'
        compare 'wmv/presentation.wmv'
    rlPhaseEnd

    rlPhaseStartTest 'wps'
        compare 'wps/word_document.wps'
    rlPhaseEnd

    rlPhaseStartTest 'wsc'
        compare 'wsc/HelloWorld.wsc'
    rlPhaseEnd

    rlPhaseStartTest 'wsf'
        compare 'wsf/HelloWorld.wsf'
    rlPhaseEnd

    rlPhaseStartTest 'wsh'
        compare 'wsh/HelloWorld.wsh'
    rlPhaseEnd

    rlPhaseStartTest 'xlam'
        compare 'xlam/calculation.xlam'
    rlPhaseEnd

    rlPhaseStartTest 'xls'
        compare 'xls/calculation-new-format.xls'
        compare 'xls/calculation-old-format.xls'
        compare 'xls/calculation_with_autostart_macro.xls'
    rlPhaseEnd

    rlPhaseStartTest 'xlsb'
        compare 'xlsb/calculation_with_autostart_macro.xlsb'
        compare 'xlsb/calculation.xlsb'
        compare 'xlsb/encrypted.xlsb'
    rlPhaseEnd

    rlPhaseStartTest 'xlsm'
        compare 'xlsm/calculation_with_autostart_macro.xlsm'
        compare 'xlsm/calculation.xlsm'
        compare 'xlsm/encrypted.xlsm'
    rlPhaseEnd

    rlPhaseStartTest 'xlsx'
        compare 'xlsx/calculation.xlsx'
        compare 'xlsx/encrypted.xlsx'
    rlPhaseEnd

    rlPhaseStartTest 'xlt'
        compare 'xlt/calculation.xlt'
    rlPhaseEnd

    rlPhaseStartTest 'xltm'
        compare 'xltm/calculation.xltm'
    rlPhaseEnd

    rlPhaseStartTest 'xltx'
        compare 'xltx/calculation.xltx'
    rlPhaseEnd

    rlPhaseStartTest 'xml'
        compare 'xml/calculation.xml'
        compare 'xml/output.xml'
        compare 'xml/result.xml'
        compare 'xml/xmlutf16.xml'
    rlPhaseEnd

    rlPhaseStartTest 'xps'
    rlPhaseEnd

    rlPhaseStartTest 'xpt'
        compare 'xpt/calbase.xpt'
    rlPhaseEnd

    rlPhaseStartTest 'xsl'
        compare 'xsl/table.xsl'
    rlPhaseEnd

    rlPhaseStartTest 'z5'
        compare 'z5/Aisle.z5'
        compare 'z5/guess.z5'
        compare 'z5/stiffmst.z5'
    rlPhaseEnd

    rlPhaseStartTest 'z7'
        compare 'z7/custard.z7'
    rlPhaseEnd

    rlPhaseStartTest 'z8'
        compare 'z8/ats.z8'
    rlPhaseEnd

    rlPhaseStartTest 'zip'
        compare 'zip/empty.zip'
        compare 'zip/stde.zip'
        compare 'zip/VisualC.zip'
    rlPhaseEnd

    rlPhaseStartCleanup
        rm -rf "$TMPDIR"
    rlPhaseEnd

    rlJournalPrintText
rlJournalEnd
