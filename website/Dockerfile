# ─── Website Dockerfile ───────────────────────────────────────
# Runner uses python:3.11-slim base + Node.js copied from builder
# Build context: project root

# ── Node.js build stage ──────────────────────────────────────
FROM node:20-slim AS builder
WORKDIR /app

COPY website/package.json website/package-lock.json* ./
RUN npm ci

COPY website/ .
RUN npm run build

# ── Production runner (Python base + Node binary) ────────────
FROM python:3.11-slim AS runner
WORKDIR /app

ENV NODE_ENV=production
ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

# Copy Node.js binary from builder
COPY --from=builder /usr/local/bin/node /usr/local/bin/node

# Install Python dependencies for the extractor
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt && \
    rm /tmp/requirements.txt

# Create non-root user
RUN groupadd --system --gid 1001 nodejs && \
    useradd --system --uid 1001 nextjs

# Create data directories with correct ownership
RUN mkdir -p /data/factsheets /data/output /extractor && \
    chown -R nextjs:nodejs /data /extractor

# Copy standalone build
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public

# Copy extractor script
COPY --chown=nextjs:nodejs gemini_extractor.py /extractor/gemini_extractor.py

USER nextjs

EXPOSE 3000
CMD ["node", "server.js"]
