# --- Build Stage ---
FROM python:3.12-slim AS builder

# Create a virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:${PATH}"

WORKDIR /app

# --- Install Dependencies ---
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --- Copy the rest of the application
COPY . .

RUN python run.py

# --- Final Stage ---

FROM python:3.12-slim

WORKDIR /app

# --- Create a non-root user WITH a home directory ---
RUN groupadd --system appgroup && useradd --system --create-home --gid appgroup appuser

# Copy the perfected virtual environment from the builder
COPY --from=builder /opt/venv /opt/venv

# --- Copy only the necessary files from the builder stage
COPY --from=builder /app/app.py .
COPY --from=builder /app/.streamlit ./.streamlit/
COPY --from=builder /app/images ./images/

# --- Change ownership of BOTH the app and the venv ---
RUN chown -R appuser:appgroup /app /opt/venv

# -- Switch to the non-root user
USER appuser

# Activate the virtual environment for the final image
ENV PATH="/opt/venv/bin:${PATH}"

EXPOSE 8501

ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
