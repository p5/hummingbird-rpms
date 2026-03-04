
# languages
jq -r '."639-2"[] | "\t\(.alpha_2)\t\(.alpha_3)\t\(.name)"' /usr/share/iso-codes/json/iso_639-2.json \
  >iso_639-2.txt
jq -r '."639-3"[] | "\t\(.alpha_3)\t\(.name)"' /usr/share/iso-codes/json/iso_639-3.json \
  >iso_639-3.txt
# territories
jq -r '."3166-1"[] | "\(.alpha_2)\t\(.name)"' /usr/share/iso-codes/json/iso_3166-1.json \
  >iso_3166.txt
# scripts
jq -r '."15924"[] | "\(.alpha_4)\t\(.name)"' /usr/share/iso-codes/json/iso_15924.json \
  >iso_15924.txt

# Locale format:
# - language[_territory][@modifier]
# - language_SCRIPT
# - language[_territory[.charset]][@modifier]

# FYI: Add \. into the sed expression to include locales with charset - language[_territory[.charset]][@modifier]:
#       | sed -E 's/([a-zA-Z0-9_@-\.]+).*/\1/; s/_$//; s/-$//' \
#
# 1. Ask repoquery for files under /usr/share/locale/*
# 2. Somehow the repoquery outputs other directories other than /usr/share/locale/, so skip them
# 3. Skip all_languages|currency|locale.alias
# 4. Skip charset in language[_territory[.charset]][@modifier] and keep only language[_territory][@modifier]
repoquery --quiet --available --list --file='/usr/share/locale/*' --setopt=\*.skip_if_unavailable=true \
    | grep -E '/usr/share/locale/' \
    | sed -E 's|^(/[^/]+){3}/([^/]+).*|\2|' \
    | grep -E -v 'all_languages|currency|locale.alias' \
    | sed -E 's/([a-zA-Z0-9_@-]+).*/\1/; s/_$//; s/-$//' \
    | sort | uniq > lang-exceptions.repoquery

cat <<EOF_HEADER > lang-exceptions
# Updated: `date`
#
# This file contains a list of locales for which we ship translations.
#
# Run this to update the list:
#
# . generate-lang-exceptions.sh
#
EOF_HEADER

cat lang-exceptions.repoquery | grep -v "^#" | while read loc ; do
    locale=$loc
    territory=
    special=
    # Locale format:
    # - language[_territory][@modifier]
    # - language_SCRIPT
    # - language[_territory[.charset]][@modifier]
    # TODO: BCP 47 style zh-Hant falls to special category
    [[ "$locale" =~ "@" ]] && locale=${locale%%@*}
    [[ "$locale" =~ "_" ]] && territory=${locale##*_}
    [[ "$loc" =~ "_" ]] || [[ "$loc" =~ "@" ]] || special=$loc
    [[ "$territory" =~ "." ]] && territory=${territory%%.*}

    # If the territory is not official, skip it
    if [ -n "$territory" ]; then
        grep -q "^$territory" iso_3166.txt
        IsItTerritory=$?
        # territory can be script
        grep -q "^$territory" iso_15924.txt
        IsItScript=$?
        [[ $IsItTerritory -eq 1 && $IsItScript -eq 1 ]] && continue
    fi
    # If the locale is not official and not special, skip it
    if [ -z "$special" ]; then
        grep -E -q "[[:space:]]${locale%%_*}[[:space:]]" \
           iso_639-2.txt iso_639-3.txt || continue
    fi
    echo $loc >> lang-exceptions
done

cat <<EOF_MANUAL >> lang-exceptions
#
# Manual additions:
#
# The standard: UN M49 https://unstats.un.org/unsd/methodology/m49/ -> Geographic Regions -> Latin America and the Caribbean 419
es_419

# Own directories for actively used locales with charset definition:
own_charset:cs.cp1250
own_charset:de.us-ascii
own_charset:es.us-ascii
own_charset:fr.us-ascii
own_charset:ja.euc-jp
own_charset:nl.us-ascii
own_charset:no.us-ascii
own_charset:pt_BR.us-ascii
own_charset:pt.us-ascii
own_charset:sk.cp1250
own_charset:zh_CN.GB2312
own_charset:zh_TW.Big5
EOF_MANUAL

rm -f iso_639-2.txt iso_639-3.txt iso_3166.txt
rm -f lang-exceptions.repoquery

# Not added:
#
# /usr/share/locale/es_EU
#
# EU in es_EU is not a territory/script defined by ISO 3166/ISO 15924, glibc, or common
# i18n standards - a custom or erroneous locale name, unlike es_ES or es_419.
#
# Provided by hunspell pkg.

# Command cheat sheet:
#
# Find a package name that provides directory /usr/share/locale/es_EU ('*' is important otherwise output is empty):
#
# $ repoquery -q --queryformat '%{name}' --file '/usr/share/locale/es_EU*'
# hunspell
# $
#
# List files provided by hunspell:
#
# $ repoquery --list hunspell
#
# Find directories under /usr/share/locale/ not owned by any package:
#
# while read locale; do for pkg in $(repoquery --quiet --queryformat '%{name}' --file "/usr/share/locale/${locale}*" --setopt=\*.skip_if_unavailable=true); do FOUND=$(repoquery --quiet --list $pkg --setopt=\*.skip_if_unavailable=true | grep "^/usr/share/locale/${locale}$"); if [ ! -z "$FOUND" ]; then break; fi; done; if [ -z "$FOUND" ]; then echo "haven't found owner of: /usr/share/locale/$locale"; fi done < <(cat lang-exceptions.repoquery) | tee locales-not-owned-by-anyone.log
#
# Find actively used locales with charset definition:
#
# while read Input; do echo INPUT: $Input; repoquery -q --queryformat '%{name}' --file "/usr/share/locale/$Input/*"; done < <(grep '\.' lang-exceptions.repoquery | grep -v '^#')

