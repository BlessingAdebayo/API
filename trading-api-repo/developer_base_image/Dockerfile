# syntax = docker/dockerfile:experimental
FROM python:3.9
LABEL maintainer="info@mercor.finance"


# Create a non-root user to run the app with.
RUN mkdir /userhome
RUN groupadd --gid 1000 user
RUN adduser --disabled-password --gecos '' --uid 1000 --gid 1000 user

RUN chown user:user /userhome
WORKDIR /userhome
USER user

ENV PATH="/home/user/.local/bin:${PATH}"

# Copy over our Pipfiles so we can install our env
COPY --chown=user:user requirements.txt ./
COPY --chown=user:user entrypoint.sh ./

RUN --mount=type=cache,target=/root/.cache pip3 install -r requirements.txt

RUN ["chmod", "+x", "entrypoint.sh"]

ENTRYPOINT ["bash", "-c", "./entrypoint.sh"]