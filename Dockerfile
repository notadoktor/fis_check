FROM python:3.9-buster

ENV LANGUAGE=C.UTF-8 \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    PIPENV_VENV_IN_PROJECT=1

RUN sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt buster-pgdg main" > /etc/apt/sources.list.d/pgdg.list' && \
    wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | apt-key add - && \
    apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install --no-install-recommends \
        curl \
        file \
        libpq-dev \
        make \
        mlocate \
        postgresql-common \
        postgresql-server-dev-12 \
        vim \
        -y

RUN pip install -U pip setuptools && pip install pipenv

WORKDIR /app

COPY Pipfile Pipfile.lock /app/

RUN pipenv install --dev 

COPY . /app

CMD ["/bin/bash"]
