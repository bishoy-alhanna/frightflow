# Multi-stage build for React customer portal
FROM node:20-alpine

# Set working directory
WORKDIR /app

# Copy package files
COPY package*.json ./
COPY pnpm-lock.yaml* ./

# Install pnpm and dependencies
RUN npm install -g pnpm
# Copy package files
COPY package.json pnpm-lock.yaml ./

RUN pnpm install --frozen-lockfile

# Copy source code
COPY . .

# Build the application
RUN pnpm run build

# Production stage with Nginx
FROM nginx:alpine

# Copy built application
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy custom nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Create nginx user and set permissions
#RUN addgroup -g 1001 -S nginx && \
 #   adduser -S -D -H -u 1001 -h /var/cache/nginx -s /sbin/nologin -G nginx -g nginx nginx && \
  #  chown -R nginx:nginx /usr/share/nginx/html && \
   # chown -R nginx:nginx /var/cache/nginx && \
   # chown -R nginx:nginx /var/log/nginx && \
   # chown -R nginx:nginx /etc/nginx/conf.d

# Switch to non-root user
USER nginx

# Expose port
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:80/ || exit 1

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
