FROM rust:{{rust_version}}-slim AS builder

WORKDIR /app
COPY Cargo.toml Cargo.lock ./
RUN cargo build --release || true
COPY . .
RUN cargo build --release

FROM debian:bookworm-slim
COPY --from=builder /app/target/release/* /usr/local/bin/
EXPOSE {{port}}
CMD ["/usr/local/bin/app"]
