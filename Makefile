.PHONY: install install-dev uninstall test build clean

install:
	./install.sh

install-dev:
	./install.sh --link

uninstall:
	./uninstall.sh

test:
	PYTHONPATH=src python3 -m unittest discover -s tests -t . -v

build:
	python3 scripts/build_zipapp.py dist/miscree
	chmod +x dist/miscree

clean:
	rm -rf dist
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
