#!/bin/sh

export PYTHONPATH=lib:../lib:$PYTHONPATH
pylint -E -e F -f parseable lib/*.py scripts/*.py

coverage run -a --branch `which nosetests`

coverage html -d coverage.new
if [ -e coverage ] ; then
	mv coverage coverage.old
	mv coverage.new coverage
	rm -rf coverage.old
else
	mv coverage.new coverage
fi
