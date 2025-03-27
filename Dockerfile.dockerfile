FROM python:3.12
WORKDIR /usr/local/app
RUN pip install -r requirements.txt
RUN python run.py
ENTRYPOINT [“streamlit”, “run”]
CMD [ “app.py” ]
