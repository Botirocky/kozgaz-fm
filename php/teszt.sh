#!/bin/sh
exec docker --context default run --rm -v "$(cd "$(dirname "$0")" && pwd):/app" -w /app kozgazfm-php:helyi php tests/futtat.php "$@"
