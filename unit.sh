#!/bin/sh

export PYTHONPATH=lib:../lib:$PYTHONPATH
pylint -E -e F -f parseable lib/*.py scripts/*.py
