# STUB — targets are in place, but the program itself is not written yet.
# The rules below are the ones the subject requires, plus a test target.

PYTHON  := python3
MAIN    := a_maze_ing.py
CONFIG  := config.txt

# Everything runs inside a local virtualenv, so the machine's own
# Python is never touched and a checkout only needs "make".
VENV    := .venv
VPYTHON := $(VENV)/bin/python
# Written once the dependencies are in: the other targets depend on it,
# so they install what they need the first time and skip it afterwards.
STAMP   := $(VENV)/.installed

# Colours for the help screen. ESC is built with printf so the escape
# character is stored literally and any echo prints it as it is.
ESC     := $(shell printf '\033')
BOLD    := $(ESC)[1m
DIM     := $(ESC)[2m
CYAN    := $(ESC)[36m
GREEN   := $(ESC)[32m
YELLOW  := $(ESC)[33m
MAGENTA := $(ESC)[35m
RED     := $(ESC)[31m
RESET   := $(ESC)[0m

MYPY_FLAGS := --warn-return-any --warn-unused-ignores \
	          --ignore-missing-imports --disallow-untyped-defs \
	          --check-untyped-defs

.PHONY: install run debug demo preview clean fclean lint lint-strict \
        test check-all help

# First target of the file, so a bare "make" lands here.
help:
	@printf '$(CYAN)$(BOLD)'
	@printf '%s\n' \
	'    ___         __  ___                       _' \
	'   /   |       /  |/  /___ _____  ___        (_)___  ____ _' \
	'  / /| |______/ /|_/ / __ `/_  / / _ \______/ / __ \/ __ `/' \
	' / ___ /_____/ /  / / /_/ / / /_/  __/_____/ / / / / /_/ /' \
	'/_/  |_|    /_/  /_/\__,_/ /___/\___/     /_/_/ /_/\__, /' \
	'                                                  /____/'
	@printf '$(RESET)$(DIM)%s$(RESET)\n\n' 'developed by anade-mo and ltamiano'
	@printf '$(GREEN)$(BOLD)%s$(RESET)\n' 'Build and run'
	@printf '  $(BOLD)%-12s$(RESET) %s\n' \
	'install' 'create $(VENV) and install the dependencies' \
	'run'     'draw the maze $(CONFIG) asks for, fitted to the terminal' \
	'debug'   'run it under pdb'
	@printf '\n$(MAGENTA)$(BOLD)%s$(RESET)\n' 'Preview'
	@printf '  $(BOLD)%-12s$(RESET) %s\n' \
	'demo'    'draw a maze step by step, then animate it' \
	'preview' 'same as run: the maze fitted to this terminal'
	@printf '\n$(YELLOW)$(BOLD)%s$(RESET)\n' 'Checks'
	@printf '  $(BOLD)%-12s$(RESET) %s\n' \
	'check-all'   'run the tests and the strict linting, all at once' \
	'test'        'run the unit tests' \
	'lint'        'flake8 + mypy with the required flags' \
	'lint-strict' 'flake8 + mypy --strict'
	@printf '\n$(RED)$(BOLD)%s$(RESET)\n' 'Housekeeping'
	@printf '  $(BOLD)%-12s$(RESET) %s\n' \
	'clean'  'remove caches and build artefacts' \
	'fclean' 'clean, and remove $(VENV) as well'
	@printf '\n'
	@printf '$(DIM)%s$(RESET)\n' \
	'First time here: run "make install" once, then any target above.' \
	'The package lives in src/, so outside $(VENV) it is not on the path:' \
	'  PYTHONPATH=src python3 -m app.render.terminal_demo' \
	'  PYTHONPATH=src python3 -m unittest discover -s tests -t .'

install: $(STAMP)

# Remade when pyproject.toml changes, since it is the only place the
# dependencies are declared. "-e ." installs the package itself in
# editable mode, "[dev]" adds the tools the checks need.
$(STAMP): pyproject.toml
	$(PYTHON) -m venv $(VENV)
	$(VPYTHON) -m pip install --upgrade pip
	$(VPYTHON) -m pip install -e .[dev]
	touch $(STAMP)

run: $(STAMP)
	$(VPYTHON) $(MAIN) $(CONFIG)

debug: $(STAMP)
	$(VPYTHON) -m pdb $(MAIN) $(CONFIG)

# The renderer drawn one step at a time — canvas, floor, walls,
# border, junctions, path, marks, title — and then the same maze
# animated. It pauses once, before the animation.
demo: $(STAMP)
	$(VPYTHON) -m app.render.terminal_demo

# The maze $(CONFIG) asks for, drawn at whatever size the terminal
# can take: full cells if there is room, blocks if there is not. Same
# thing "run" does, since that is now all the program does.
preview: run
test: $(STAMP)
	$(VPYTHON) -m unittest discover -s tests -t .

lint: $(STAMP)
	$(VPYTHON) -m flake8 .
	$(VPYTHON) -m mypy . $(MYPY_FLAGS)

lint-strict: $(STAMP)
	$(VPYTHON) -m flake8 .
	$(VPYTHON) -m mypy . --strict

# Everything at once, in the order that fails fastest: the tests first,
# then the strictest linting. Make stops at the first command that
# fails, so a green run means the whole project is in order.
check-all: test lint-strict
	@printf '$(GREEN)$(BOLD)%s$(RESET)\n' 'tests and strict linting: all good'

clean:
	rm -rf .mypy_cache .pytest_cache build dist *.egg-info
	find . -type d -name __pycache__ -not -path "./mlx/*" \
	      -exec rm -rf {} + 2>/dev/null || true

# The virtualenv is rebuilt by any target that needs it, so removing it
# is safe; kept apart from clean because rebuilding costs a download.
fclean: clean
	rm -rf $(VENV)
