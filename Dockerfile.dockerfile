FROM python:3.12
RUN pip install -r requirements.txt
RUN python run.py
ENTRYPOINT [“streamlit”, “run”]
CMD [ “app.py” ]
