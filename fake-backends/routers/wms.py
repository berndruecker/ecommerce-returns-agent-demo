import logging
from fastapi import APIRouter, HTTPException, Query
from datetime import datetime, timedelta
from models import FulfillmentEligibility, ExpectedReturn, Shipment
from data_store import data_store

router = APIRouter()
logger = logging.getLogger("fake-services.wms")

# ========== Fulfillment Eligibility ==========
@router.get("/fulfillment/eligibility", response_model=FulfillmentEligibility)
async def check_fulfillment_eligibility(
    sku: str = Query(...),
    postalCode: str = Query(..., alias="postalCode")
):
    """Check if SKU can be fulfilled to postal code"""
    logger.info("### MANHATTAN WMS ### checkFulfillmentEligibility ### sku=%s, postalCode=%s", sku, postalCode)
    product = data_store.products.get(sku)
    if not product:
        raise HTTPException(status_code=404, detail="SKU not found")
    
    if not product.in_stock:
        response = FulfillmentEligibility(
            eligible=False,
            estimated_delivery="N/A - Out of stock",
            shipping_method="N/A",
            warehouse="N/A"
        )
        logger.info("WMS fulfillment-eligibility response: eligible=%s, reason=out_of_stock", response.eligible)
        return response
    
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
    
    response = FulfillmentEligibility(
        eligible=True,
        estimated_delivery=delivery_date.strftime("%Y-%m-%d %H:%M"),
        shipping_method=shipping_method,
        warehouse=warehouse
    )
    logger.info("WMS fulfillment-eligibility response: eligible=%s, method=%s, warehouse=%s", response.eligible, response.shipping_method, response.warehouse)
    return response

# ========== Create Expected Return ==========
@router.post("/returns/expected", response_model=ExpectedReturn)
async def create_expected_return(
    rmaId: str = Query(None),
    sku: str = Query(None),
    qty: int = Query(1),
    customer_id: str = Query(None),
    reason: str = Query(None),
    overrides: list[str] = Query(None),
    caseId: str = Query(None),
    approvalCode: str = Query(None)
):
    """Create an expected return record (Manhattan WMS)
    
    Supports overrides for special handling:
    - ALLOW_CLEARANCE_RETURN: Accept returns of clearance/EOL products
    - BYPASS_RESELL_CHECK: Skip resell eligibility verification
    - EXPEDITE_PROCESSING: Priority processing for this return
    """
    logger.info(
        "### MANHATTAN WMS ### createExpectedReturn ### rmaId=%s, sku=%s, qty=%s, overrides=%s",
        rmaId, sku, qty, overrides
    )
    
    # Verify customer exists if provided
    if customer_id:
        customer = next((c for c in data_store.customers if c.customer_id == customer_id), None)
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")
    
    from models import ExpectedReturnReference
    
    # Build reference from individual fields
    reference = None
    if caseId or approvalCode:
        reference = ExpectedReturnReference(case_id=caseId, approval_code=approvalCode)
    
    expected_return = ExpectedReturn(
        return_id=data_store.generate_id("RET"),
        rma_id=rmaId,
        sku=sku,
        customer_id=customer_id,
        qty=qty,
        reason=reason,
        overrides=overrides or [],
        reference=reference,
        status="expected",
        created_at=datetime.now()
    )
    
    data_store.expected_returns.append(expected_return)
    logger.info(
        "### MANHATTAN WMS ### createExpectedReturn ### return_id=%s, status=%s, overrides_applied=%s",
        expected_return.return_id, expected_return.status, len(expected_return.overrides)
    )
    return expected_return

# ========== Release Outbound Shipment ==========
@router.post("/shipments/release", response_model=Shipment)
async def release_shipment(
    order_id: str,
    shipping_method: str = "STANDARD"
):
    """Release a shipment for an order"""
    logger.info("### MANHATTAN WMS ### releaseShipment ### order_id=%s, shipping_method=%s", order_id, shipping_method)
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
    
    logger.info("WMS release-shipment response: shipment_id=%s, tracking=%s, carrier=%s, status=%s", shipment.shipment_id, shipment.tracking_number, shipment.carrier, shipment.status)
    return shipment
