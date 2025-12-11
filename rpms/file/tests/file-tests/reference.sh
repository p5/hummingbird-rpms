#!/bin/bash -ex

rm -rf reference
mkdir reference

cd db
for d in * ; do
    mkdir "../reference/$d"
    for f in "$d"/* ; do
        if [[ ${f: -11} != ".source.txt" ]]; then
            file "$f" | sed "s|$f: ||" > "../reference/$f.ref"
        fi
    done
done
