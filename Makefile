PY ?= python3
.PHONY: all data build analyze layout figures paper web hf-dataset clean
all: build analyze figures paper
data:
	bash scripts/get_data.sh
build:
	cd src && $(PY) build.py
analyze:
	cd src && $(PY) analyze.py
layout:
	cd src && $(PY) layout.py
figures: layout
	cd src && $(PY) fig_hero.py 5000 all && $(PY) fig_hero.py 2400 collapsed && $(PY) fig_flows.py && $(PY) fig_more.py
paper:
	cd src && $(PY) make_macros.py
	cd paper && pdflatex -interaction=nonstopmode paper.tex >/dev/null && pdflatex -interaction=nonstopmode paper.tex >/dev/null && echo "built paper/paper.pdf"
web:
	$(PY) scripts/build_web_paper.py
hf-dataset:
	$(PY) scripts/make_hf_dataset.py
clean:
	rm -rf data/processed paper/*.aux paper/*.log paper/*.out src/__pycache__
