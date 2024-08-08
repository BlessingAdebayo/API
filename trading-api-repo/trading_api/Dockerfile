FROM python:3.9

WORKDIR /app/trading_api

# Create a non-root user to run the app with.
RUN mkdir /userhome
RUN groupadd --gid 1000 user
RUN adduser --disabled-password --gecos '' --uid 1000 --gid 1000 user
RUN chown user:user /userhome
USER user

# Install the pipenv package in pip.
RUN pip install --user pipenv

ENV PATH="/home/user/.local/bin:${PATH}"

# Copy over our Pipfiles so we can install our env
COPY --chown=user:user trading_api/Pipfile ./
COPY --chown=user:user trading_api/Pipfile.lock ./

RUN pipenv install --deploy --verbose
