# RUN addgroup -g 1001 -S nginx && \
  #  adduser -S -D -H -u 1001 -h /var/cache/nginx -s /sbin/nologin -G nginx -g nginx nginx && \
  #  chown -R nginx:nginx /usr/share/nginx/html && \
  #  chown -R nginx:nginx /var/cache/nginx && \
  #  chown -R nginx:nginx /var/log/nginx && \
  #  chown -R nginx:nginx /etc/nginx/conf.d

# Switch to non-root user
USER nginx

# Expose port
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:80/ || exit 1

# Start nginx
CMD ["nginx", "-g", "daemon off;"]

