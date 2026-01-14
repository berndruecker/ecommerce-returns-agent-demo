import logging
from fastapi import APIRouter, HTTPException
from datetime import datetime, timedelta
from models import ReturnLabel
from data_store import data_store

router = APIRouter()
logger = logging.getLogger("fake-services.returns-provider")

# ========== Generate Return Label ==========
@router.post("/labels", response_model=ReturnLabel)
async def generate_return_label(
    customer_id: str,
    rma_id: str,
    carrier: str = "USPS"
):
    """Generate a prepaid return shipping label"""
    logger.info("Returns-provider generate-label request: customer_id=%s, rma_id=%s, carrier=%s", customer_id, rma_id, carrier)
    # Verify customer exists
    customer = next((c for c in data_store.customers if c.customer_id == customer_id), None)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    # Verify RMA exists
    rma = next((r for r in data_store.rmas if r.rma_id == rma_id), None)
    if not rma:
        raise HTTPException(status_code=404, detail="RMA not found")
    
    # Generate label
    label = ReturnLabel(
        label_id=data_store.generate_id("LBL"),
        tracking_number=data_store.generate_id("TRK"),
        carrier=carrier,
        label_url=f"https://returns.example.com/labels/{data_store.generate_id('LBL')}.pdf",
        expires_at=datetime.now() + timedelta(days=30)
    )
    
    data_store.return_labels.append(label)
    logger.info("Returns-provider generate-label response: label_id=%s, tracking=%s, carrier=%s", label.label_id, label.tracking_number, label.carrier)
    return label
