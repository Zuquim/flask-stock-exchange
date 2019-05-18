FROM python:alpine
WORKDIR /opt
COPY app.py .
RUN ln -sf /usr/local/zoneinfo/America/Sao_Paulo /etc/timezone && \
    pip install --no-cache-dir flask
ENV FLASK_APP app.py
ENV FLASK_ENV development
ENV FLASK_DEBUG 0
EXPOSE 5000
ENTRYPOINT ["flask", "run", "--host=0.0.0.0"]