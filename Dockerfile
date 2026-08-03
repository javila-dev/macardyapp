FROM python:3.9
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && \
    apt-get install -y locales postgresql-client && \
    sed -i -e 's/# es_CO.UTF-8 UTF-8/es_CO.UTF-8 UTF-8/' /etc/locale.gen && \
    dpkg-reconfigure --frontend=noninteractive locales && \
    rm -rf /var/lib/apt/lists/*

ENV LANG es_CO.UTF-8
ENV LC_ALL es_CO.UTF-8

WORKDIR /code
COPY requirements.txt /code/
RUN pip install -r requirements.txt
COPY entrypoint.sh /entrypoint.sh
COPY entrypoint-staging.sh /entrypoint-staging.sh
RUN chmod +x /entrypoint.sh /entrypoint-staging.sh
COPY . /code/

RUN python manage.py collectstatic --noinput

EXPOSE 8000
ENTRYPOINT ["/entrypoint.sh"]
CMD ["gunicorn", "mcd_project.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120", "--access-logfile", "-", "--error-logfile", "-", "--log-level", "info"]
