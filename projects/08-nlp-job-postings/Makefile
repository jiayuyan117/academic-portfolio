PYTHON ?= python
.PHONY: setup data reproduce verify smoke test
setup:
	$(PYTHON) -m pip install -r requirements.txt
data:
	$(PYTHON) run.py data
reproduce:
	$(PYTHON) run.py reproduce
verify:
	$(PYTHON) run.py verify
smoke:
	$(PYTHON) run.py smoke
test:
	$(PYTHON) run.py test
