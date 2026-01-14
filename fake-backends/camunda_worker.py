import asyncio
import logging
import os
import json
from typing import Any, Dict, Tuple

import requests
from pyzeebe import Job, ZeebeWorker, create_camunda_cloud_channel, create_insecure_channel

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s %(message)s")
logger = logging.getLogger("magento-worker")

DEFAULT_API_BASE = "http://localhost:8100/commerce"

# Mapping of Camunda element IDs to operation names
ELEMENT_ID_TO_OPERATION = {
    "Tool_Magento_ListRecentOrders": "listOrders",
    "Tool_Magento_ProductSearch": "productSearch",
    "Tool_Magento_CreateRma": "createRma",
    "Tool_Magento_CreateCart": "createCart",
    "Tool_Magento_AddCartItem": "addCartItem",
    "Tool_Magento_ApplyStoreCredit": "applyStoreCredit",
    "Tool_Magento_PlaceOrder": "placeOrder",
}


def _get_env(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)
    return value if value not in (None, "") else default


def _create_channel():
    """Create Zeebe channel for Camunda 8 (SaaS or self-managed)."""
    client_id = _get_env("ZEEBE_CLIENT_ID")
    if client_id:
        logger.info("Using Camunda 8 SaaS channel")
        return create_camunda_cloud_channel(
            client_id=client_id,
            client_secret=_get_env("ZEEBE_CLIENT_SECRET", ""),
            cluster_id=_get_env("ZEEBE_ADDRESS", ""),
            region=_get_env("ZEEBE_REGION", "bru-2"),
            auth_server=_get_env(
                "ZEEBE_AUTHORIZATION_SERVER_URL",
                "https://login.cloud.camunda.io/oauth/token",
            ),
        )

    address = _get_env("ZEEBE_ADDRESS", "localhost:26500")
    logger.info("Using self-managed Zeebe channel to %s", address)
    return create_insecure_channel(grpc_address=address)

class MagentoConnectorError(Exception):
    """Raised when the Magento connector call fails."""


def _request(method: str, url: str, params: Dict[str, Any] | None = None) -> Tuple[int, Any]:
    try:
        response = requests.request(method=method, url=url, params=params, timeout=15)
        content_type = response.headers.get("Content-Type", "")
        if "application/json" in content_type:
            body = response.json()
        else:
            body = response.text
        return response.status_code, body
    except Exception as exc:  # pragma: no cover - demo-oriented
        raise MagentoConnectorError(f"Failed to call {url}: {exc}") from exc


