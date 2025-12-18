#!/bin/bash

# exit when any command fails
set -e

declare -A archs
archs[ia64]="efi_alt_arch=none
	efi_alt_arch_upper=NONE
	efi_arch=ia64
	efi_arch_upper=IA64
	efi_has_alt_arch=00
	efi_has_arch=01"
archs[x86_64]="efi_alt_arch=ia32
	efi_alt_arch_upper=IA32
	efi_arch=x64
	efi_arch_upper=X64
	efi_has_alt_arch=01
	efi_has_arch=01"
archs["%{ix86}"]="efi_alt_arch=none
	efi_alt_arch_upper=NONE
	efi_arch=ia32
	efi_arch_upper=IA32
	efi_has_alt_arch=00
	efi_has_arch=01"
archs[aarch64]="efi_alt_arch=none
	efi_alt_arch_upper=NONE
	efi_arch=aa64
	efi_arch_upper=AA64
	efi_has_alt_arch=00
	efi_has_arch=01"
archs["%{arm}"]="efi_alt_arch=none
	efi_alt_arch_upper=NONE
	efi_arch=arm
	efi_arch_upper=ARM
	efi_has_alt_arch=00
	efi_has_arch=01"

common="efi_esp_boot=/boot/efi/EFI/BOOT
	efi_esp_dir=/boot/efi/EFI/fedora
	efi_esp_efi=/boot/efi/EFI
	efi_esp_root=/boot/efi
	efi_vendor=fedora"

output=$(mktemp)

for arch in "${!archs[@]}"; do
	echo "Testing ${arch}"
	rpmbuild -bp --target ${arch}-fedora-linux test.spec \
            | grep -A12 %prep > $output

	for item in ${archs[$arch]}; do
		grep ^$item $output
	done
	for item in ${common}; do
		grep ^$item $output
	done
	echo ""
done
