#!/usr/bin/env python
"""
Test script to verify FEEL expression evaluator works with actual Magento responses.
"""

import sys
import json
from pprint import pprint

# Add fake-backends to path
sys.path.insert(0, "fake-backends")

from camunda_worker import _evaluate_result_expression

def test_list_orders_expression():
    """Test the listOrders resultExpression with sample data."""
    
    # The FEEL expression from listOrders task
    expression = """if response.body = null or count(response.body) = 0 then
{
  recentOrders: [],
  selectedOrderCandidate: null,
  toolCallResult: {
    status: "no_orders",
    message: "No recent orders found for this customer."
  }
}
else
{
  recentOrders: response.body,
  selectedOrderCandidate: response.body[1],
  toolCallResult: {
    status: "orders_found",
    candidate: {
      orderId: response.body[1].order_id,
      deliveryDate: response.body[1].delivery_date,
      status: response.body[1].status,
      firstItem: response.body[1].items[1]
    },
    message:
      "Found a delivered order. Likely match: " +
      response.body[1].items[1].product_name +
      " delivered on " + response.body[1].delivery_date +
      " for $" + string(response.body[1].items[1].unit_price) +
      ". Ask the customer to confirm this is the one to return."
  }
}
"""
    
    # Test with real sample data
    response = {
        "status": 200,
        "body": [
            {
                "order_id": "ORD-2025-007891",
                "customer_id": "0039Q00001VsHMXQA3",
                "delivery_date": "2024-12-21",
                "status": "DELIVERED",
                "items": [
                    {
                        "product_id": "PROD-001",
                        "product_name": "HomeStream Basic Router",
                        "unit_price": 149.99,
                        "quantity": 1
                    },
                    {
                        "product_id": "PROD-004",
                        "product_name": "Spare Cable",
                        "unit_price": 24.99,
                        "quantity": 1
                    }
                ]
            },
            {
                "order_id": "ORD-2025-007892",
                "customer_id": "0039Q00001VsHMXQA3",
                "delivery_date": "2025-01-02",
                "status": "DELIVERED",
                "items": [
                    {
                        "product_id": "PROD-002",
                        "product_name": "WiFi Extender Pro",
                        "unit_price": 89.99,
                        "quantity": 2
                    },
                    {
                        "product_id": "PROD-005",
                        "product_name": "Network Cable",
                        "unit_price": 19.99,
                        "quantity": 1
                    }
                ]
            },
            {
                "order_id": "ORD-2025-007893",
                "customer_id": "0039Q00001VsHMXQA3",
                "delivery_date": "2025-01-10",
                "status": "PENDING",
                "items": [
                    {
                        "product_id": "PROD-003",
                        "product_name": "Network Cable 100ft",
                        "unit_price": 24.99,
                        "quantity": 3
                    },
                    {
                        "product_id": "PROD-006",
                        "product_name": "Connector Kit",
                        "unit_price": 12.99,
                        "quantity": 2
                    }
                ]
            }
        ]
    }
    
    print("=" * 80)
    print("Testing FEEL Expression Evaluator")
    print("=" * 80)
    print("\nTest 1: With sample orders (should pick index [1]):")
    print(f"Response has {len(response['body'])} orders")
    
    result = _evaluate_result_expression(expression, response)
    
    print("\nResult:")
    pprint(result, width=120)
    
    # Validate structure
    assert isinstance(result, dict), f"Expected dict, got {type(result)}"
    assert "recentOrders" in result, "Missing recentOrders"
    assert "selectedOrderCandidate" in result, "Missing selectedOrderCandidate"
    assert "toolCallResult" in result, "Missing toolCallResult"
    
    print("\n[OK] Structure validation passed")
    print(f"[OK] recentOrders: {len(result.get('recentOrders', []))} orders")
    print(f"[OK] selectedOrderCandidate.orderId: {result.get('selectedOrderCandidate', {}).get('orderId')}")
    print(f"[OK] toolCallResult.status: {result.get('toolCallResult', {}).get('status')}")
    
    # Test with empty response
    print("\n" + "=" * 80)
    print("Test 2: With no orders (empty list):")
    
    empty_response = {
        "status": 200,
        "body": []
    }
    
    result2 = _evaluate_result_expression(expression, empty_response)
    
    print("\nResult:")
    pprint(result2, width=120)
    
    assert result2["recentOrders"] == [], "Expected empty recentOrders"
    assert result2["selectedOrderCandidate"] is None, "Expected null selectedOrderCandidate"
    assert result2["toolCallResult"]["status"] == "no_orders", "Expected no_orders status"
    
    print("\n[OK] Empty response handling passed")
    
    # Test with null response
    print("\n" + "=" * 80)
    print("Test 3: With null response:")
    
    null_response = {
        "status": 200,
        "body": None
    }
    
    result3 = _evaluate_result_expression(expression, null_response)
    
    print("\nResult:")
    pprint(result3, width=120)
    
    assert result3["recentOrders"] == [], "Expected empty recentOrders"
    assert result3["selectedOrderCandidate"] is None, "Expected null selectedOrderCandidate"
    
    print("\n[OK] Null response handling passed")
    
    print("\n" + "=" * 80)
    print("[OK] All FEEL expression tests passed!")
    print("=" * 80)


if __name__ == "__main__":
    try:
        test_list_orders_expression()
    except Exception as e:
        print(f"\nTest failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
