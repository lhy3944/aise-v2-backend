# ---- Build stage ----
FROM node:20-alpine AS builder

WORKDIR /app

ARG NEXT_PUBLIC_API_URL=""
ARG BACKEND_URL="http://localhost:8081"
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}
ENV BACKEND_URL=${BACKEND_URL}

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

# ---- Run stage ----
FROM node:20-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production
ENV HOSTNAME="0.0.0.0"

COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

EXPOSE 3000

CMD ["node", "server.js"]
