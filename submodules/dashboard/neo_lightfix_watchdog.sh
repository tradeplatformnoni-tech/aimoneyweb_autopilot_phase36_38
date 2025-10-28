#!/usr/bin/env bash
while true; do
  docker ps --format '{{.Names}} {{.Status}}' | while read -r name status_rest; do
    # If not "Up", attempt restart
    if echo "$status_rest" | grep -vq "^Up"; then
      echo "⚠️  $name unhealthy: $status_rest -> restarting"
      docker restart "$name" >/dev/null 2>&1
    fi
  done
  sleep 20
done
