FROM python:3.10.5

RUN apt-get update; \
    apt-get install -y --no-install-recommends \
        # To fetch from pip
        git \
        gettext \
        nano \
       ; \
    rm -rf /var/lib/apt/lists/*;


WORKDIR /duckhunt/
COPY requirements.txt /duckhunt/

RUN pip install --use-deprecated=legacy-resolver -U -r requirements.txt

# Fix for babel stupid parsing
# RUN curl https://raw.githubusercontent.com/paris-ci/babel/master/babel/dates.py > /usr/local/lib/python3.10/site-packages/babel/dates.py

ENV BOT_TOKEN=""
ENV DB_HOST=""
ENV DB_PORT="5432"
ENV DB_USER=""
ENV DB_PASSWORD=""
ENV DB_NAME=""
ENV GLOBAL_API_KEY=""
ENV STATCORD_TOKEN="abcdef"
ENV JISHAKU_HIDE="True"
ENV JISHAKU_NO_DM_TRACEBACK="True"
ENV JISHAKU_NO_UNDERSCORE="True"

COPY / /duckhunt/

WORKDIR /duckhunt/src/

# Compile messages catalogs
#RUN pybabel compile -d locales/
RUN for dirr in ./locales/*/LC_MESSAGES/ ; do msgfmt "${dirr}messages.po" -o "${dirr}messages.mo" ; echo "${dirr} compiled"; done

ENTRYPOINT ["sh"]
CMD ["/duckhunt/docker_run.sh"]

STOPSIGNAL SIGTERM

EXPOSE 8080/tcp
