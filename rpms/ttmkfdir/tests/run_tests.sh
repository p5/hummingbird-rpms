#!/bin/bash

if [ -d /tmp/test-ttmkfdir ];then
	rm -rf /tmp/test-ttmkfdir
fi

mkdir /tmp/test-ttmkfdir
cd /tmp/test-ttmkfdir
ttmkfdir -d /usr/share/X11/fonts/TTF .
if [ -f ./fonts.scale ]; then
	diff -urN ./fonts.scale /usr/share/X11/fonts/TTF/fonts.scale
	retval=$?
	echo $retval
	if [ $retval -ne 0 ]; then
		echo "check if xorg-x11-fonts-ethiopic is installed or its packaging is changed"
		exit 1
	else
		echo "ttmkfdir sucessfully generated fonts.scale file for xorg-x11-fonts-ethiopic directory"
	fi
fi


