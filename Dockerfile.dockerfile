FROM python:3.12
WORKDIR /app
COPY . /app
RUN pip install -r requirements.txt
RUN python run.py
ENTRYPOINT [“streamlit”, “run”]
CMD [ “app.py” ]
