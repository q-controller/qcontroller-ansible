#!/usr/bin/env bash

set -euo pipefail

PATH=$PATH:/usr/local/go/bin
PATH=$(go env GOPATH)/bin:$PATH

TEMPDIR=$(mktemp -d)
OUTPUT_DIR="${1:-./generated}"
QCONTROLLER_LOCATION="${2:-}"

trap "rm -rf ${TEMPDIR}" EXIT ERR SIGINT SIGTERM

pushd "${TEMPDIR}"

if [[ -z "${QCONTROLLER_LOCATION}" ]]; then
    git clone https://github.com/q-controller/qcontroller.git
    QCONTROLLER_LOCATION="${TEMPDIR}/qcontroller"
fi

git clone https://github.com/googleapis/googleapis.git

mkdir -p ${OUTPUT_DIR}/protos

# Generate python interfaces for proto definitions
find ${QCONTROLLER_LOCATION}/src/protos -name "*.proto" -exec python3 -m grpc_tools.protoc \
    -I${QCONTROLLER_LOCATION}/src/protos \
    -Igoogleapis \
    --python_out=${OUTPUT_DIR}/protos \
    --pyi_out=${OUTPUT_DIR}/protos \
    {} \;

# Generate OpenAPI schema
protoc \
    -I${QCONTROLLER_LOCATION}/src/protos \
    -I googleapis \
    --openapi_out=. \
    --openapi_opt=fq_schema_naming=true,default_response=false,title="Controller Service",version=v1,description="This is the OpenAPI schema for Controller gRPC API",naming=json \
    ${QCONTROLLER_LOCATION}/src/protos/services/v1/controller.proto

find ${OUTPUT_DIR}/protos/* -type d -exec touch {}/__init__.py \;

# Generate OpenAPI client for controller service
openapi-generator-cli generate -g python -i openapi.yaml --additional-properties=generateSourceCodeOnly=false,packageName=controller_service -o ${OUTPUT_DIR}/controller

# Generate OpenAPI client for image service
openapi-generator-cli generate -g python -i ${QCONTROLLER_LOCATION}/image-service-openapi.yml --additional-properties=generateSourceCodeOnly=false,packageName=image_service -o ${OUTPUT_DIR}/image
