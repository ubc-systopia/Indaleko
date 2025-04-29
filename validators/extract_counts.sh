jq -s 'group_by(.st_mode) | .[] | {"type": "count", "field": "st_mode", "value": .[0].st_mode, "count": length}' $1 | jq -c '.'
