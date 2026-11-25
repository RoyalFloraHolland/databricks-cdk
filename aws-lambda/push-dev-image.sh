#!/usr/bin/env bash

set -euv

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

cd $SCRIPT_DIR

docker build --platform linux/amd64 -t databricks-cdk-lambda:dev .
docker tag databricks-cdk-lambda:dev floriday/databricks-cdk-lambda:dev
docker push floriday/databricks-cdk-lambda:dev
