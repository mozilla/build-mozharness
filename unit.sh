#!/bin/sh

export PYTHONPATH=lib:../lib:$PYTHONPATH
pylint -E -e F -f parseable lib/*.py scripts/*.py

coverage run -a --branch --omit='/Library/*,/usr/*,/opt/*' `which nosetests`
rm localconfig.json
for file in lib/*.py; do
  coverage run -a --branch --omit='/Library/*,/usr/*,/opt/*' $file | egrep -v '^(PASS|###)'
done
rm localconfig.json

coverage html --omit="/Library/*,/usr/*,/opt/*" -d coverage.new
if [ -e coverage ] ; then
	mv coverage coverage.old
	mv coverage.new coverage
	rm -rf coverage.old
else
	mv coverage.new coverage
fi
