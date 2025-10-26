.PHONY: build up test
build:
	docker-compose build

up:
	docker-compose up --build

test:
	pytest -q
