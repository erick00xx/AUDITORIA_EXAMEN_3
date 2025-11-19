# frontend/Dockerfile

# --- Fase 1: Construcción ---
# Usamos la imagen oficial de Node.js 22
FROM node:22 AS build

# Establecemos el directorio de trabajo
WORKDIR /app

# Copiamos los archivos de configuración del proyecto y ejecutamos la instalación
COPY package*.json ./
RUN npm install

# Copiamos el resto del código del frontend
COPY . .

# Este comando crea la versión de producción optimizada de la app
RUN npm run build

# --- Fase 2: Producción ---
# Usamos un servidor web Nginx, que es muy eficiente para servir archivos estáticos
FROM nginx:stable-alpine

# Copiamos solo los archivos compilados de la fase anterior a la carpeta web de Nginx
COPY --from=build /app/dist /usr/share/nginx/html

# El puerto 80 es el puerto por defecto de Nginx
EXPOSE 80

# Comando para iniciar el servidor Nginx
CMD ["nginx", "-g", "daemon off;"]