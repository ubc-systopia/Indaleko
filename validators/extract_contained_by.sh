jq -s 'group_by(.URI) | .[] | {type:"contained_by", child_uri: .[0].URI, parent_uris: map(.Path)}' $1 | jq -c '.'
