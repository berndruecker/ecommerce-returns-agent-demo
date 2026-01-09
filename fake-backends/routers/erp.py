from fastapi import APIRouter, HTTPException, Query
from datetime import datetime, timedelta
from models import ReturnEligibility, SKUInfo, AvailabilityInfo
from data_store import data_store

router = APIRouter()

# ========== SKU Return Eligibility ==========
@router.get("/skus/{sku}/return-eligibility", response_model=ReturnEligibility)
async def check_return_eligibility(
    sku: str,
    orderId: str = Query(..., alias="orderId"),
    daysSinceDelivery: int = Query(..., alias="daysSinceDelivery")
):
    """Check if a SKU is eligible for return based on order and delivery date"""
    
    # Verify order exists
    order = next((o for o in data_store.orders if o.order_id == orderId), None)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Verify SKU is in order
    if not any(item.sku == sku for item in order.items):
        raise HTTPException(status_code=404, detail="SKU not found in order")
    
    # Standard return policy: 30 days
    STANDARD_RETURN_DAYS = 30
    
    if daysSinceDelivery <= STANDARD_RETURN_DAYS:
        return ReturnEligibility(
            eligible=True,
            reason="Within standard 30-day return window",
            days_remaining=STANDARD_RETURN_DAYS - daysSinceDelivery,
            restocking_fee=0.0
        )
    else:
        return ReturnEligibility(
            eligible=False,
            reason=f"Return window expired ({daysSinceDelivery} days since delivery, limit is {STANDARD_RETURN_DAYS})",
            days_remaining=0,
            restocking_fee=0.0
        )

# ========== SKU Lifecycle Info ==========
@router.get("/skus/{sku}", response_model=SKUInfo)
async def get_sku_info(sku: str):
    """Get SKU lifecycle and clearance information"""
    
    product = data_store.products.get(sku)
    if not product:
        raise HTTPException(status_code=404, detail="SKU not found")
    
    return SKUInfo(
        sku=sku,
        name=product.name,
        lifecycle_status=product.lifecycle_status,
        is_clearance=product.lifecycle_status == "clearance",
        is_discontinued=product.lifecycle_status == "discontinued",
        current_price=product.price
    )

# ========== Availability Check ==========
@router.get("/availability", response_model=AvailabilityInfo)
async def check_availability(sku: str = Query(...)):
    """Check product availability and stock level"""
    
    product = data_store.products.get(sku)
    if not product:
        raise HTTPException(status_code=404, detail="SKU not found")
    
    # Determine warehouse based on stock
    warehouse = "CA-SAN-01" if product.in_stock else "OUT_OF_STOCK"
    
    return AvailabilityInfo(
        sku=sku,
        available=product.in_stock,
        quantity=product.stock_quantity,
        warehouse_location=warehouse
    )
