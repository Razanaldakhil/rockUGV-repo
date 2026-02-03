# FROM dustynv/l4t-pytorch:r36.4.0
FROM nvcr.io/nvidia/l4t-pytorch:r32.4.3pth1.6-py3

WORKDIR /app

# Install packages with NumPy version pinned to avoid conflicts
RUN pip3 install --no-cache-dir \
    --index-url https://pypi.org/simple \
    --default-timeout=100 \
    --retries 5 \
    "numpy<2" \
    fastapi uvicorn python-multipart pillow ultralytics opencv-python-headless

# Copy application
COPY app/ .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
