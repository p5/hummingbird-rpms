#!/bin/sh -e

if [ $# -lt 1 ]; then
    echo "What?"
    exit 1
fi

repo="https://svn.apache.org/repos/asf/httpd/httpd/trunk"
repo="https://svn.apache.org/repos/asf/httpd/httpd/branches/2.4.x"
ver=$(rpm -q --specfile httpd.spec --qf '%{VERSION}\n' | sed 1q)
prefix="httpd-${ver}"
suffix="${SUFFIX:-r$1${2:++}}"
fn="${prefix}-${suffix}.patch"
vcurl="http://svn.apache.org/viewvc?view=revision&revision="

if test -f ${fn}; then
    mv -v -f ${fn} ${fn}\~
    echo "# $0 $*" > ${fn}
    sed '1{/#.*pullrev/d;};/^--- /,$d' < ${fn}\~ >> ${fn}
else
    echo "# $0 $*" > ${fn}
fi

new=0
for r in $*; do
   case $r in
        http*) url=$r ;;
        *) url=${vcurl}${r} ;;
   esac
   if ! grep -q "^${url}" ${fn}; then
       echo "${url}"
       new=1
   fi
done >> ${fn}

[ $new -eq 0 ] || echo >> ${fn}

prev=/dev/null
for r in $*; do
    echo "+ fetching ${r}"
    this=`mktemp /tmp/pullrevXXXXXX`
    case $r in
        http*) curl -s "$r" | filterdiff --strip=3 ;;
        *) svn diff -c ${r} ${repo}  ;;
    esac | filterdiff --remove-timestamps --clean \
                      -x 'CHANGES' -x 'changes-entries/*.txt' \
                      -x '*/next-number' -x 'STATUS' -x '*.xml' \
                      -x '.github/*' \
                      --addprefix="${prefix}/" > ${this}
    next=`mktemp /tmp/pullrevXXXXXX`
    if ! combinediff -w ${prev} ${this} > ${next}; then
        echo "Failed combining previous ${prev} with ${this}";
        exit 1
    fi
    rm -f "${this}"
    [ "${prev}" = "/dev/null" ] || rm -f "${prev}"
    prev=${next}
done

cat ${prev} >> ${fn}

vi "${fn}"
echo "+ git add ${fn}" 
git add "${fn}"
echo "+ spec template:"
echo "PatchN: ${fn}"
