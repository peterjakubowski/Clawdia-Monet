FROM python:3.12
WORKDIR /app
COPY . /app
EXPOSE 8501
RUN pip install -r requirements.txt
RUN python run.py
ENTRYPOINT ["streamlit", "run", "app.py", "--server.port 8501", "--server.headless true"]
