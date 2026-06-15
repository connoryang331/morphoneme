.PHONY: install install-dev test doctest unittest clean build

install:
	pip install .

install-dev:
	pip install -e .

test: doctest unittest

doctest:
	python -m doctest morph_query/mq.py -v

unittest:
	python -m unittest discover -s tests -v

clean:
	rm -rf build/ dist/ *.egg-info/ __pycache__/
	rm -rf morph_query/__pycache__/
	rm -rf morph_query/*.pyc
	find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null; true

build:
	python -m build
