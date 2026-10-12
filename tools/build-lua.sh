#!/bin/sh
# Build the Lua 5.2.4 interpreter (the version GarageBand/MainStage embed) into
# tools/lua-5.2.4 for test/harness.lua. Nothing is installed system-wide.
set -e
cd "$(dirname "$0")"
[ -x lua-5.2.4/src/lua ] && { echo "already built: tools/lua-5.2.4/src/lua"; exit 0; }
curl -sSLO https://www.lua.org/ftp/lua-5.2.4.tar.gz
echo "b9e2e4aad6789b3b63a056d442f7b39f0ecfca3ae0f1fc0ae4e9614401b69f4b  lua-5.2.4.tar.gz" | shasum -a 256 -c -
tar xzf lua-5.2.4.tar.gz && rm lua-5.2.4.tar.gz
make -s -C lua-5.2.4/src macosx CC=clang MYCFLAGS="-Wno-deprecated-declarations" >/dev/null
echo "built: tools/lua-5.2.4/src/lua"
