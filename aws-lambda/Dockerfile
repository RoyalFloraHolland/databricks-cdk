# Docker image to run the datascience-resources lambda function.

FROM public.ecr.aws/lambda/python:3.12


COPY ./src/ ./src/
COPY pyproject.toml .
COPY poetry.lock .
COPY README.md .

RUN export POETRY_VERSION=2.5.1 \
    && curl -sSL https://install.python-poetry.org | python3 - \
    && export PATH="/root/.local/bin:$PATH" \
    && poetry config virtualenvs.create false \
    && poetry install --only main --no-ansi \
    && rm -rf /root/.cache

COPY src/databricks_cdk/handler.py ${LAMBDA_TASK_ROOT}

CMD ["handler.handler"]
