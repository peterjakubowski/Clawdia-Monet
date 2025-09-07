# --- Build Stage ---
FROM python:3.12-slim AS builder

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

# --- Add the user's local bin directory to the PATH ---
ENV PATH="/home/appuser/.local/bin:${PATH}"

# --- Copy ONLY the production requirements file ---
COPY --from=builder /app/requirements.txt .

# --- Copy only the necessary files from the builder stage
COPY --from=builder /app/app.py .
COPY --from=builder /app/.streamlit ./.streamlit/
COPY --from=builder /app/images ./images/

# --- Change ownership of ALL copied files at once ---
RUN chown -R appuser:appgroup /app

# -- Switch to the non-root user
USER appuser

# Install ONLY production dependencies
RUN pip install --no-cache-dir --user -r requirements.txt

EXPOSE 8501

ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
