FROM python:3.11-slim-bullseye

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

ENV UV_SYSTEM_PYTHON=1

RUN uv pip install --system --no-cache \
    torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu \
    "numpy<2.0"


COPY pyproject.toml uv.lock ./


RUN uv pip install --system --no-cache .


RUN rm -rf /root/.cache

COPY . .

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8002"]
