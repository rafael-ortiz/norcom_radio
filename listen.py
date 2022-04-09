#!/usr/bin/env python3
from process_line import process_line
import json

while True:
    line = input()
    page = process_line(line)
    if page:
        print(json.dumps(page.__dict__))
