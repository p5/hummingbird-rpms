jq -r '."639-2"[] | "\t\(.alpha_2)\t\(.alpha_3)\t\(.name)"' /usr/share/iso-codes/json/iso_639-2.json > iso_639-2.tab

cat <<EOF_HEADER > iso_639-2.locales
# Updated: `date`
#
# This file contains a list of locales from ISO 639-2 standard.
#
# Run this to update the list:
#
# . generate-iso_639-2-locales.sh
#
EOF_HEADER

cat iso_639-2.tab | while read alpha_2 alpha_3 name ; do
    [[ "$name" =~ "Reserved" ]] && continue
    [[ "$name" =~ "No linguistic" ]] && continue

    locale=$alpha_2
    if [ "$locale" = "null" ]; then
        locale=$alpha_3
    fi
    echo $locale >> iso_639-2.locales
done

rm -f iso_639-2.tab

