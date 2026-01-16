#!/usr/bin/env python
import yaml
documents = """
---
name: foo
---
name: bar
---
name: foobar
"""

for data in yaml.load_all(documents, Loader=yaml.SafeLoader):
    print(data)
