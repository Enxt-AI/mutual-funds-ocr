# ─── Admin Panel Dockerfile ───────────────────────────────────
# Multi-stage build for Next.js standalone output

FROM node:20-alpine AS base

# ─── Stage 1: Install dependencies ─────────────────────────
FROM base AS deps
WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci --only=production

# ─── Stage 2: Build the application ────────────────────────
FROM base AS builder
WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci

COPY . .

# Build Next.js (standalone mode)
RUN npm run build

# ─── Stage 3: Production runner ────────────────────────────
FROM base AS runner
WORKDIR /app

ENV NODE_ENV=production
ENV PORT=3001
ENV HOSTNAME="0.0.0.0"

# Create non-root user
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

# Copy standalone build
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

USER nextjs

EXPOSE 3001

CMD ["node", "server.js"]
