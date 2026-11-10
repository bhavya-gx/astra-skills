#!/bin/sh
cd "$(dirname "$0")" || exit 1
if ! command -v python3 >/dev/null 2>&1; then
  echo "Install Python 3.12 or newer from https://www.python.org/downloads/ and try again."
  read -r answer
  exit 1
fi
python3 bootstrap.py
status=$?
if [ "$status" -ne 0 ]; then read -r answer; fi
exit "$status"
