#!/usr/bin/env python
"""Test API endpoint returns 3 orders"""

import requests

response = requests.get("http://localhost:8100/commerce/customers/0039Q00001VsHMXQA3/orders?limit=5")
data = response.json()

print(f"Order count: {len(data)}")
print(f"Order[0]: {data[0]['order_id']}")
print(f"Order[1]: {data[1]['order_id']}")
print(f"Order[1].items[1].product_name: {data[1]['items'][1]['product_name']}")
