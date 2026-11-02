# syntax=docker/dockerfile:1

# Docker image to run the databricks-cdk lambda function.

# Pinned by digest and updated by Dependabot. Keep the version in sync with .github/actions/setup-uv/action.yml
FROM ghcr.io/astral-sh/uv:0.13.6@sha256:af22a52f5eafef3d78e551599d405c02df61919d18028f0cea8eda93bc9986d0 AS uv

FROM public.ecr.aws/lambda/python:3.12 AS builder

COPY --from=uv /uv /bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /build

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv export --locked --no-dev --no-emit-project -o requirements.txt \
    && uv pip install --python /var/lang/bin/python --target "${LAMBDA_TASK_ROOT}" -r requirements.txt

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=README.md,target=README.md \
    --mount=type=bind,source=src,target=src \
    uv pip install --python /var/lang/bin/python --target "${LAMBDA_TASK_ROOT}" --no-deps .

FROM public.ecr.aws/lambda/python:3.12

COPY --from=builder ${LAMBDA_TASK_ROOT} ${LAMBDA_TASK_ROOT}
COPY src/databricks_cdk/handler.py ${LAMBDA_TASK_ROOT}

CMD ["handler.handler"]
