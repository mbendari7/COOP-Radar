# Multi-stage: 'dev' target runs the Vite dev server,
# 'prod' builds static files for nginx serving.

FROM node:20-alpine AS base
WORKDIR /app
COPY package*.json ./
RUN npm ci

# Dev stage — used by docker-compose for local development
FROM base AS dev
COPY . .
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

# Build stage — compiles the SPA to dist/
FROM base AS build
COPY . .
RUN npm run build

# Production stage — serves the built files via nginx
FROM nginx:alpine AS prod
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
