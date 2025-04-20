#!/usr/bin/env bash

# Infinite loop: invoke codex and sleep 10 seconds between runs
while true; do
  codex "$@"
  sleep 10
done