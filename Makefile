.PHONY: install harvest download ocr index search run-all clean clean-all test lint

UV := uv

install:
	$(UV) sync

harvest:
	$(UV) run unimap harvest

download:
	$(UV) run unimap download

ocr:
	$(UV) run unimap ocr --spotter paddle

index:
	$(UV) run unimap index

search:
	@test -n "$(Q)" || (echo "Usage: make search Q='your query'"; exit 1)
	$(UV) run unimap search "$(Q)"

run-all:
	$(UV) run unimap run-all

clean:
	rm -rf data/patches data/ocr_raw
	@echo "Cleaned intermediate files. Images and results preserved."

clean-all:
	rm -rf data
	@echo "Cleaned all data."

test:
	$(UV) run pytest tests/ -v

lint:
	$(UV) run ruff check src/ tests/
