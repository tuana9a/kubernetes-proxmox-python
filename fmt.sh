#!/bin/bash

.venv/bin/yapf -ir \
*.py \
examples/*.py \
cloud-imgs/**/*.py \
app/ \
cli/
