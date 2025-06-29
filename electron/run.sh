#!/bin/sh
set -e
cd "$(dirname "$0")"

# When invoked with the "lint" argument run ESLint instead of launching
# the application. Dependencies are installed automatically if missing.
if [ "$1" = "lint" ]; then
  shift
  if [ ! -d node_modules ]; then
    echo "Node dependencies not found. Running 'npm install' first..."
    npm install
  fi
  npm run lint "$@"
  exit
fi

if [ ! -d node_modules ]; then
  echo "Installing dependencies..."
  npm install
fi

npx electron . "$@"
