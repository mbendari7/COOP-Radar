# Development image for the Vite dev server (used by docker-compose.yml, hot reload).
# Production doesn't use this file: the root Dockerfile builds the site into the API image.

FROM node:22-alpine AS dev
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
