#!/bin/bash

input=$(cat)
file_path=$(echo "$input" | jq -r '.tool_input.file_path // empty')

[[ -z "$file_path" || ! -f "$file_path" ]] && exit 0
[[ "$file_path" != *.py && "$file_path" != *.pyi ]] && exit 0

format_result=$(uv run ruff format --no-cache "$file_path" 2>&1)
lint_result=$(uv run ruff check --no-cache --show-fixes "$file_path" 2>&1)

rel_path="$file_path"
[[ "$file_path" == "$PWD"/* ]] && rel_path="${file_path#$PWD/}"

output="<output cmd=\"ruff format $rel_path\">${format_result:-OK}</output>"
output+="<output cmd=\"ruff check --show-fixes $rel_path\">${lint_result:-OK}</output>"

jq -n --arg content "$output" '{"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": $content}}'
exit 0
