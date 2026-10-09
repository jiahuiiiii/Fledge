#!/bin/zsh
cd -- "${0:A:h}"
if [[ ! -x .venv/bin/python ]]; then
  echo 'Run the setup steps in README.md first.'
  read '?Press Return to close.'
  exit 1
fi
.venv/bin/python run.py --open
read '?Press Return to close.'
