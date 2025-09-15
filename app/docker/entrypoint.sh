#!/bin/bash
ollama serve &
sleep 5
ollama pull gemma3:1b
wait
