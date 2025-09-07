# --- Build Stage ---
FROM python:3.12-slim AS builder

WORKDIR /app

# --- Install Dependencies ---
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --- Copy the rest of the application
COPY . .

RUN run.py

# --- Final Stage ---

FROM python:3.12-slim

WORKDIR /app

# --- Create a non-root user ---
RUN addgroup -S appgroup && adduser -G appgroup
USER appuser

# --- Copy only the necessary files from the builder stage
COPY --from=builder /app /app

EXPOSE 8501

ENTRYPOINT ["streamlit", "run", "app.py"]
