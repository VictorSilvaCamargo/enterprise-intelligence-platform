FROM node:22-alpine AS builder

WORKDIR /app

COPY package.json ./
RUN npm install --no-audit --no-fund

COPY . .

ARG VITE_API_BASE_URL=http://localhost:8000
ARG VITE_APP_NAME="Enterprise Intelligence Platform"
ARG VITE_HEALTH_POLL_INTERVAL_MS=30000

ENV VITE_API_BASE_URL=${VITE_API_BASE_URL} \
    VITE_APP_NAME=${VITE_APP_NAME} \
    VITE_HEALTH_POLL_INTERVAL_MS=${VITE_HEALTH_POLL_INTERVAL_MS}

RUN npm run build

FROM nginx:1.27-alpine AS production

COPY --from=builder /app/dist /usr/share/nginx/html

# Fallback nginx configuration for standalone builds; docker-compose mounts
# infrastructure/docker/nginx/default.conf over this file.
RUN printf '%s\n' \
  'server {' \
  '    listen 80;' \
  '    server_name _;' \
  '    root /usr/share/nginx/html;' \
  '    index index.html;' \
  '    location = /nginx-health { access_log off; default_type text/plain; return 200 "ok\n"; }' \
  '    location / { try_files $uri $uri/ /index.html; }' \
  '}' > /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
