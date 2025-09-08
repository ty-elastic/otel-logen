# OTel Log Generator for Elastic

# Use
```
export ELASTIC_ENDPOINT=
export ELASTIC_API_KEY=
```

```
docker compose build
docker compose up
```

# Streams Mode

## Wired

config/collector.yaml
```
    logs_index: logs
    logs_dynamic_index:
      enabled: false
```

## Classic

config/collector.yaml
```
    #logs_index: logs
    logs_dynamic_index:
      enabled: true
```

# Config

`config/otel-logen.yaml`
