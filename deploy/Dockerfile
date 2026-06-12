# Col on Render: Rust solver + Python orchestrator/GUI (stdlib only).
FROM rust:1-bookworm AS builder
WORKDIR /app
COPY solver/Cargo.toml solver/Cargo.lock solver/
COPY solver/src solver/src
RUN cd solver && cargo build --release

FROM python:3.12-slim-bookworm
WORKDIR /app

COPY --from=builder /app/solver/target/release/col-rs /app/solver/target/release/col-rs
COPY col-solve continuous-solve continuous_solve.py ./
COPY python/ python/
COPY deploy/start-web.sh deploy/start-worker.sh deploy/start-all.sh deploy/

RUN chmod +x col-solve continuous-solve deploy/start-web.sh deploy/start-worker.sh deploy/start-all.sh

ENV PYTHONPATH=/app/python
ENV TABLEBASE_DIR=/data/tablebases
ENV STATUS_FILE=/data/solver_status.json
