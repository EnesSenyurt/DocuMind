# --- Build stage ---
# Debian-based (glibc), not Alpine: Rollup/esbuild ship platform-specific native
# binaries as optional npm dependencies, and npm has a long-standing bug
# (npm/cli#4828) where a lockfile resolved on a glibc host can install the wrong
# (or no) binary on musl/Alpine, making `vite build` fail with a cryptic
# "Cannot find module @rollup/rollup-linux-*-musl" error. Debian sidesteps the
# whole class of failure.
FROM node:20-bookworm-slim AS build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

# --- Serve stage ---
FROM nginx:1.27-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80
