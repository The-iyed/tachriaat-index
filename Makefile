PYTHON ?= python3

.PHONY: export-sheet-json export-sheet-json-matrix export-sheet-json-kv-array export-sheet-json-matrix-rows export-sheet-json-matrix-flat export-sheet-english convert-sheet-embedding run-embeddings install-deps

install-deps:
	$(PYTHON) -m pip install --upgrade pip | cat
	$(PYTHON) -m pip install -r requirements.txt | cat

export-sheet-json: requirements.txt scripts/export_sheet_json.py sheet.xlsx
	$(PYTHON) scripts/export_sheet_json.py sheet.xlsx sheet.json --mode matrix --matrix-output records | cat

export-sheet-json-matrix: requirements.txt scripts/export_sheet_json.py sheet.xlsx
	$(PYTHON) scripts/export_sheet_json.py sheet.xlsx sheet.json --mode matrix | cat

export-sheet-json-kv-array: requirements.txt scripts/export_sheet_json.py sheet.xlsx
	$(PYTHON) scripts/export_sheet_json.py sheet.xlsx sheet.json --mode kv | cat

export-sheet-json-matrix-rows: requirements.txt scripts/export_sheet_json.py sheet.xlsx
	$(PYTHON) scripts/export_sheet_json.py sheet.xlsx sheet.json --mode matrix | cat

export-sheet-json-matrix-flat: requirements.txt scripts/export_sheet_json.py sheet.xlsx
	$(PYTHON) scripts/export_sheet_json.py sheet.xlsx sheet.json --mode matrix | cat

export-sheet-english: requirements.txt scripts/export_sheet_english.py sheet.xlsx
	$(PYTHON) scripts/export_sheet_english.py sheet.xlsx sheet_english.json | cat

convert-sheet-embedding: requirements.txt scripts/convert_sheet_embedding.py sheet_english.json
	AZURE_OPENAI_API_KEY=$$AZURE_OPENAI_API_KEY \
	AZURE_OPENAI_ENDPOINT=$$AZURE_OPENAI_ENDPOINT \
	AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME=$$AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME \
	$(PYTHON) scripts/convert_sheet_embedding.py sheet_english.json sheet_english_embedded.json --batch-size 4 --max-retries 6 --retry-wait 2 --timeout 120 | cat

run-embeddings: requirements.txt scripts/convert_sheet_embedding.py sheet_english.json
	AZURE_OPENAI_API_KEY=$$AZURE_OPENAI_API_KEY \
	AZURE_OPENAI_ENDPOINT=$$AZURE_OPENAI_ENDPOINT \
	AZURE_OPENAI_API_VERSION=$$AZURE_OPENAI_API_VERSION \
	AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME=$$AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME \
	AZURE_OPENAI_DEPLOYMENT_NAME=$$AZURE_OPENAI_DEPLOYMENT_NAME \
	$(PYTHON) scripts/convert_sheet_embedding.py sheet_english.json sheet_english_embedded.json --batch-size 4 --max-retries 6 --retry-wait 2 --timeout 120 | cat


