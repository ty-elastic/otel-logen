# OTel Log Generator for Elastic

# Setup

## Elastic ECH or Serverless or Self-Managed
1. Create an API Key as a superuser

## Machine you are running the tool from
1. Setup the following env vars:
```
export KIBANA_URL=
export ELASTICSEARCH_URL=
export ELASTICSEARCH_APIKEY=
```
2. Run 
```
cd cluster
./setup.sh
```

# Use
1. Setup the following env vars:
```
export KIBANA_URL=
export ELASTICSEARCH_URL=
export ELASTICSEARCH_APIKEY=
```
2. Run docker compose:
```
docker compose build
docker compose up
```

# Config

[config/otel-logen.yaml](config/otel-logen.yaml)

* message sources are defined under `thread/messages`
* name the source (in the example, `nominal`)

## canned logs

* put structured logs from https://github.com/logpai/loghub in [logs](logs/)
* add to messages source for thread:
```
    messages:
      nominal:
        file:
          path: logs/Spark_2k.log_structured.csv
          type: csv
        order: loop
```
* set `order` to `loop` or `random`
