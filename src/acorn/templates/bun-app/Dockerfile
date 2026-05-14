FROM oven/bun:{{bun_version}}

WORKDIR /app
COPY package.json bun.lockb ./
RUN bun install
COPY . .

EXPOSE {{port}}
CMD ["bun", "run", "index.ts"]