def _evaluate_result_expression(expression: str, response: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluate a FEEL expression from task headers.
    Returns the result as a dict with workflow variables.
    """
    if not expression or not expression.strip():
        # Default: return raw response
        return {"magentoResponse": response}
    
    try:
        # Remove leading = if present (FEEL syntax in Camunda)
        expr = expression.lstrip("= \t")
        
        # Skip verbose FEEL expression logging to reduce noise
        # logger.info(f"Evaluating FEEL resultExpression (first 80 chars): {expr[:80]}...")
        
        # Use fallback evaluator
        return _evaluate_feel_fallback(expr, response)
        
    except Exception as e:
        logger.error(f"Error evaluating result expression: {e}", exc_info=True)
        return {"magentoResponse": response}

        # If result is a dict, return it as-is (contains all variables)
        if isinstance(result, dict):
            return result
        else:
            # If not a dict, wrap it
            return {"result": result}
            
    except ImportError:
        logger.warning("feelthere not installed, trying fallback evaluation")
        return _evaluate_feel_fallback(expression, response)
    except Exception as e:
        logger.error(f"Error evaluating resultExpression: {e}", exc_info=True)
        # Fallback to returning raw response
        return {"magentoResponse": response}


def _evaluate_feel_fallback(expression: str, response: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fallback FEEL evaluator for if/then/else and object literals.
    Handles basic FEEL syntax without external library.
    """
    try:
        import re
        
        expression = expression.strip()
        logger.debug(f"FEEL fallback evaluator: {expression[:100]}...")
        
        # Build evaluation context with Python equivalents of FEEL functions
        def feel_count(x):
            if isinstance(x, (list, dict, str)):
                return len(x)
            return 0
        
        eval_context = {
            "response": response,
            "count": feel_count,
            "string": str,
        }
        
        # Handle if/then/else: if <condition> then <then_expr> else <else_expr>
        # The condition may contain comparison operators, function calls
        # The expressions are usually object literals {...}
        
        # Find the if/then/else structure
        # We need to be careful about nested braces
        if_match = re.match(r'^\s*if\s+(.+?)\s+then\s+(\{.+?\})\s+else\s+(\{.+\})$', expression, re.DOTALL | re.IGNORECASE)
        
        if not if_match:
            # Try as direct object literal
            if expression.startswith('{'):
                logger.debug("Trying to parse as direct object literal")
                result = _parse_feel_dict_literal(expression, eval_context)
                return result if isinstance(result, dict) else {"magentoResponse": response}
            else:
                logger.warning(f"Could not parse FEEL expression (no if/then/else pattern)")
                return {"magentoResponse": response}
        
        # Extract parts
        condition_str = if_match.group(1).strip()
        then_obj_str = if_match.group(2).strip()
        else_obj_str = if_match.group(3).strip()
        
        logger.debug(f"Condition: {condition_str[:60]}...")
        
        # Evaluate condition
        try:
            condition_value = _evaluate_condition(condition_str, response)
            logger.debug(f"Condition result: {condition_value}")
            
            # Choose branch
            obj_str = then_obj_str if condition_value else else_obj_str
            logger.debug(f"Selected branch ({('then' if condition_value else 'else')}): {obj_str[:60]}...")
            
            # Parse the object
            result = _parse_feel_dict_literal(obj_str, eval_context)
            
            if result:
                logger.info(f"FEEL expression evaluated successfully: {list(result.keys())}")
                return result
            else:
                logger.warning("Could not parse FEEL object from selected branch")
                return {"magentoResponse": response}
                
        except Exception as e:
            logger.error(f"Error evaluating FEEL expression: {e}", exc_info=True)
            return {"magentoResponse": response}
            
    except Exception as e:
        logger.error(f"Fallback evaluator error: {e}", exc_info=True)
        return {"magentoResponse": response}


def _evaluate_condition(condition_str: str, response: Dict[str, Any]) -> bool:
    """
    Evaluate a FEEL condition like: response.body = null or count(response.body) = 0
    Returns: boolean result
    """
    import re
    
    try:
        # Build context with proper field access
        eval_context = {
            "response": response,
            "count": lambda x: len(x) if hasattr(x, '__len__') else 0,
        }
        
        # Replace FEEL operators and keywords with Python equivalents
        condition = condition_str
        
        # Replace field access: response.body -> response['body']
        # But be careful with function calls like count(response.body)
        condition = re.sub(r'response\.(\w+)', r"response['\1']", condition)
        
        # Replace 'or' and 'and' (already Python keywords, but ensure they're spaced)
        condition = re.sub(r'\bor\b', 'or', condition, flags=re.IGNORECASE)
        condition = re.sub(r'\band\b', 'and', condition, flags=re.IGNORECASE)
        
        # Replace 'null' with None
        condition = condition.replace('null', 'None')
        
        # Handle FEEL '=' with Python '=='
        # Replace ' = ' with ' == ' but not ' == '
        condition = re.sub(r'(\s)=(?!=)(\s)', r'\1==\2', condition)
        
        # Handle count(...) function calls - keep them as is, we have count in context
        
        # Evaluate the condition
        logger.debug(f"Evaluating condition (Python): {condition}")
        logger.debug(f"Response: {response}")
        result = eval(condition, {"__builtins__": {}}, eval_context)
        
        logger.info(f"Condition result: {result} (body count: {len(response.get('body', [])) if response.get('body') else 0})")
        return bool(result)
        
    except Exception as e:
        # Silently fail condition evaluation - default to False for else branch
        # logger.warning(f"Error evaluating condition '{condition_str}': {e}")
        # logger.warning(f"Response at error: {response}")
        # If condition fails, default to False to use else branch
        return False


def _parse_feel_dict_literal(dict_str: str, eval_context: Dict[str, Any]) -> Dict[str, Any] | None:
    """
    Parse a FEEL object literal like: {key: value, nested: {key: value}, arr: array[1]}
    Handles field access (response.body[0].field), function calls, string concatenation, etc.
    """
    import re
    
    try:
        dict_str = dict_str.strip()
        
        if not dict_str.startswith('{') or not dict_str.endswith('}'):
            logger.debug(f"Not an object literal: {dict_str[:50]}")
            return None
        
        # Remove outer braces
        content = dict_str[1:-1]
        
        result = {}
        i = 0
        
        while i < len(content):
            # Skip whitespace
            while i < len(content) and content[i] in ' \n\t\r':
                i += 1
            
            if i >= len(content):
                break
            
            # Parse key
            key_match = re.match(r'([a-zA-Z_][a-zA-Z0-9_]*)\s*:', content[i:])
            if not key_match:
                i += 1
                continue
            
            key = key_match.group(1)
            i += len(key_match.group(0))
            
            # Skip whitespace
            while i < len(content) and content[i] in ' \n\t\r':
                i += 1
            
            # Find the value (until comma or end)
            value_start = i
            brace_depth = 0
            bracket_depth = 0
            in_string = False
            escape = False
            
            while i < len(content):
                char = content[i]
                
                if escape:
                    escape = False
                    i += 1
                    continue
                
                if char == '\\':
                    escape = True
                    i += 1
                    continue
                
                if char == '"':
                    in_string = not in_string
                    i += 1
                    continue
                
                if in_string:
                    i += 1
                    continue
                
                if char == '{':
                    brace_depth += 1
                elif char == '}':
                    if brace_depth == 0:
                        break
                    brace_depth -= 1
                elif char == '[':
                    bracket_depth += 1
                elif char == ']':
                    bracket_depth -= 1
                elif char == ',' and brace_depth == 0 and bracket_depth == 0:
                    break
                
                i += 1
            
            value_str = content[value_start:i].strip()
            
            # Evaluate the value
            try:
                logger.debug(f"Evaluating value for key '{key}': {value_str[:100]}")
                value = _evaluate_feel_value(value_str, eval_context)
                result[key] = value
                logger.debug(f"Parsed {key}: {type(value).__name__} = {str(value)[:100]}")
            except Exception as e:
                logger.debug(f"Could not evaluate value for key '{key}': {value_str[:50]} - {e}")
                # Try as string literal
                value_str_unquoted = value_str.strip('"')
                result[key] = value_str_unquoted
            
            # Skip comma
            while i < len(content) and content[i] in ',\n\t\r ':
                i += 1
        
        return result if result else None
        
    except Exception as e:
        logger.error(f"Error parsing FEEL dict: {e}", exc_info=True)
        return None


def _evaluate_feel_value(value_str: str, eval_context: Dict[str, Any]) -> Any:
    """
    Evaluate a single FEEL value which can be:
    - A literal: "string", 123, true, false, null
    - A field access: response.body, response.body[0]
    - A function call: count(arr), string(x)
    - An object: {...}
    - An array subscript: arr[0], nested[1].field
    - String concatenation: "text" + response.field
    """
    import re
    
    value_str = value_str.strip()
    
    # Handle nested object
    if value_str.startswith('{') and value_str.endswith('}'):
        return _parse_feel_dict_literal(value_str, eval_context)
    
    # Handle array literal [...]
    if value_str.startswith('[') and value_str.endswith(']'):
        inner = value_str[1:-1].strip()
        if not inner:
            return []
        # Try to parse as Python array
        try:
            return eval(f'[{inner}]', {"__builtins__": {}}, eval_context)
        except:
            return []
    
    # Handle string literals (but not if there's a + after)
    if ((value_str.startswith('"') and value_str.endswith('"')) or (value_str.startswith("'") and value_str.endswith("'"))) \
            and '+' not in value_str[1:-1]:  # Make sure there's no concatenation inside
        return value_str[1:-1]
    
    # Handle FEEL keywords
    if value_str.lower() == 'null':
        return None
    if value_str.lower() == 'true':
        return True
    if value_str.lower() == 'false':
        return False
    
    # Handle string concatenation: "text" + field + " more"
    if '+' in value_str:
        logger.debug(f"Handling concatenation: {value_str[:80]}...")
        
        # Split by + but respect nesting (quotes, brackets, etc.)
        parts = []
        current = ""
        in_string = False
        escape = False
        depth = 0
        
        for char in value_str:
            if escape:
                current += char
                escape = False
                continue
            
            if char == '\\':
                current += char
                escape = True
                continue
            
            if char == '"':
                in_string = not in_string
                current += char
                continue
            
            if in_string:
                current += char
                continue
            
            if char in '([{':
                depth += 1
                current += char
            elif char in ')]}':
                depth -= 1
                current += char
            elif char == '+' and depth == 0:
                # Top-level concatenation operator
                if current.strip():
                    parts.append(current.strip())
                current = ""
            else:
                current += char
        
        if current.strip():
            parts.append(current.strip())
        
        # Evaluate and concatenate
        if len(parts) > 1:
            result_parts = []
            for part in parts:
                try:
                    part_val = _evaluate_feel_value(part, eval_context)
                    result_parts.append(str(part_val) if part_val is not None else '')
                except Exception as e:
                    logger.debug(f"Error evaluating concat part '{part}': {e}")
                    result_parts.append(str(part))
            return ''.join(result_parts)
        # If only one part, continue to other evaluation methods
    
    # Handle function calls like count(...), string(...)
    if '(' in value_str and ')' in value_str:
        func_match = re.match(r'(\w+)\s*\((.+)\)$', value_str)
        if func_match:
            func_name = func_match.group(1)
            args_str = func_match.group(2)
            
            # Evaluate args
            try:
                if func_name.lower() == 'count':
                    # count(x) -> len(x)
                    arg_val = _evaluate_field_access(args_str, eval_context)
                    return len(arg_val) if hasattr(arg_val, '__len__') else 0
                elif func_name.lower() == 'string':
                    # string(x) -> str(x)
                    arg_val = _evaluate_field_access(args_str, eval_context)
                    return str(arg_val)
                else:
                    # Try in eval context
                    if func_name in eval_context:
                        arg_val = _evaluate_field_access(args_str, eval_context)
                        return eval_context[func_name](arg_val)
            except Exception as e:
                logger.debug(f"Error evaluating function {func_name}: {e}")
    
    # Handle field access like response.body, response.body[0].field
    if '.' in value_str or '[' in value_str:
        try:
            return _evaluate_field_access(value_str, eval_context)
        except Exception as e:
            logger.debug(f"Error evaluating field access '{value_str}': {e}")
    
    # Try as numeric literal
    try:
        if '.' in value_str:
            return float(value_str)
        else:
            return int(value_str)
    except:
        pass
    
    # Fallback: try Python eval
    try:
        return eval(value_str, {"__builtins__": {}}, eval_context)
    except:
        logger.debug(f"Could not evaluate value: {value_str}")
        return value_str


def _evaluate_field_access(field_str: str, eval_context: Dict[str, Any]) -> Any:
    """
    Evaluate field access like:
    - response
    - response.body
    - response.body[0]
    - response.body[0].field
    - response.body[1].items[1].product_name
    """
    import re
    
    field_str = field_str.strip()
    logger.debug(f"Evaluating field access: {field_str}")
    
    # Start with response object
    if not field_str.startswith('response'):
        logger.debug(f"Field access must start with 'response', got: {field_str}")
        return None
    
    # Get the response object
    result = eval_context.get('response')
    
    # Remove 'response' prefix and process the rest
    rest = field_str[8:]  # len('response') = 8
    
    if not rest:
        return result
    
    # Use a more robust parser for the access chain
    i = 0
    while i < len(rest):
        if rest[i] == '.':
            # Field access (.field)
            i += 1
            # Extract field name until we hit . or [ or end
            field_match = re.match(r'([a-zA-Z_][a-zA-Z0-9_]*)', rest[i:])
            if not field_match:
                logger.debug(f"Invalid field at position {i}")
                return None
            
            field_name = field_match.group(1)
            i += len(field_name)
            
            # Access the field
            if result is None:
                return None
            
            if isinstance(result, dict):
                result = result.get(field_name)
                logger.debug(f"Accessed dict['{field_name}'] -> {type(result).__name__}")
            elif hasattr(result, field_name):
                result = getattr(result, field_name)
                logger.debug(f"Accessed .{field_name} -> {type(result).__name__}")
            else:
                logger.debug(f"Field '{field_name}' not found on {type(result).__name__}")
                return None
        
        elif rest[i] == '[':
            # Array/dict access ([index])
            i += 1
            # Find the closing bracket
            bracket_end = rest.find(']', i)
            if bracket_end == -1:
                logger.debug(f"No closing bracket found")
                return None
            
            index_str = rest[i:bracket_end].strip()
            i = bracket_end + 1
            
            if result is None:
                return None
            
            # Try to parse as integer or string
            try:
                # Try as integer first
                index = int(index_str)
                if isinstance(result, (list, tuple)):
                    # FEEL uses 1-based indexing; convert to 0-based for Python
                    py_index = index - 1
                    if 0 <= py_index < len(result):
                        result = result[py_index]
                        logger.debug(f"Accessed [FEEL {index} -> py {py_index}] -> {type(result).__name__}")
                    else:
                        logger.debug(f"Index (FEEL) {index} out of range for {len(result)} items")
                        return None
                elif isinstance(result, dict):
                    result = result.get(index)
                    logger.debug(f"Accessed dict[{index}]")
                elif isinstance(result, str):
                    result = result[index] if index < len(result) else None
                else:
                    logger.debug(f"Cannot index into {type(result).__name__}")
                    return None
            except ValueError:
                # String key
                if isinstance(result, dict):
                    result = result.get(index_str)
                    logger.debug(f"Accessed dict['{index_str}']")
                else:
                    logger.debug(f"Cannot access field '{index_str}' on {type(result).__name__}")
                    return None
        
        elif rest[i] in ' \t':
            # Skip whitespace
            i += 1
        else:
            logger.debug(f"Unexpected character at position {i}: {rest[i]}")
            break
    
    return result



def _build_url(base: str, path: str) -> str:
    return f"{base.rstrip('/')}/{path.lstrip('/')}"


def _get(vars: Dict[str, Any], *keys: str, default: Any = None) -> Any:
    for key in keys:
        if key in vars and vars[key] not in (None, ""):
            return vars[key]
    return default


def _handle_operation(operation: str, vars: Dict[str, Any]) -> Dict[str, Any]:
    base = _get(vars, "apiBaseUrl", default=_get_env("MAGENTO_API_BASE", DEFAULT_API_BASE))

    match operation:
        case "listOrders":
            customer_id = _get(vars, "customerId", "customer_id")
            limit = _get(vars, "limit", default=5)
            if not customer_id:
                raise MagentoConnectorError("customerId is required for listOrders")
            url = _build_url(base, f"customers/{customer_id}/orders")
            status, body = _request("GET", url, params={"limit": limit})
        case "productSearch":
            params = {}
            for key in ("category", "wifiMin", "tags"):
                value = _get(vars, key)
                if value not in (None, ""):
                    params[key] = value
            url = _build_url(base, "catalog/products")
            status, body = _request("GET", url, params=params or None)
        case "createRma":
            order_id = _get(vars, "orderId", "order_id")
            customer_id = _get(vars, "customerId", "customer_id")
            sku = _get(vars, "sku")
            reason = _get(vars, "reason")
            if not all([order_id, customer_id, sku, reason]):
                raise MagentoConnectorError("orderId, customerId, sku, and reason are required for createRma")
            url = _build_url(base, "rmas")
            status, body = _request(
                "POST", url, params={"order_id": order_id, "customer_id": customer_id, "sku": sku, "reason": reason}
            )
        case "createCart":
            customer_id = _get(vars, "customerId", "customer_id")
            if not customer_id:
                raise MagentoConnectorError("customerId is required for createCart")
            url = _build_url(base, "carts")
            status, body = _request("POST", url, params={"customer_id": customer_id})
        case "addCartItem":
            cart_id = _get(vars, "cartId", "cart_id")
            sku = _get(vars, "sku")
            quantity = int(_get(vars, "quantity", default=1))
            if not cart_id or not sku:
                raise MagentoConnectorError("cartId and sku are required for addCartItem")
            url = _build_url(base, f"carts/{cart_id}/items")
            status, body = _request("POST", url, params={"sku": sku, "quantity": quantity})
        case "applyStoreCredit":
            cart_id = _get(vars, "cartId", "cart_id")
            amount = _get(vars, "amount")
            if cart_id is None or amount is None:
                raise MagentoConnectorError("cartId and amount are required for applyStoreCredit")
            url = _build_url(base, f"carts/{cart_id}/discounts/store-credit")
            status, body = _request("POST", url, params={"amount": amount})
        case "placeOrder":
            cart_id = _get(vars, "cartId", "cart_id")
            payment_method = _get(vars, "paymentMethod", default="credit_card")
            if not cart_id:
                raise MagentoConnectorError("cartId is required for placeOrder")
            url = _build_url(base, "orders")
            status, body = _request("POST", url, params={"cart_id": cart_id, "payment_method": payment_method})
        case _:
            raise MagentoConnectorError(f"Unsupported operation: {operation}")

    return {"status": status, "body": body}


def magento_connector(job: Job) -> Dict[str, Any]:
    """Route Camunda job to the fake Magento endpoints based on operation selection."""
    variables = job.variables or {}
    
    # Try to get operation from multiple sources
    operation = _get(variables, "operation")
    
    # If no operation variable, try to map from elementId
    if not operation and job.element_id:
        operation = ELEMENT_ID_TO_OPERATION.get(job.element_id)
    
    # If still no operation, check headers
    if not operation:
        custom_headers = job.custom_headers or {}
        operation = custom_headers.get("operation")
    
    if not operation:
        logger.error(f"operation not found in variables, headers, or element mapping")
        logger.error(f"  ElementId: {job.element_id}")
        raise MagentoConnectorError("operation is required")

    # Log relevant context
    customer_id = _get(variables, "customerId", "customer_id")
    logger.info(f"[{job.key}] Executing {operation} for customer {customer_id}")
    
    result = _handle_operation(operation, variables)
    
    # Log the result for debugging FEEL expression issues
    if result.get('body'):
        body_type = type(result.get('body')).__name__
        body_info = f"(len={len(result['body'])})" if isinstance(result['body'], list) else ""
        logger.info(f"[{job.key}] API Result: status={result.get('status')}, body_type={body_type} {body_info}")
        if isinstance(result.get('body'), list) and len(result.get('body')) > 0:
            first_item = result['body'][0]
            if isinstance(first_item, dict):
                logger.debug(f"[{job.key}] First item keys: {list(first_item.keys())}")

    # Check for resultExpression in task headers
    custom_headers = job.custom_headers or {}
    result_expression = custom_headers.get("resultExpression")
    result_variable = _get(variables, "resultVariable", default="magentoResponse")
    
    # If resultExpression is provided, evaluate it to get multiple output variables
    if result_expression:
        output_vars = _evaluate_result_expression(result_expression, result)
        logger.info(f"[{job.key}] Applied resultExpression, returning {len(output_vars)} variables")
        return output_vars
    else:
        # Default: return raw response in the result variable
        return {result_variable: result}


async def _worker_main():
    # Ensure channel is created inside the running event loop (required by grpc.aio)
    channel = _create_channel()
    worker = ZeebeWorker(channel)

    # register task dynamically to avoid binding to a worker created on a different loop
    # Use "*" to fetch all process variables (Zeebe convention)
    worker.task(
        task_type="magento-connector",
        timeout_ms=120000,
        variables_to_fetch=[]  # fetch all process variables
    )(magento_connector)

    await worker.work()


def run_worker():
    logger.info("Starting Magento connector worker ...")
    # pyzeebe 3.x work() is async; create loop inside this thread
    asyncio.run(_worker_main())


if __name__ == "__main__":
    run_worker()
