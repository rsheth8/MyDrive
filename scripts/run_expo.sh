#!/usr/bin/env bash
# Start Expo Go (wrapper for dev.sh expo).
exec "$(dirname "$0")/dev.sh" expo "$@"
