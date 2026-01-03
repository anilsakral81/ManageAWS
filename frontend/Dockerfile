# Build stage
FROM --platform=linux/amd64 node:20-bookworm AS builder

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies with reduced memory usage
RUN npm ci --prefer-offline --no-audit

# Copy application files
COPY . .

# Build application with increased memory limits
    ENV NODE_OPTIONS="--max-old-space-size=4096"
RUN npm run build

# Production stage
FROM --platform=linux/amd64 nginx:alpine

# Copy built files from builder
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost/ || exit 1

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
