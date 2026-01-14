FROM openapitools/openapi-generator-cli:v7.18.0

RUN apt update && apt install -y git unzip python3 python3-pip
RUN python3 -m pip install grpcio-tools

RUN curl -LO https://github.com/protocolbuffers/protobuf/releases/download/v21.12/protoc-21.12-linux-x86_64.zip && \
    unzip protoc-21.12-linux-x86_64.zip -d /usr/local

RUN curl -LO https://go.dev/dl/go1.25.5.linux-amd64.tar.gz && \
    tar -C /usr/local -xzf go1.25.5.linux-amd64.tar.gz && \
    rm -f go1.25.5.linux-amd64.tar.gz

COPY generate.sh /usr/local/bin/generate.sh

RUN groupadd -g 1000 generator && useradd -u 1000 -g 1000 -ms /bin/bash generator
USER generator

RUN PATH=$PATH:/usr/local/go/bin go install github.com/google/gnostic/cmd/protoc-gen-openapi@v0.7.1

ENTRYPOINT ["generate.sh"]
