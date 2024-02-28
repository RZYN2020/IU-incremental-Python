#!/bin/bash

current_dir="$(pwd)"
script_dir="$(dirname "$0")"
echo $script_dir/runtime.c

if [ ! -f "$script_dir/runtime.o" ]; then
    gcc -c -g -std=c99 "$script_dir/runtime.c" -o "$script_dir/runtime.o"
fi

source_file="$1"
asm_file="$current_dir/${source_file%.py}.s"
exe_file="$current_dir/${source_file%.py}"

# Compile the source file
python3 "$script_dir/main.py" "$source_file" -o "$exe_file"

# Run the compiled output
"$exe_file"

# Remove the output files
rm "$asm_file"
rm "$exe_file"