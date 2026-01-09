from fastapi import APIRouter, HTTPException, Query
from datetime import datetime, timedelta
from models import FulfillmentEligibility, ExpectedReturn, Shipment
from data_store import data_store

router = APIRouter()

# ========== Fulfillment Eligibility ==========
@router.get("/fulfillment/eligibility", response_model=FulfillmentEligibility)
async def check_fulfillment_eligibility(
    sku: str = Query(...),
    postalCode: str = Query(..., alias="postalCode")
):
    """Check if SKU can be fulfilled to postal code"""
    
    product = data_store.products.get(sku)
    if not product:
        raise HTTPException(status_code=404, detail="SKU not found")
    
    if not product.in_stock:
        return FulfillmentEligibility(
            eligible=False,
            estimated_delivery="N/A - Out of stock",
            shipping_method="N/A",
            warehouse="N/A"
        )
    
    # Check postal code for shipping method
    # CA postal codes get same-day, others get standard
    if postalCode.startswith("94") or postalCode.startswith("95"):
        shipping_method = "SAME_DAY"
        delivery_date = datetime.now() + timedelta(hours=6)
        warehouse = "CA-SAN-01"
    else:
        shipping_method = "STANDARD"
        delivery_date = datetime.now() + timedelta(days=3)
        warehouse = "CA-SAN-01"
    
    return FulfillmentEligibility(
        eligible=True,
        estimated_delivery=delivery_date.strftime("%Y-%m-%d %H:%M"),
        shipping_method=shipping_method,
        warehouse=warehouse
    )

# ========== Create Expected Return ==========
@router.post("/returns/expected", response_model=ExpectedReturn)
async def create_expected_return(
    sku: str,
    customer_id: str,
    reason: str,
    override_reason: str = None
):
    """Create an expected return record"""
    
    # Verify customer exists
    customer = next((c for c in data_store.customers if c.customer_id == customer_id), None)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    expected_return = ExpectedReturn(
        return_id=data_store.generate_id("RET"),
        sku=sku,
        customer_id=customer_id,
        reason=reason,
        override_reason=override_reason,
        status="expected",
        created_at=datetime.now()
    )
    
    data_store.expected_returns.append(expected_return)
    return expected_return

# ========== Release Outbound Shipment ==========
@router.post("/shipments/release", response_model=Shipment)
async def release_shipment(
    order_id: str,
    shipping_method: str = "STANDARD"
):
    """Release a shipment for an order"""
    
    # Verify order exists
    order = next((o for o in data_store.orders if o.order_id == order_id), None)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Determine carrier and delivery estimate
    if shipping_method == "SAME_DAY":
        carrier = "OnTrac"
        estimated_delivery = (datetime.now() + timedelta(hours=6)).strftime("%Y-%m-%d %H:%M")
    elif shipping_method == "OVERNIGHT":
        carrier = "FedEx"
        estimated_delivery = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d %H:%M")
    else:  # STANDARD
        carrier = "USPS"
        estimated_delivery = (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d %H:%M")
    
    shipment = Shipment(
        shipment_id=data_store.generate_id("SHIP"),
        order_id=order_id,
        tracking_number=data_store.generate_id("TRK"),
        carrier=carrier,
        estimated_delivery=estimated_delivery,
        status="released"
    )
    
    data_store.shipments.append(shipment)
    
    # Update order status
    order.status = "shipped"
    
    return shipment
