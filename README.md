# OTel Log Generator for Elastic

# Setup

## Elastic
1. Create an API Key as a superuser
2. Open AI Assistant, "Install Knowledge Base"

## Local
1. Setup the following env vars:
```
export KIBANA_URL=
export ELASTICSEARCH_URL=
export ELASTICSEARCH_APIKEY=
```
2. run `cluster/setup.sh`

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

# Demo Notes

## Partitioning

You can ask the AI Assistant to partition for you based on `service.name`:
```
can you partition my logs based on service?
```

You can also partition manually on say `resource.attributes.service.name`
