# kernel-srpm-macros

The kernel-srpm-macros package

This source package results in two "binary" packages, kernel-rpm-macros
and kernel-srpm-macros. The role and locations of files is as follows:

kernel-srpm-macros:

/usr/lib/rpm/fileattrs/kmod.attr
	For /lib/modules/XYZ/modules.builtin and .../MODULE.ko.XYZ
	specifies a Lua script to generate kmod(MODULE.ko)
	"Provides:" deps
/usr/lib/rpm/macros.d/macros.kernel-srpm
	Automatically included by all rpm invocations.
	Defines %kernel_arches (try rpm --eval '%kernel_arches')
		Question: what uses this macro? I didn't find any users.

kernel-rpm-macros:

/usr/lib/rpm/redhat/find-provides.ksyms
	Runs from rpmbuild at the end of kernel builds and 3rd party module
	builds, to extract
	kernel(SYMBOL)=0xHASH "Provides:" deps from modules in kernel packages,
	and ksym(SYMBOL)=0xHASH for 3rd party modules.
	Takes input list of files on stdin.
/usr/lib/rpm/fileattrs/provided_ksyms.attr
	For newer rpmbuild with "internal dependency generators",
	this file specifies that find-provides.ksyms should be run
	only on .ko.XYZ files
	(with "external dependency generators", the script needs to
	filter out the files by itself).

/usr/lib/rpm/redhat/find-requires.ksyms
	?
/usr/lib/rpm/fileattrs/required_ksyms.attr
	For newer rpmbuild with "internal dependency generators",
	this file specifies that find-requires.ksyms should be run
	only on .ko.XYZ files, and not for /lib/modules/XYZ/kernel/*
	(IOW: only for building 3rd-party modules)

/usr/lib/rpm/redhat/find-provides.d/modalias.prov
	Runs from rpmbuild at the end of kernel builds and 3rd party module
	builds, to extract
	modalias(pci:SOMETHING)=OPTIONALLY_VERSION "Provides:" deps from modules
	in kernel and 3rd party modules packages.
	Takes input list of files on stdin.
		Question: what uses these deps?
/usr/lib/rpm/fileattrs/modalias.attr
	For newer rpmbuild with "internal dependency generators",
	this file specifies that modalias.prov should be run
	only on .ko.XYZ files

/usr/lib/rpm/redhat/find-provides.d/firmware.prov
	?

/usr/lib/rpm/kabi.sh
	Runs from rpmbuild at the end of kernel build to extract
	kernel(SYMBOL)=0xHASH "Provides:" deps.
/usr/lib/rpm/fileattrs/kabi.attr
	For newer rpmbuild with "internal dependency generators",
	this file specifies that kabi.sh should be run on
	/boot/symvers-* and /lib/modules/XYZ/symvers.gz

/usr/lib/rpm/macros.d/macros.kmp
	Automatically included by all rpm invocations.
	Defines a number of macros.

/usr/lib/rpm/redhat/brp-kmod-restore-perms
	?
/usr/lib/rpm/redhat/brp-kmod-set-exec-bit
	?

/usr/lib/rpm/redhat/kmodtool
	?
/usr/lib/rpm/redhat/rpmsort
	?
/usr/lib/rpm/redhat/symset-table
	?
