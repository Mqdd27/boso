# syntax=docker/dockerfile:1

FROM node:24-alpine AS web
WORKDIR /src
COPY package.json package-lock.json ./
COPY apps/web/package.json apps/web/
COPY apps/server/package.json apps/server/
RUN npm ci
COPY schema/ schema/
COPY apps/web/ apps/web/
RUN npm run build -w web

FROM golang:1.27-alpine AS server
WORKDIR /src
COPY apps/server/go.mod apps/server/go.sum ./
RUN go mod download
COPY apps/server/ ./
COPY --from=web /src/apps/server/web/dist ./web/dist
RUN CGO_ENABLED=0 go build -trimpath -ldflags "-s -w" -o /boso ./cmd/boso && mkdir /data

FROM gcr.io/distroless/static-debian12:nonroot
COPY --from=server /boso /boso
COPY --from=server --chown=65532:65532 /data /data
ENV BOSO_ADDR=:8080 BOSO_DATA_DIR=/data
VOLUME /data
EXPOSE 8080
ENTRYPOINT ["/boso"]
