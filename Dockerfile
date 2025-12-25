FROM python:3.14.2-trixie

# ============================================================================
# APT PACKAGE VERSION PINNING
# ============================================================================
# This section pins Debian package versions for reproducible builds.
# Renovate automatically updates these versions using the deb datasource.
#
# UPDATING THE DEBIAN SUITE:
# When you change the base image (e.g., FROM python:3.14 to python:3.15),
# you need to:
# 1. Check the Debian version of the new base image:
#    docker run --rm python:3.14 cat /etc/os-release | grep VERSION_CODENAME
# 2. Update all "suite=" comments below (e.g., trixie -> forky)
# 3. Update all package versions (see next section)
#
# GETTING PACKAGE VERSIONS:
# To get the current versions of all packages (needed when changing suite or
# adding new packages):
#    docker run --rm python:3.14 bash -c "apt-get update -qq && \
#      apt-cache policy PACKAGE_NAME | grep Candidate | awk '{print \$2}'"
#
# Or for all packages at once:
#    docker run --rm python:3.14 bash -c "apt-get update -qq && \
#      apt-cache policy git gettext nano 2>/dev/null | \
#      grep -E '^[^ ]|Candidate:' | paste - - | sed 's/:$//' | \
#      awk '{print \$1, \$3}'"
#
# ADDING A NEW PACKAGE:
# 1. Get the version using the command above with your package name
# 2. Add a comment: # renovate: suite=trixie depName=PACKAGE-NAME
# 3. Add ENV variable: ENV PACKAGE_VERSION="x.y.z"
# 4. Add to apt-get install: package-name="${PACKAGE_VERSION}"
# ============================================================================

# renovate: suite=trixie depName=git
ENV GIT_VERSION="1:2.47.3-0+deb13u1"
# renovate: suite=trixie depName=gettext
ENV GETTEXT_VERSION="0.23.1-2"
# renovate: suite=trixie depName=nano
ENV NANO_VERSION="8.4-1"

RUN apt-get update; \
    apt-get install -y --no-install-recommends \
        # To fetch from pip
        git="${GIT_VERSION}" \
        gettext="${GETTEXT_VERSION}" \
        nano="${NANO_VERSION}" \
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
