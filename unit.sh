#!/bin/sh

export PYTHONPATH=lib:../lib:$PYTHONPATH
pylint -E -e F -f parseable `find lib -name [a-z]\*.py` `find scripts -name [a-z]\*.py`

if [ -e localconfig.json ] ; then rm localconfig.json; fi
coverage run -a --branch --omit='/Library/*,/usr/*,/opt/*' `which nosetests`
for filename in `find lib -name [a-z]\*.py`; do
  coverage run -a --branch --omit='/Library/*,/usr/*,/opt/*' $filename
done
for filename in `find scripts -name [a-z]\*.py` ; do
  coverage run -a --branch --omit='/Library/*,/usr/*,/opt/*' $filename --list-actions
done
if [ -e localconfig.json ] ; then rm localconfig.json; fi

coverage html --omit="/Library/*,/usr/*,/opt/*" -d coverage.new
if [ -e coverage ] ; then
    mv coverage coverage.old
    mv coverage.new coverage
    rm -rf coverage.old
else
    mv coverage.new coverage
fi
