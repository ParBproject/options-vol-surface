PY ?= python
.PHONY: all verify analyze readme lint test fetch
all: verify analyze readme lint test
fetch:        ## ONLINE: re-download raw data (changes hashes; not part of `all`)
	$(PY) scripts/fetch_data.py && $(PY) scripts/manifest.py
verify:
	$(PY) scripts/manifest.py --check
analyze:
	PYTHONPATH=src $(PY) -m volsurf.analysis
readme:
	PYTHONPATH=src $(PY) scripts/build_readme.py
lint:
	$(PY) -m ruff check .
test:
	$(PY) -m pytest -q
