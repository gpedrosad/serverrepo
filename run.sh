#!/bin/bash
# Levanta el container de YurOTS con puertos publicados e interactivo.
set -e
cd "$(dirname "$0")"
docker compose run --rm --service-ports yurots bash
