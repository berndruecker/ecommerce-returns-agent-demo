#!/usr/bin/env python
"""
Test the actual HTTP flow - call the API like the worker would
"""

import sys
import json
sys.path.insert(0, "fake-backends")

import requests
from camunda_worker import _request, _handle_operation

# Test calling the API
print("Testing _request function:")
print("=" * 80)

result = _handle_operation("listOrders", {
    "customerId": "0039Q00001VsHMXQA3",
    "limit": 5,
    "apiBaseUrl": "http://localhost:8100/commerce"
})

print(f"Result type: {type(result)}")
print(f"Result keys: {result.keys()}")
print(f"Status: {result['status']}")
print(f"Body type: {type(result['body'])}")
print(f"Body length: {len(result['body']) if isinstance(result['body'], list) else 'N/A'}")

if isinstance(result['body'], list) and len(result['body']) > 1:
    print(f"\nOrder [1] keys: {result['body'][1].keys() if isinstance(result['body'][1], dict) else 'not a dict'}")
    print(f"Order [1] order_id: {result['body'][1].get('order_id') if isinstance(result['body'][1], dict) else 'N/A'}")
    print(f"Order [1] items type: {type(result['body'][1].get('items')) if isinstance(result['body'][1], dict) else 'N/A'}")
    if isinstance(result['body'][1], dict) and isinstance(result['body'][1].get('items'), list):
        items = result['body'][1]['items']
        print(f"Order [1] items count: {len(items)}")
        if len(items) > 1:
            print(f"Order [1] items[1]: {items[1].keys() if isinstance(items[1], dict) else 'not a dict'}")
            print(f"Order [1] items[1] product_name: {items[1].get('product_name')}")
            print(f"Order [1] items[1] unit_price: {items[1].get('unit_price')}")

print("\nFull response body[1]:")
if isinstance(result['body'], list) and len(result['body']) > 1:
    print(json.dumps(result['body'][1], indent=2, default=str))
