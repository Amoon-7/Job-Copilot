FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir ".[ui]"
COPY data ./data
EXPOSE 8000 8501
CMD ["uvicorn", "job_copilot.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
