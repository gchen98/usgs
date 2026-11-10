#!/bin/bash

LLAMA_SERVER='/home/garyc/code/llama.cpp/build/bin/llama-server'
MODEL_GGUF='/home/garyc/models/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf'

${LLAMA_SERVER} -m $MODEL_GGUF -c 8192 -t 4 --host 127.0.0.1 --port 8080

