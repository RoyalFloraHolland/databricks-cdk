# syntax=docker/dockerfile:1

# Docker image to run the databricks-cdk lambda function.

# Pinned by digest and updated by Dependabot. Keep the version in sync with .github/actions/setup-uv/action.yml
FROM ghcr.io/astral-sh/uv:0.13.7@sha256:96f40d3904aad8d0bd010539001d36c8e2188b981e1334471a90c4a1d93bb490 AS uv

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
