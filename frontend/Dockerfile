FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files
COPY package.json package-lock.json* ./

# Install dependencies
RUN npm ci

# Copy source files
COPY . .

# Build the application. The backend API key is intentionally NOT passed in
# here — it must never be baked into the client bundle. nginx injects it
# server-side at runtime instead (see below).
RUN npm run build

# Production stage
FROM nginx:alpine

# Copy built files to nginx
COPY --from=builder /app/dist /usr/share/nginx/html

# nginx template processing: the entrypoint runs envsubst over files in
# /etc/nginx/templates/*.template at startup. NGINX_ENVSUBST_FILTER restricts
# substitution to these three vars only, so nginx's own $variables are preserved.
# BACKEND_URL/HOST default to Render production; docker-compose overrides them
# for local dev. CDDBS_API_KEY is set by the Render dashboard or docker-compose.
ENV CDDBS_API_KEY=""
ENV BACKEND_URL="https://cddbs-api.onrender.com"
ENV BACKEND_HOST="cddbs-api.onrender.com"
ENV NGINX_ENVSUBST_FILTER="CDDBS_API_KEY|BACKEND_URL|BACKEND_HOST"

# Copy nginx configuration as a template so ${CDDBS_API_KEY} is substituted
COPY nginx.conf /etc/nginx/templates/default.conf.template

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
