set -ex

rpm -D '%_distro_extra_cflags -Wall' -E %{build_cflags} | grep -e '\-Wall\s*$'
rpm -D '%_distro_extra_cxxflags -Wall' -E %{build_cxxflags} | grep -e '\-Wall\s*$'
rpm -D '%_distro_extra_ldflags -Wall' -E %{build_ldflags} | grep -e '\-Wall\s*$'
rpm -D '%_distro_extra_fflags -Wall' -E %{build_fflags} | grep -e '\-Wall\s*$'
