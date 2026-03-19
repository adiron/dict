# dict

A local Dutch - English dictionary reader, backed by a `.mobi` dictionary file.

## Setup

Source a `.mobi` dictionary file, then:

```bash
# Python extractor (one-time)
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
npm run data:make -- path/to/dictionary.mobi

# App
npm install
npm run dev
```

The database only needs to be regenerated if you change the source file or the extractor.

## Commands

| Command | What it does |
|---|---|
| `npm run data:make -- <file.mobi>` | Extract MOBI into `data/dictionary.sqlite` |
| `npm run dev` | Start the dev server |
| `npm run build` | Production build |
| `npm run check` | Type check |
| `npm test` | Run tests |
