# syntax=docker/dockerfile:1
#
# Requires data/dictionary.sqlite to exist before building.
# Run the extractor first: python3 scripts/extract.py path/to/dictionary.mobi

# ── Stage 1: production dependencies ─────────────────────────────────────────
# Runs on the TARGET so native addons (better-sqlite3) compile for the right arch.
FROM node:22-alpine AS deps
RUN apk add --no-cache python3 make g++
WORKDIR /app
COPY package*.json ./
RUN npm ci --omit=dev

# ── Stage 2: build ────────────────────────────────────────────────────────────
# Runs on the BUILD HOST so Rolldown (Vite 8's native bundler) can execute.
# The output is plain JS - no architecture dependency.
FROM --platform=$BUILDPLATFORM node:22-alpine AS builder
RUN apk add --no-cache python3 make g++
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY src ./src
COPY public ./public
COPY svelte.config.js vite.config.ts tsconfig.json ./
COPY data/dictionary.sqlite ./data/dictionary.sqlite
RUN npm run build

# ── Stage 3: production image ─────────────────────────────────────────────────
FROM node:22-alpine
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY --from=builder /app/build ./build
COPY data/dictionary.sqlite ./data/dictionary.sqlite
EXPOSE 3000
ENV NODE_ENV=production
CMD ["node", "build"]
