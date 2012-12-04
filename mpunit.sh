#!/bin/bash

set -x

###########################################################################
# This requires coverage and nosetests:
#
#  easy_install coverage
#  easy_install nose
#  easy_install pylint
#  easy_install pyflakes
#
# test_base_vcs_mercurial.py requires hg >= 1.6.0 with mq, rebase, share
# extensions to fully test.
###########################################################################

# this breaks mercurial unit tests
unset HG_SHARE_BASE_DIR

COVERAGE_ARGS="--omit='/usr/*,/opt/*'"
OS_TYPE='linux'
uname -v | grep -q Darwin
if [ $? -eq 0 ] ; then
  OS_TYPE='osx'
  COVERAGE_ARGS="--omit='/Library/*,/usr/*,/opt/*'"
fi
uname -s | egrep -q MINGW32   # Cygwin will be linux in this case?
if [ $? -eq 0 ] ; then
  OS_TYPE='windows'
fi
NOSETESTS=`env which nosetests`

#echo "### Finding mozharness/ .py files..."
#files=`find mozharness -name [a-z]\*.py`
#if [ $OS_TYPE == 'windows' ] ; then
#  MOZHARNESS_PY_FILES=""
#  for f in $files; do
#    file $f | grep -q "Assembler source"
#    if [ $? -ne 0 ] ; then
#      MOZHARNESS_PY_FILES="$MOZHARNESS_PY_FILES $f"
#    fi
#  done
#else
#  MOZHARNESS_PY_FILES=$files
#fi
echo "### Finding scripts/ .py files..."
files=`find scripts -name [a-z]\*.py`
if [ $OS_TYPE == 'windows' ] ; then
  SCRIPTS_PY_FILES=""
  for f in $files; do
    file $f | grep -q "Assembler source"
    if [ $? -ne 0 ] ; then
      SCRIPTS_PY_FILES="$SCRIPTS_PY_FILES $f"
    fi
  done
else
  SCRIPTS_PY_FILES=$files
fi
export PYTHONPATH=`env pwd`:$PYTHONPATH

rm -rf logs
#rm -rf build logs
if [ ! -d build ]; then
    virtualenv-2.7 --no-site-packages build/venv
    build/venv/bin/pip install requests
fi

if [ $OS_TYPE != 'windows' ] ; then
  echo "### Testing mozpool unit tests"
  coverage run -a --branch $COVERAGE_ARGS $NOSETESTS test/mozpool/test_*.py
  echo "### Running *.py [--list-actions]"
else
  echo "### Running nosetests..."
  nosetests
fi
#rm -rf build logs
