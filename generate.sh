#!/usr/bin/env bash

set -euo pipefail

PATH=$PATH:/usr/local/go/bin
PATH=$(go env GOPATH)/bin:$PATH

TEMPDIR=$(mktemp -d)
OUTPUT_DIR="${1:-./generated}"

trap "rm -rf ${TEMPDIR}" EXIT ERR SIGINT SIGTERM

pushd "${TEMPDIR}"

git clone https://github.com/q-controller/qcontroller.git
git clone https://github.com/googleapis/googleapis.git

mkdir -p ${OUTPUT_DIR}

# Generate python interfaces for proto definitions
find qcontroller/src/protos -name "*.proto" -exec python3 -m grpc_tools.protoc \
    -Iqcontroller/src/protos \
    -Igoogleapis \
    --python_out=${OUTPUT_DIR} \
    --pyi_out=${OUTPUT_DIR} \
    {} \;

# Generate OpenAPI schema
protoc \
    -I qcontroller/src/protos \
    -I googleapis \
    --openapi_out=. \
    --openapi_opt=fq_schema_naming=true,default_response=false,title="Controller Service",version=v1,description="This is the OpenAPI schema for Controller gRPC API",naming=json \
    qcontroller/src/protos/services/v1/controller.proto

# Generate OpenAPI client
openapi-generator-cli generate -g python -i openapi.yaml --additional-properties=generateSourceCodeOnly=false -o ${OUTPUT_DIR}
