from fastapi import APIRouter, HTTPException
from models import PolicyEvaluationRequest, PolicyEvaluationResponse
from data_store import data_store

router = APIRouter()

# ========== Evaluate Return Policy ==========
@router.post("/returns/evaluate", response_model=PolicyEvaluationResponse)
async def evaluate_return_policy(request: PolicyEvaluationRequest):
    """Evaluate return policy with rules and exceptions"""
    
    # Verify order exists
    order = next((o for o in data_store.orders if o.order_id == request.order_id), None)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Base evaluation
    STANDARD_RETURN_DAYS = 30
    approved = request.days_since_delivery <= STANDARD_RETURN_DAYS
    restocking_fee = 0.0
    exception_applied = None
    policy_matched = "STANDARD_30_DAY"
    refund_type = "store_credit"
    notes = ""
    
    # Check for discontinued/clearance exception
    if request.lifecycle_status in ["discontinued", "clearance"]:
        approved = True
        exception_applied = "DISCONTINUED_ITEM_EXCEPTION"
        refund_type = "store_credit"
        notes = "Exception applied: Product discontinued. Store credit issued for exchange."
        policy_matched = "EXCEPTION_POLICY"
    
    # Check reason for additional policies
    if "defective" in request.reason.lower() or "broken" in request.reason.lower():
        approved = True
        exception_applied = "DEFECTIVE_PRODUCT"
        refund_type = "original_payment"
        restocking_fee = 0.0
        notes = "Defective product - full refund to original payment method"
    
    # Performance issues
    if "performance" in request.reason.lower() or "slow" in request.reason.lower():
        approved = True
        refund_type = "store_credit"
        restocking_fee = 0.0
        notes = "Performance issues reported - store credit for exchange recommended"
    
    return PolicyEvaluationResponse(
        approved=approved,
        policy_matched=policy_matched,
        exception_applied=exception_applied,
        refund_type=refund_type,
        restocking_fee=restocking_fee,
        notes=notes
    )
