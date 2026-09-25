#!/usr/bin/env bash
# usage: wait_file.sh <path> [pattern]  — exits when the file exists (and matches pattern), or after ~9 min
for i in $(seq 1 54); do
  if [[ -f "$1" ]] && { [[ -z "${2:-}" ]] || grep -Eq "$2" "$1"; }; then echo "READY: $1"; exit 0; fi
  sleep 10
done
echo "NOT YET: $1"
