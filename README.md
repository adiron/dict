# dict

A local Dutch - English dictionary reader, backed by a `.mobi` dictionary file.

## Setup

Source a `.mobi` dictionary file, then:

```bash
# 1. Create and activate the Python virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Extract the dictionary (one-time, produces data/dictionary.sqlite)
python3 scripts/extract.py path/to/dictionary.mobi

# 4. Install Node dependencies and start the app
npm install
npm run dev
```

The database only needs to be regenerated if you change the source file or the extractor.

## Commands

| Command | What it does |
|---|---|
| `python3 scripts/extract.py <file.mobi>` | Extract MOBI into `data/dictionary.sqlite` |
| `python3 scripts/extract.py <file.mobi> --keep-html` | Same, but skip body HTML cleanup |
| `npm run dev` | Start the dev server |
| `npm run build` | Production build |
| `npm run check` | Type check |
| `npm test` | Run tests |
