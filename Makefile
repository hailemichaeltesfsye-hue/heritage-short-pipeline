# Makefile for The Heritage Short AI Filmmaking Pipeline

.PHONY: all film validate test metrics clean serve-api serve-frontend export-showcase build-frontend deploy-static

all: film

film:
	uv run python -m pipeline.run run --stage all --language both

validate:
	uv run python -m pipeline.run validate

test:
	uv run pytest -v

metrics:
	uv run python -m pipeline.run metrics

clean:
	python -c "import shutil, pathlib; [shutil.rmtree(p) for p in pathlib.Path('outputs').glob('*') if p.is_dir()]; [p.unlink() for p in pathlib.Path('outputs').glob('*.*')]"

# ── Phase 4: Showcase UI & FastAPI control tower ──────────────────────────────

serve-api:
	uv run uvicorn api.server:app --reload --port 8000

serve-frontend:
	cd frontend && npm run dev

export-showcase:
	uv run python pipeline/export_showcase.py

build-frontend:
	cd frontend && npm run build

deploy-static: export-showcase build-frontend
	@echo "Static showcase built in frontend/dist/ — ready for Hugging Face Spaces."
