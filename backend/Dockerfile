FROM node:22-alpine AS deps
WORKDIR /app
COPY backend/package.json ./backend/
WORKDIR /app/backend
RUN npm install --omit=dev

FROM node:22-alpine AS build
WORKDIR /app
COPY backend/package.json ./backend/
WORKDIR /app/backend
RUN npm install
COPY backend/ .
RUN npm run build

FROM node:22-alpine
WORKDIR /app
ENV NODE_ENV=production
COPY --from=deps /app/backend/node_modules ./node_modules
COPY --from=build /app/backend/dist ./dist
COPY backend/package.json ./
RUN mkdir -p /app/data
EXPOSE 4000
CMD ["node", "dist/index.js"]
