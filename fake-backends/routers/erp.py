import logging
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Query
from fastapi.encoders import jsonable_encoder
from models import ReturnEligibility, SKUInfo, AvailabilityInfo
from data_store import data_store

router = APIRouter()
logger = logging.getLogger("fake-services.erp")

def _log(operation: str, parameters: dict, response):
    """Helper to log business operations"""
    data_store.log_operation(
        system="SAP ERP",
        operation=operation,
        parameters=parameters,
        response=jsonable_encoder(response)
    )

# ========== SKU Return Eligibility ==========
@router.get("/skus/{sku}/return-eligibility", response_model=ReturnEligibility)
async def check_return_eligibility(
    sku: str,
    orderId: str = Query(..., alias="orderId"),
    daysSinceDelivery: int = Query(..., alias="daysSinceDelivery")
):
    """Check if a SKU is eligible for return based on order and delivery date"""
    logger.info(
        "ERP return-eligibility request: sku=%s, orderId=%s, daysSinceDelivery=%s",
        sku,
        orderId,
        daysSinceDelivery,
    )
    
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
        response = ReturnEligibility(
            eligible=True,
            reason="Within standard 30-day return window",
            days_remaining=STANDARD_RETURN_DAYS - daysSinceDelivery,
            restocking_fee=0.0
        )
    else:
        response = ReturnEligibility(
            eligible=False,
            reason=f"Return window expired ({daysSinceDelivery} days since delivery, limit is {STANDARD_RETURN_DAYS})",
            days_remaining=0,
            restocking_fee=0.0
        )

    logger.info(
        "ERP return-eligibility response: eligible=%s, days_remaining=%s, restocking_fee=%s, reason=%s",
        response.eligible,
        response.days_remaining,
        response.restocking_fee,
        response.reason,
    )
    _log("checkReturnEligibility", {"sku": sku, "orderId": orderId, "daysSinceDelivery": daysSinceDelivery}, response)
    return response

# ========== SKU Lifecycle Info ==========
@router.get("/skus/{sku}", response_model=SKUInfo)
async def get_sku_info(sku: str):
    """Get SKU lifecycle and clearance information"""
    logger.info("ERP sku-info request: sku=%s", sku)
    product = data_store.products.get(sku)
    if not product:
        raise HTTPException(status_code=404, detail="SKU not found")

    response = SKUInfo(
        sku=sku,
        name=product.name,
        lifecycle_status=product.lifecycle_status,
        is_clearance=product.lifecycle_status == "clearance",
        is_discontinued=product.lifecycle_status == "discontinued",
        current_price=product.price
    )
    logger.info(
        "ERP sku-info response: sku=%s, lifecycle=%s, clearance=%s, discontinued=%s, price=%s",
        response.sku,
        response.lifecycle_status,
        response.is_clearance,
        response.is_discontinued,
        response.current_price,
    )
    _log("getSkuInfo", {"sku": sku}, response)
    return response

# ========== Availability Check ==========
@router.get("/availability", response_model=AvailabilityInfo)
async def check_availability(sku: str = Query(...)):
    """Check product availability and stock level"""
    logger.info("ERP availability request: sku=%s", sku)
    product = data_store.products.get(sku)
    if not product:
        raise HTTPException(status_code=404, detail="SKU not found")
    
    # Determine warehouse based on stock
    warehouse = "CA-SAN-01" if product.in_stock else "OUT_OF_STOCK"
    
    response = AvailabilityInfo(
        sku=sku,
        available=product.in_stock,
        quantity=product.stock_quantity,
        warehouse_location=warehouse
    )
    logger.info(
        "ERP availability response: sku=%s, available=%s, qty=%s, warehouse=%s",
        response.sku,
        response.available,
        response.quantity,
        response.warehouse_location,
    )
    _log("checkAvailability", {"sku": sku}, response)
    return response
