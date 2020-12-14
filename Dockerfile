FROM python:latest

RUN apt-get update; \
    apt-get install -y --no-install-recommends \
        # To fetch from pip
        git \
       ; \
    rm -rf /var/lib/apt/lists/*;


WORKDIR /
COPY requirements.txt /

RUN pip install --use-deprecated=legacy-resolver -U -r requirements.txt

# Fix for babel stupid parsing
RUN curl https://raw.githubusercontent.com/paris-ci/babel/master/babel/dates.py > /usr/local/lib/python3.9/site-packages/babel/dates.py

COPY src/ /bot

ENV BOT_TOKEN=""
ENV DB_HOST=""
ENV DB_PORT="5432"
ENV DB_USER=""
ENV DB_PASSWORD=""
ENV DB_NAME=""
ENV GLOBAL_API_KEY=""

COPY docker_config.toml /docker_config.toml
COPY generate_config_from_env.py /generate_config_from_env.py
COPY docker_run.sh /run.sh

WORKDIR /bot/
ENTRYPOINT ["sh"]
CMD ["/run.sh"]

STOPSIGNAL SIGTERM

EXPOSE 8080/tcp
