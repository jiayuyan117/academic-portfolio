FROM python:3.12.10-slim-bookworm
ENV PYTHONUTF8=1 \
    MPLBACKEND=Agg \
    OPENBLAS_NUM_THREADS=1 \
    OMP_NUM_THREADS=1 \
    MKL_NUM_THREADS=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
RUN apt-get update && apt-get install -y --no-install-recommends fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /portfolio
COPY . .
RUN python -m pip install --no-cache-dir -c constraints.txt -r requirements.txt \
    && python -m pip check
CMD ["python", "tools/rebuild.py"]
