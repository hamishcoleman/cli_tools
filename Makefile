
# Just the packages needed to run lint
PACKAGES+=flake8

PYTHON=$(wildcard *.py)

all:
	@echo Pure Python package - nothing to build

build-dep:
	sudo apt-get install $(PACKAGES)

lint:
	flake8
