import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.encoders import jsonable_encoder

from models import Order, Product, RMA, Cart, CartItem, OrderItem, OrderStatus, Address
from data_store import data_store

router = APIRouter()
logger = logging.getLogger("fake-services.commerce")


def _log(system: str, operation: str, parameters, response):
    data_store.log_operation(system=system, operation=operation, parameters=jsonable_encoder(parameters), response=jsonable_encoder(response))

# ========== List Recent Orders ==========
@router.get("/customers/{customer_id}/orders", response_model=List[Order])
async def list_recent_orders(
    customer_id: str,
    limit: int = Query(5, ge=1, le=50)
):
    """List recent orders for a customer"""
    logger.info("### MAGENTO ### listOrders ### customer_id=%s, limit=%s", customer_id, limit)
    customer_orders = [
        order for order in data_store.orders 
        if order.customer_id == customer_id
    ]
    # Sort by order date descending
    customer_orders.sort(key=lambda x: x.order_date, reverse=True)
    result = customer_orders[:limit]
    logger.info("Commerce list-orders response: customer_id=%s, count=%s", customer_id, len(result))
    _log("Magento", "listRecentOrders", {"customer_id": customer_id, "limit": limit}, result)
    return result

# ========== Product Search ==========
@router.get("/catalog/products", response_model=List[Product])
async def search_products(
    query: Optional[str] = None,
    category: Optional[str] = None,
    tags: Optional[str] = None
):
    """Search products with filters"""
    logger.info("### MAGENTO ### productSearch ### query=%s, category=%s, tags=%s", query, category, tags)
    results = list(data_store.products.values())
    
    # Filter by free-text query (searches name, description, tags)
    if query:
        query_lower = query.lower()
        results = [
            p for p in results 
            if query_lower in p.name.lower() 
            or query_lower in p.description.lower()
            or any(query_lower in tag.lower() for tag in p.tags)
        ]
    
    # Filter by category
    if category:
        results = [p for p in results if p.category.value == category]
    
    # Filter by tags (comma-separated)
    if tags:
        tag_list = [t.strip() for t in tags.split(",")]
        results = [
            p for p in results 
            if any(tag in p.tags for tag in tag_list)
        ]
    
    # Sort by price descending (show premium options first)
    results.sort(key=lambda x: x.price, reverse=True)
    logger.info("Commerce search-products response: count=%s", len(results))
    _log("Magento", "productSearch", {"query": query, "category": category, "tags": tags}, results)
    return results

# ========== Create RMA ==========
@router.post("/rmas", response_model=RMA)
async def create_rma(
    order_id: str,
    customer_id: str,
    sku: str,
    reason: str
):
    """Create a return merchandise authorization"""
    logger.info("### MAGENTO ### createRma ### order_id=%s, customer_id=%s, sku=%s", order_id, customer_id, sku)
    # Verify order exists
    order = next((o for o in data_store.orders if o.order_id == order_id), None)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Verify SKU is in the order
    if not any(item.sku == sku for item in order.items):
        raise HTTPException(status_code=400, detail="SKU not found in order")
    
    rma = RMA(
        rma_id=data_store.generate_id("RMA"),
        order_id=order_id,
        customer_id=customer_id,
        sku=sku,
        reason=reason,
        status="approved",
        created_at=datetime.now()
    )
    
    data_store.rmas.append(rma)
    logger.info("Commerce create-rma response: rma_id=%s, status=%s", rma.rma_id, rma.status)
    _log("Magento", "createRma", {"order_id": order_id, "customer_id": customer_id, "sku": sku, "reason": reason}, rma)
    return rma

# ========== Create Cart ==========
@router.post("/carts", response_model=Cart)
async def create_cart(customer_id: str):
    """Create a new shopping cart"""
    logger.info("### MAGENTO ### createCart ### customer_id=%s", customer_id)
    cart = Cart(
        cart_id=data_store.generate_id("CART"),
        customer_id=customer_id,
        items=[],
        created_at=datetime.now()
    )
    
    data_store.carts[cart.cart_id] = cart
    _log("Magento", "createCart", {"customer_id": customer_id}, cart)
    return cart

# ========== Add Item to Cart ==========
@router.post("/carts/{cart_id}/items", response_model=Cart)
async def add_cart_item(
    cart_id: str,
    sku: str,
    quantity: int = 1
):
    """Add an item to cart"""
    logger.info("### MAGENTO ### addCartItem ### cart_id=%s, sku=%s, quantity=%s", cart_id, sku, quantity)
    cart = data_store.carts.get(cart_id)
    if not cart:
        raise HTTPException(status_code=404, detail="Cart not found")
    
    product = data_store.products.get(sku)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Check if item already in cart
    existing_item = next((item for item in cart.items if item.sku == sku), None)
    if existing_item:
        existing_item.quantity += quantity
    else:
        cart.items.append(CartItem(
            sku=sku,
            product_name=product.name,
            quantity=quantity,
            unit_price=product.price
        ))
    _log("Magento", "addCartItem", {"cart_id": cart_id, "sku": sku, "quantity": quantity}, cart)
    return cart

# ========== Apply Store Credit ==========
@router.post("/carts/{cart_id}/discounts/store-credit", response_model=Cart)
async def apply_store_credit(
    cart_id: str,
    amount: float
):
    """Apply store credit to cart"""
    logger.info("### MAGENTO ### applyStoreCredit ### cart_id=%s, amount=%s", cart_id, amount)
    cart = data_store.carts.get(cart_id)
    if not cart:
        raise HTTPException(status_code=404, detail="Cart not found")
    
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")
    
    # Limit to cart subtotal
    cart.store_credit_applied = min(amount, cart.subtotal)
    _log("Magento", "applyStoreCredit", {"cart_id": cart_id, "amount": amount}, cart)
    return cart

# ========== Place Order ==========
@router.post("/orders", response_model=Order)
async def place_order(
    cart_id: str,
    payment_method: str = "credit_card"
):
    """Place an order from cart"""
    logger.info("### MAGENTO ### placeOrder ### cart_id=%s, payment_method=%s", cart_id, payment_method)
    cart = data_store.carts.get(cart_id)
    if not cart:
        raise HTTPException(status_code=404, detail="Cart not found")
    
    if not cart.items:
        raise HTTPException(status_code=400, detail="Cart is empty")
    
    # Get customer
    customer = next((c for c in data_store.customers if c.customer_id == cart.customer_id), None)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    # Calculate totals
    subtotal = cart.subtotal
    tax = round(subtotal * 0.08, 2)  # 8% tax
    shipping = 0.0 if subtotal > 50 else 8.99  # Free shipping over $50
    total = subtotal + tax + shipping - cart.store_credit_applied
    
    # Create order
    order = Order(
        order_id=data_store.generate_id("ORD"),
        customer_id=cart.customer_id,
        order_date=datetime.now(),
        status=OrderStatus.PROCESSING,
        items=[
            OrderItem(
                sku=item.sku,
                product_name=item.product_name,
                quantity=item.quantity,
                unit_price=item.unit_price,
                total_price=item.quantity * item.unit_price
            ) for item in cart.items
        ],
        subtotal=subtotal,
        tax=tax,
        shipping=shipping,
        total=total,
        shipping_address=customer.address
    )
    
    data_store.orders.append(order)
    
    # Clear cart
    del data_store.carts[cart_id]
    _log("Magento", "placeOrder", {"cart_id": cart_id, "payment_method": payment_method}, order)
    return order
