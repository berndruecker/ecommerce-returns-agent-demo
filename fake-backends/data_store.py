from datetime import datetime, timedelta
from typing import Dict, List
from models import (
    Customer, Address, Product, ProductCategory, Order, OrderStatus, 
    OrderItem, RMA, Cart, ExpectedReturn, Shipment, StoreCredit, 
    Charge, EmailNotification, ReturnLabel
)
import uuid

class DataStore:
    """In-memory data store for demo data"""
    
    def __init__(self):
        self.customers: List[Customer] = []
        self.products: Dict[str, Product] = {}
        self.orders: List[Order] = []
        self.rmas: List[RMA] = []
        self.carts: Dict[str, Cart] = {}
        self.expected_returns: List[ExpectedReturn] = []
        self.shipments: List[Shipment] = []
        self.store_credits: List[StoreCredit] = []
        self.charges: List[Charge] = []
        self.email_notifications: List[EmailNotification] = []
        self.return_labels: List[ReturnLabel] = []
        
        self._initialize_demo_data()
    
    def _initialize_demo_data(self):
        """Initialize sample data for the demo"""
        
        # Sample Customer
        customer_address = Address(
            street="123 Main Street",
            city="San Francisco",
            state="CA",
            postal_code="94102",
            country="USA"
        )
        
        self.customers.append(Customer(
            customer_id="CUST001",
            name="John Smith",
            email="john.smith@example.com",
            phone="+1-555-0123",
            address=customer_address
        ))
        
        # Sample Products - Current router being returned
        self.products["RTR-AC1900"] = Product(
            sku="RTR-AC1900",
            name="AC1900 Dual-Band WiFi Router",
            category=ProductCategory.ROUTERS,
            price=129.99,
            wifi_standard=5,
            tags=["ac1900", "dual-band", "basic"],
            description="Basic AC1900 router suitable for light browsing",
            lifecycle_status="discontinued",
            in_stock=False,
            stock_quantity=0
        )
        
        # Better replacement products
        self.products["RTR-AX5400"] = Product(
            sku="RTR-AX5400",
            name="AX5400 WiFi 6 Gaming Router",
            category=ProductCategory.ROUTERS,
            price=199.99,
            wifi_standard=6,
            tags=["gaming", "low-latency", "wifi6", "mesh-ready"],
            description="High-performance WiFi 6 router optimized for gaming and video calls with advanced QoS",
            lifecycle_status="active",
            in_stock=True,
            stock_quantity=45
        )
        
        self.products["RTR-AXE7800"] = Product(
            sku="RTR-AXE7800",
            name="AXE7800 Tri-Band WiFi 6E Gaming Router",
            category=ProductCategory.ROUTERS,
            price=349.99,
            wifi_standard=7,  # WiFi 6E
            tags=["gaming", "low-latency", "wifi6e", "tri-band", "professional"],
            description="Premium WiFi 6E tri-band router with dedicated 6GHz band for ultra-low latency",
            lifecycle_status="active",
            in_stock=True,
            stock_quantity=23
        )
        
        self.products["RTR-AX3000"] = Product(
            sku="RTR-AX3000",
            name="AX3000 WiFi 6 Router",
            category=ProductCategory.ROUTERS,
            price=149.99,
            wifi_standard=6,
            tags=["wifi6", "value", "home-office"],
            description="Affordable WiFi 6 router great for home office and streaming",
            lifecycle_status="active",
            in_stock=True,
            stock_quantity=78
        )
        
        # Sample Order - Recent delivery of the router being returned
        delivery_date = datetime.now() - timedelta(days=12)
        order_date = delivery_date - timedelta(days=3)
        
        self.orders.append(Order(
            order_id="ORD-2025-001234",
            customer_id="CUST001",
            order_date=order_date,
            delivery_date=delivery_date,
            status=OrderStatus.DELIVERED,
            items=[
                OrderItem(
                    sku="RTR-AC1900",
                    product_name="AC1900 Dual-Band WiFi Router",
                    quantity=1,
                    unit_price=129.99,
                    total_price=129.99
                )
            ],
            subtotal=129.99,
            tax=10.40,
            shipping=8.99,
            total=149.38,
            shipping_address=customer_address
        ))
        
        # Additional older orders for context
        self.orders.append(Order(
            order_id="ORD-2024-998877",
            customer_id="CUST001",
            order_date=datetime.now() - timedelta(days=90),
            delivery_date=datetime.now() - timedelta(days=87),
            status=OrderStatus.DELIVERED,
            items=[
                OrderItem(
                    sku="ACC-CAT6-10FT",
                    product_name="CAT6 Ethernet Cable 10ft",
                    quantity=2,
                    unit_price=12.99,
                    total_price=25.98
                )
            ],
            subtotal=25.98,
            tax=2.08,
            shipping=5.99,
            total=34.05,
            shipping_address=customer_address
        ))
    
    def generate_id(self, prefix: str) -> str:
        """Generate a unique ID with prefix"""
        return f"{prefix}-{uuid.uuid4().hex[:8].upper()}"

# Global data store instance
data_store = DataStore()
