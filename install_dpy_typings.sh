#!/usr/bin/env bash
FOLDER=./dpy-typings

echo "[typings] Deleting previous run..."

rm -Rvf $FOLDER

echo "[typings] Downloading typings..."
git clone --single-branch --branch typings --depth 1 https://github.com/bryanforbes/discord.py.git $FOLDER

echo "[typings] Removing library files..."
rm -Rvf $FOLDER/.git
find $FOLDER -not -name "*.pyi" -not -type d -print -delete

echo "[typings] Getting discord package directory..."
discord_package_dir=$(python3 -c "import discord as _; print(_.__path__[0])")
echo "[typings] Got discord package directory: $discord_package_dir"

echo "[typings] Installing typings"
cp -Rv $FOLDER/discord/* "$discord_package_dir"/

echo "[typings] Removing typings repository"
rm -Rvf $FOLDER