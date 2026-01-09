from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, date
from enum import Enum

# ========== Common Models ==========

class OrderStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    RETURNED = "returned"
    CANCELLED = "cancelled"

class ProductCategory(str, Enum):
    ROUTERS = "routers"
    MODEMS = "modems"
    SWITCHES = "switches"
    ACCESSORIES = "accessories"

# ========== Customer & Address Models ==========

class Address(BaseModel):
    street: str
    city: str
    state: str
    postal_code: str
    country: str = "USA"

class Customer(BaseModel):
    customer_id: str
    name: str
    email: str
    phone: str
    address: Address

# ========== Product Models ==========

class Product(BaseModel):
    sku: str
    name: str
    category: ProductCategory
    price: float
    wifi_standard: Optional[int] = None  # 5, 6, 6E, 7
    tags: List[str] = []
    description: str
    lifecycle_status: str = "active"  # active, discontinued, clearance
    in_stock: bool = True
    stock_quantity: int = 100

# ========== Order Models ==========

class OrderItem(BaseModel):
    sku: str
    product_name: str
    quantity: int
    unit_price: float
    total_price: float

class Order(BaseModel):
    order_id: str
    customer_id: str
    order_date: datetime
    delivery_date: Optional[datetime] = None
    status: OrderStatus
    items: List[OrderItem]
    subtotal: float
    tax: float
    shipping: float
    total: float
    shipping_address: Address

# ========== RMA Models ==========

class RMA(BaseModel):
    rma_id: str
    order_id: str
    customer_id: str
    sku: str
    reason: str
    status: str = "approved"
    created_at: datetime = Field(default_factory=datetime.now)

# ========== Cart Models ==========

class CartItem(BaseModel):
    sku: str
    product_name: str
    quantity: int
    unit_price: float

class Cart(BaseModel):
    cart_id: str
    customer_id: str
    items: List[CartItem] = []
    store_credit_applied: float = 0.0
    created_at: datetime = Field(default_factory=datetime.now)
    
    @property
    def subtotal(self) -> float:
        return sum(item.quantity * item.unit_price for item in self.items)

# ========== Return Eligibility Models ==========

class ReturnEligibility(BaseModel):
    eligible: bool
    reason: str
    days_remaining: Optional[int] = None
    restocking_fee: float = 0.0

class SKUInfo(BaseModel):
    sku: str
    name: str
    lifecycle_status: str
    is_clearance: bool
    is_discontinued: bool
    current_price: float

class AvailabilityInfo(BaseModel):
    sku: str
    available: bool
    quantity: int
    warehouse_location: str

# ========== WMS Models ==========

class FulfillmentEligibility(BaseModel):
    eligible: bool
    estimated_delivery: str
    shipping_method: str
    warehouse: str

class ExpectedReturn(BaseModel):
    return_id: str
    sku: str
    customer_id: str
    reason: str
    override_reason: Optional[str] = None
    status: str = "expected"
    created_at: datetime = Field(default_factory=datetime.now)

class Shipment(BaseModel):
    shipment_id: str
    order_id: str
    tracking_number: str
    carrier: str
    estimated_delivery: str
    status: str = "released"

# ========== Policy Models ==========

class PolicyEvaluationRequest(BaseModel):
    order_id: str
    sku: str
    days_since_delivery: int
    reason: str
    lifecycle_status: str

class PolicyEvaluationResponse(BaseModel):
    approved: bool
    policy_matched: str
    exception_applied: Optional[str] = None
    refund_type: str  # store_credit, original_payment, exchange_only
    restocking_fee: float = 0.0
    notes: str

# ========== Returns Provider Models ==========

class ReturnLabel(BaseModel):
    label_id: str
    tracking_number: str
    carrier: str
    label_url: str
    expires_at: datetime

# ========== Payment Models ==========

class StoreCredit(BaseModel):
    credit_id: str
    customer_id: str
    amount: float
    reason: str
    created_at: datetime = Field(default_factory=datetime.now)
    applied: bool = False

class Charge(BaseModel):
    charge_id: str
    customer_id: str
    amount: float
    payment_method: str
    status: str = "completed"
    created_at: datetime = Field(default_factory=datetime.now)

# ========== Notification Models ==========

class EmailNotification(BaseModel):
    email_id: str
    to: str
    subject: str
    body: str
    attachments: List[str] = []
    sent_at: datetime = Field(default_factory=datetime.now)
