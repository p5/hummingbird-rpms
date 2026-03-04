
git clone https://src.fedoraproject.org/rpms/glibc.git
pushd glibc
wget `awk -v pkg="glibc" '/^SHA/ {gsub(/[()]/,"",$2); print "https://src.fedoraproject.org/lookaside/pkgs/"pkg"/"$2"/sha512/"$4"/"$2}' sources`
SOURCES=`awk '/^SHA/ {gsub(/[()]/,"",$2); print $2}' sources`
tar -xf $SOURCES
cp `echo $SOURCES | sed -e 's/.tar.*//'`/localedata/SUPPORTED ../glibc-SUPPORTED
popd
rm -rf glibc

sed -i -e 's/SUPPORTED-LOCALES=/SUPPORTED_LOCALES="/' glibc-SUPPORTED
echo "\"" >> glibc-SUPPORTED

cat <<EOF_HEADER > glibc-SUPPORTED.locales
# Updated: `date`
#
# This file contains a list of locales supported by glibc.
#
# Run this to update the list:
#
# . generate-glibc-supported-locales.sh
#
EOF_HEADER

# Locale format:
# - language[_territory][@modifier]
# - language_SCRIPT
# - language[_territory[.charset]][@modifier]

. glibc-SUPPORTED
# Skip charset in language[_territory[.charset]][@modifier] and keep only language[_territory][@modifier]
for i in $SUPPORTED_LOCALES; do echo $i | sed -E 's/([a-zA-Z0-9_@-]+).*/\1/; s/_$//; s/-$//' ; done | sort | uniq >> glibc-SUPPORTED.locales

rm -f glibc-SUPPORTED

