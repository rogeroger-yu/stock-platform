.PHONY: dev test build clean

dev:
	docker compose up --build

test:
	cd backend && python -m pytest tests/ -v

build:
	docker compose build

clean:
	docker compose down -v
