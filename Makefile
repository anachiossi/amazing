# STUB — targets are in place, but the program itself is not written yet.
# The rules below are the ones the subject requires, plus a test target.

PYTHON  := python3
MAIN    := a_maze_ing.py
CONFIG  := config.txt

MYPY_FLAGS := --warn-return-any --warn-unused-ignores \
	          --ignore-missing-imports --disallow-untyped-defs \
	          --check-untyped-defs

.PHONY: install run debug clean lint lint-strict test help

help:
	@echo "install      install the project dependencies"
	@echo "run          run the generator on $(CONFIG)"
	@echo "debug        run it under pdb"
	@echo "test         run the unit tests"
	@echo "lint         flake8 + mypy with the required flags"
	@echo "lint-strict  flake8 + mypy --strict"
	@echo "clean        remove caches and build artefacts"

install:
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install flake8 mypy
	$(PYTHON) -m pip install -e .

run:
	$(PYTHON) $(MAIN) $(CONFIG)

debug:
	$(PYTHON) -m pdb $(MAIN) $(CONFIG)

test:
	$(PYTHON) -m unittest discover -s tests -t .

lint:
	flake8 .
	mypy . $(MYPY_FLAGS)

lint-strict:
	flake8 .
	mypy . --strict

clean:
	rm -rf .mypy_cache .pytest_cache build dist *.egg-info
	find . -type d -name __pycache__ -not -path "./mlx/*" \
	      -exec rm -rf {} + 2>/dev/null || true
