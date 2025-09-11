echo KIBANA_URL=$KIBANA_URL
echo ELASTICSEARCH_URL=$ELASTICSEARCH_URL
echo ELASTICSEARCH_APIKEY=$ELASTICSEARCH_APIKEY

# ------------- STREAMS

echo "/api/streams/_enable"
curl -X POST "$KIBANA_URL/api/streams/_enable" \
    --header "kbn-xsrf: true" \
    --header 'x-elastic-internal-origin: Kibana' \
    --header "Authorization: ApiKey $ELASTICSEARCH_APIKEY"

echo "/internal/kibana/settings"
curl -X POST "$KIBANA_URL/internal/kibana/settings" \
    --header 'Content-Type: application/json' \
    --header "kbn-xsrf: true" \
    --header "Authorization: ApiKey $ELASTICSEARCH_APIKEY" \
    --header 'x-elastic-internal-origin: Kibana' \
    -d '{"changes":{"observability:streamsEnableSignificantEvents":true}}'

# # ------------- TEMPLATE

echo "/_component_template/logs-otel@custom"
curl -X POST "$ELASTICSEARCH_URL/_component_template/logs-otel@custom" \
    --header 'Content-Type: application/json' \
    --header "Authorization: ApiKey $ELASTICSEARCH_APIKEY" \
    -d '
{
  "template": {
    "mappings": {
      "dynamic_templates": [
        {
          "complex_attributes": {
            "path_match": [
              "resource.attributes.*",
              "scope.attributes.*",
              "attributes.*"
            ],
            "mapping": {
              "type": "object",
              "subobjects": false
            },
            "match_mapping_type": "object"
          }
        }
      ]
    }
  }
}'

# # ------------- PROMPT

echo "/internal/observability_ai_assistant/kb/user_instructions"
curl -X PUT "$KIBANA_URL/internal/observability_ai_assistant/kb/user_instructions" \
  --header 'Content-Type: application/json' \
  --header "kbn-xsrf: true" \
  --header "Authorization: ApiKey $ELASTICSEARCH_APIKEY" \
  --header 'x-elastic-internal-origin: Kibana' \
  -d @prompt.json
