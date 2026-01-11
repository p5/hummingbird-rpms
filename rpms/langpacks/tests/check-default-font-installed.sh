#!/bin/bash
set -e

echo "First check installed langpacks list"
sudo dnf list --installed| grep langpacks

echo "Check hi language"
sudo dnf list --installed|grep google-noto-sans-devanagari-vf-fonts
retval=$?
echo $retval
if [ $retval -ne 0 ]; then
	echo "langpacks-core-hi failed to install google-noto-sans-devanagari-vf-fonts as default font package"
else
	echo "langpacks-core-hi installed with default font google-noto-sans-devanagari-vf-fonts package"
fi

echo "Check ja language"
sudo dnf list --installed|grep google-noto-sans-cjk-vf-fonts
retval=$?
echo $retval
if [ $retval -ne 0 ]; then
        echo "langpacks-core-ja failed to install google-noto-sans-cjk-vf-fonts as default font package"
else
        echo "langpacks-core-ja installed with default font google-noto-sans-cjk-vf-fonts package"
fi

echo "Check zh_CN language"
sudo dnf list --installed|grep google-noto-sans-cjk-vf-fonts
retval=$?
echo $retval
if [ $retval -ne 0 ]; then
        echo "langpacks-core-zh_CN failed to install google-noto-sans-cjk-vf-fonts as default font package"
else
        echo "langpacks-core-zh_CN installed with default font google-noto-sans-cjk-vf-fonts package"
fi

