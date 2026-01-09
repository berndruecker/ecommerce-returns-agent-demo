from fastapi import APIRouter, HTTPException
from datetime import datetime
from models import StoreCredit, Charge
from data_store import data_store

router = APIRouter()

# ========== Create Store Credit ==========
@router.post("/credits", response_model=StoreCredit)
async def create_store_credit(
    customer_id: str,
    amount: float,
    reason: str
):
    """Issue instant store credit"""
    
    # Verify customer exists
    customer = next((c for c in data_store.customers if c.customer_id == customer_id), None)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")
    
    credit = StoreCredit(
        credit_id=data_store.generate_id("CRD"),
        customer_id=customer_id,
        amount=amount,
        reason=reason,
        created_at=datetime.now(),
        applied=False
    )
    
    data_store.store_credits.append(credit)
    return credit

# ========== Charge Payment ==========
@router.post("/charges", response_model=Charge)
async def create_charge(
    customer_id: str,
    amount: float,
    payment_method: str = "credit_card"
):
    """Charge remaining balance"""
    
    # Verify customer exists
    customer = next((c for c in data_store.customers if c.customer_id == customer_id), None)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")
    
    charge = Charge(
        charge_id=data_store.generate_id("CHG"),
        customer_id=customer_id,
        amount=amount,
        payment_method=payment_method,
        status="completed",
        created_at=datetime.now()
    )
    
    data_store.charges.append(charge)
    return charge
