# Aegis Anti Fraud — perintah operasional (T-01).
.DEFAULT_GOAL := help
COMPOSE := docker compose

.PHONY: help up down build logs ps test lint fmt migrate train clean

help: ## Tampilkan bantuan
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	  awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'

up: ## Nyalakan seluruh service (build bila perlu)
	$(COMPOSE) up -d --build

down: ## Matikan seluruh service
	$(COMPOSE) down

build: ## Build image backend
	$(COMPOSE) build

logs: ## Ikuti log semua service
	$(COMPOSE) logs -f

ps: ## Status service
	$(COMPOSE) ps

test: ## Jalankan test backend di dalam container api
	$(COMPOSE) run --rm -e AEGIS_HEALTH_URL=http://api:8000/health api pytest -q

lint: ## Lint backend (ruff)
	$(COMPOSE) run --rm api ruff check .

fmt: ## Format backend (ruff)
	$(COMPOSE) run --rm api ruff format .

migrate: ## Jalankan migrasi DB (diisi di T-02)
	@echo "migrate: belum diimplementasikan (lihat task T-02)"

train: ## Jalankan pipeline retraining (diisi di T-17)
	@echo "train: belum diimplementasikan (lihat task T-17)"

clean: ## Matikan + hapus volume (HATI-HATI: data hilang)
	$(COMPOSE) down -v
