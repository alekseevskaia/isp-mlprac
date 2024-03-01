#!/bin/bash
python3 -m venv --system-site-packages ./.venv
. .venv/bin/activate
pip install -r requirements.txt

mlcourse-evaluate
STATUS=$?

deactivate
rm -rf ./.venv
exit $STATUS
