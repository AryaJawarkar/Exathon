.PHONY: help setup db data load pipeline app clean smoke

help:
	@echo "make setup     - install Python deps"
	@echo "make db        - start Exasol Personal (docker compose)"
	@echo "make data      - generate synthetic fragmented channel data"
	@echo "make load      - create schema + unify channels into Exasol"
	@echo "make pipeline  - data + load"
	@echo "make app       - launch the Streamlit dashboard"
	@echo "make smoke     - run offline smoke tests (no DB needed)"
	@echo "make clean     - remove generated data"

setup:
	pip install -r requirements.txt

db:
	docker compose up -d
	@echo "Exasol starting; first boot ~2-3 min. Watch: docker compose logs -f exasol"

data:
	python -m src.data.generate_synthetic_data

load:
	python -m src.etl.load

pipeline: data load

app:
	streamlit run app/Home.py

smoke:
	python -m tests.smoke

clean:
	rm -f data/raw/*.csv data/processed/*.csv
