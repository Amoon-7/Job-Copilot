.PHONY: install lint test up down api ui eval-match eval-grounding

install:
	pip install -e ".[dev,ui]"

lint:
	ruff check . && ruff format --check .

test:
	pytest -q

up:
	docker compose -f infra/docker-compose.yml up --build

down:
	docker compose -f infra/docker-compose.yml down

api:
	uvicorn job_copilot.api.main:app --reload

ui:
	streamlit run src/job_copilot/ui/app.py

eval-match:
	python -m evals.run_matching evals/data/offers_labeled.jsonl

eval-grounding:
	python -m evals.run_grounding evals/data/offers_labeled.jsonl
