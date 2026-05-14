FROM denoland/deno:{{deno_version}}

WORKDIR /app
COPY . .

RUN deno cache main.ts

EXPOSE {{port}}
CMD ["deno", "run", "--allow-net", "main.ts"]
