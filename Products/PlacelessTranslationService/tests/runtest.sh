#!/bin/sh
# Executes a test Python script
# USAGE:
# runtest.sh testXXX.py

. environ.sh
${PYTHON} $1
