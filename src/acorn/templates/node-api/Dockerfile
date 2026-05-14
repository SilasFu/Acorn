FROM node:{{node_version}}-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci --only=production

COPY . .

EXPOSE {{port}}

CMD ["node", "index.js"]
