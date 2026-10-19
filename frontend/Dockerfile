# Stage 1: Build the React application
FROM node:22-alpine AS builder

WORKDIR /app

ARG REACT_APP_API_URL="/"
ENV REACT_APP_API_URL=$REACT_APP_API_URL

# Install dependencies (utilize docker layer cache)
COPY package.json package-lock.json ./
RUN npm ci

# Copy source code and build
COPY . .
RUN npm run build

# Stage 2: Serve using Nginx
FROM nginx:stable-alpine

# Copy built static assets from builder stage
COPY --from=builder /app/build /usr/share/nginx/html

# Copy custom Nginx configuration for proxy routing
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port
EXPOSE 3000

# Start Nginx
CMD ["nginx", "-g", "daemon off;"]
