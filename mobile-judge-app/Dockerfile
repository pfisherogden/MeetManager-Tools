# Build stage
FROM node:20-alpine AS build

WORKDIR /app

# Copy package files and install dependencies
# Note: In the CI we build with the root context
COPY mobile-judge-app/package*.json ./
RUN npm install --legacy-peer-deps

# Copy the rest of the application
COPY mobile-judge-app/ .

# Export the app for web
RUN npm run prebuild-web
RUN npx expo export --platform web --output-dir dist

# Production stage
FROM nginx:stable-alpine

# Copy the build output from the build stage
COPY --from=build /app/dist /usr/share/nginx/html

# Copy a simple nginx config to handle client-side routing
COPY mobile-judge-app/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 8080

CMD ["nginx", "-g", "daemon off;"]
