FROM node:20-alpine

WORKDIR /app

COPY package*.json ./

# Create dummy package.json if not exist
RUN if [ ! -f package.json ]; then echo '{}' > package.json; fi
RUN npm install

COPY . .

EXPOSE 3000

CMD ["npm", "run", "dev"]
