.PHONY: test clean

test:
	PYTHONPATH=src python3 -m unittest discover -s tests -t . -v

clean:
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
