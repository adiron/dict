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

## Docker

Build and run locally:

```bash
docker build -t dict .
docker run -p 3000:3000 dict
```

### Cross-building for Raspberry Pi (ARMv7) on Apple Silicon

The build stage runs on the host so Vite's native bundler (Rolldown) can execute. Only the runtime deps compile under emulation, which is fast on arm64.

Start a local registry and a multi-platform builder:

```bash
docker run -d -p 5000:5000 registry:2

# buildkitd.toml - needed if your registry is HTTP (e.g. over Tailscale)
cat > buildkitd.toml <<'EOF'
[registry."<host>:5000"]
  http = true
EOF

docker buildx create --use --name multiarch --config buildkitd.toml
```

Build and push:

```bash
docker buildx build --platform linux/arm/v7 \
  -t <host>:5000/dict:armv7 --push .
```

Pull and run on the Pi (add `<host>:5000` to `insecure-registries` in `/etc/docker/daemon.json` first):

```bash
docker pull <host>:5000/dict:armv7
docker run -p 3000:3000 <host>:5000/dict:armv7
```
