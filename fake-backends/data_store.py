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
        self.business_operations: List[dict] = []
        
        self._initialize_demo_data()

    def reset(self):
        """Reset demo data back to initial state (in-place)."""
        # Clear all collections
        self.customers.clear()
        self.products.clear()
        self.orders.clear()
        self.rmas.clear()
        self.carts.clear()
        self.expected_returns.clear()
        self.shipments.clear()
        self.store_credits.clear()
        self.charges.clear()
        self.email_notifications.clear()
        self.return_labels.clear()
        self.business_operations.clear()

        # Re-initialize baseline demo data
        self._initialize_demo_data()

    def log_operation(self, system: str, operation: str, parameters=None, response=None):
        """Append a business operation entry for display on the homepage."""
        self.business_operations.append({
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "system": system,
            "operation": operation,
            "parameters": parameters,
            "response": response,
        })
    
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
        
        # Sample Products - Current router being returned (EOL / clearance)
        self.products["RTR-HS-BASIC"] = Product(
            sku="RTR-HS-BASIC",
            name="HomeStream Basic Router",
            category=ProductCategory.ROUTERS,
            price=129.99,
            wifi_standard=5,
            tags=["basic", "home", "clearance"],
            description="Entry WiFi router (EOL / clearance)",
            lifecycle_status="clearance",
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
        
        # Gaming router in networking category for broader searches
        self.products["RTR-GAMING-AX5700"] = Product(
            sku="RTR-GAMING-AX5700",
            name="Gaming Pro AX5700 WiFi 6 Router",
            category=ProductCategory.NETWORKING,
            price=199.99,
            wifi_standard=6,
            tags=["gaming", "wifi", "router", "low-latency", "wifi6", "qos"],
            description="Professional gaming router with WiFi 6, advanced QoS, and ultra-low latency for competitive gaming",
            lifecycle_status="active",
            in_stock=True,
            stock_quantity=32
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

        # Vacuums (mirrors router EOL scenario)
        self.products["VAC-EASY-180"] = Product(
            sku="VAC-EASY-180",
            name="EasyVac 180",
            category=ProductCategory.APPLIANCES,
            price=179.99,
            wifi_standard=None,
            tags=["vacuum", "upright", "clearance"],
            description="Lightweight EasyVac 180 (EOL / clearance)",
            lifecycle_status="clearance",
            in_stock=False,
            stock_quantity=0
        )

        self.products["VAC-EASY-PET-PRO"] = Product(
            sku="VAC-EASY-PET-PRO",
            name="EasyVac Pet Pro",
            category=ProductCategory.APPLIANCES,
            price=239.99,
            wifi_standard=None,
            tags=["vacuum", "pet", "pet-friendly", "hair", "carpet", "anti-tangle", "powerful", "suction", "upgrade", "dog", "cat"],
            description="Upgraded pet-focused vacuum with anti-tangle brushroll, powerful suction, and HEPA filter; ideal for pet hair",
            lifecycle_status="active",
            in_stock=True,
            stock_quantity=28
        )
        
        # Sample Order for Salesforce contact - HomeStream Basic Router
        sfdc_customer_address = Address(
            street="456 Tech Avenue",
            city="Seattle",
            state="WA",
            postal_code="98101",
            country="USA"
        )
        
        # First order - older one
        delivery_date_sfdc_1 = datetime.now() - timedelta(days=45)
        order_date_sfdc_1 = delivery_date_sfdc_1 - timedelta(days=2)
        
        self.orders.append(Order(
            order_id="ORD-2025-007891",
            customer_id="0039Q00001VsHMXQA3",
            order_date=order_date_sfdc_1,
            delivery_date=delivery_date_sfdc_1,
            status=OrderStatus.DELIVERED,
            items=[
                OrderItem(
                    sku="RTR-HS-DELUXE",
                    product_name="HomeStream Deluxe Router",
                    quantity=1,
                    unit_price=199.99,
                    total_price=199.99
                ),
                OrderItem(
                    sku="ACC-PWR-CABLE",
                    product_name="Replacement Power Cable",
                    quantity=2,
                    unit_price=15.99,
                    total_price=31.98
                )
            ],
            subtotal=231.97,
            tax=18.56,
            shipping=0.00,
            total=250.53,
            shipping_address=sfdc_customer_address
        ))
        
        # Second order - most recent (HomeStream Basic Router)
        delivery_date_sfdc_2 = datetime.now() - timedelta(days=1)
        order_date_sfdc_2 = delivery_date_sfdc_2 - timedelta(days=2)
        
        self.orders.append(Order(
            order_id="ORD-2025-007892",
            customer_id="0039Q00001VsHMXQA3",
            order_date=order_date_sfdc_2,
            delivery_date=delivery_date_sfdc_2,
            status=OrderStatus.DELIVERED,
            items=[
                OrderItem(
                    sku="RTR-HS-BASIC",
                    product_name="HomeStream Basic Router",
                    quantity=1,
                    unit_price=149.99,
                    total_price=149.99
                ),
                OrderItem(
                    sku="ACC-ETHERNET",
                    product_name="CAT6 Ethernet Cable 10ft",
                    quantity=1,
                    unit_price=12.99,
                    total_price=12.99
                )
            ],
            subtotal=162.98,
            tax=13.04,
            shipping=0.00,
            total=175.02,
            shipping_address=sfdc_customer_address
        ))
        
        # Third order - older than the router order (accessories)
        delivery_date_sfdc_3 = datetime.now() - timedelta(days=12)
        order_date_sfdc_3 = delivery_date_sfdc_3 - timedelta(days=1)
        
        self.orders.append(Order(
            order_id="ORD-2025-007893",
            customer_id="0039Q00001VsHMXQA3",
            order_date=order_date_sfdc_3,
            delivery_date=delivery_date_sfdc_3,
            status=OrderStatus.DELIVERED,
            items=[
                OrderItem(
                    sku="ACC-WIFI-ADAPTER",
                    product_name="USB WiFi Adapter",
                    quantity=1,
                    unit_price=29.99,
                    total_price=29.99
                ),
                OrderItem(
                    sku="ACC-SURGE-PROTECTOR",
                    product_name="Smart Surge Protector",
                    quantity=1,
                    unit_price=34.99,
                    total_price=34.99
                )
            ],
            subtotal=64.98,
            tax=5.20,
            shipping=0.00,
            total=70.18,
            shipping_address=sfdc_customer_address
        ))

        # Fourth order - vacuum (EasyVac 180, now EOL) for pet hair complaint
        delivery_date_sfdc_4 = datetime.now() - timedelta(days=6)
        order_date_sfdc_4 = delivery_date_sfdc_4 - timedelta(days=2)

        self.orders.append(Order(
            order_id="ORD-2025-007894",
            customer_id="0039Q00001VsHMXQA3",
            order_date=order_date_sfdc_4,
            delivery_date=delivery_date_sfdc_4,
            status=OrderStatus.DELIVERED,
            items=[
                OrderItem(
                    sku="VAC-EASY-180",
                    product_name="EasyVac 180",
                    quantity=1,
                    unit_price=179.99,
                    total_price=179.99
                )
            ],
            subtotal=179.99,
            tax=14.40,
            shipping=0.00,
            total=194.39,
            shipping_address=sfdc_customer_address
        ))
        
        # Duplicate orders for second Salesforce contact: 0039Q00001VcSaVQAV
        sfdc_customer_2_address = Address(
            street="789 Innovation Drive",
            city="Portland",
            state="OR",
            postal_code="97201",
            country="USA"
        )
        
        # First order - older one
        delivery_date_sfdc2_1 = datetime.now() - timedelta(days=45)
        order_date_sfdc2_1 = delivery_date_sfdc2_1 - timedelta(days=2)
        
        self.orders.append(Order(
            order_id="ORD-2025-008891",
            customer_id="0039Q00001VcSaVQAV",
            order_date=order_date_sfdc2_1,
            delivery_date=delivery_date_sfdc2_1,
            status=OrderStatus.DELIVERED,
            items=[
                OrderItem(
                    sku="RTR-HS-DELUXE",
                    product_name="HomeStream Deluxe Router",
                    quantity=1,
                    unit_price=199.99,
                    total_price=199.99
                ),
                OrderItem(
                    sku="ACC-PWR-CABLE",
                    product_name="Replacement Power Cable",
                    quantity=2,
                    unit_price=15.99,
                    total_price=31.98
                )
            ],
            subtotal=231.97,
            tax=18.56,
            shipping=0.00,
            total=250.53,
            shipping_address=sfdc_customer_2_address
        ))
        
        # Second order - most recent (HomeStream Basic Router)
        delivery_date_sfdc2_2 = datetime.now() - timedelta(days=1)
        order_date_sfdc2_2 = delivery_date_sfdc2_2 - timedelta(days=2)
        
        self.orders.append(Order(
            order_id="ORD-2025-008892",
            customer_id="0039Q00001VcSaVQAV",
            order_date=order_date_sfdc2_2,
            delivery_date=delivery_date_sfdc2_2,
            status=OrderStatus.DELIVERED,
            items=[
                OrderItem(
                    sku="RTR-HS-BASIC",
                    product_name="HomeStream Basic Router",
                    quantity=1,
                    unit_price=149.99,
                    total_price=149.99
                ),
                OrderItem(
                    sku="ACC-ETHERNET",
                    product_name="CAT6 Ethernet Cable 10ft",
                    quantity=1,
                    unit_price=12.99,
                    total_price=12.99
                )
            ],
            subtotal=162.98,
            tax=13.04,
            shipping=0.00,
            total=175.02,
            shipping_address=sfdc_customer_2_address
        ))
        
        # Third order - older than the router order (accessories)
        delivery_date_sfdc2_3 = datetime.now() - timedelta(days=12)
        order_date_sfdc2_3 = delivery_date_sfdc2_3 - timedelta(days=1)
        
        self.orders.append(Order(
            order_id="ORD-2025-008893",
            customer_id="0039Q00001VcSaVQAV",
            order_date=order_date_sfdc2_3,
            delivery_date=delivery_date_sfdc2_3,
            status=OrderStatus.DELIVERED,
            items=[
                OrderItem(
                    sku="ACC-WIFI-ADAPTER",
                    product_name="USB WiFi Adapter",
                    quantity=1,
                    unit_price=29.99,
                    total_price=29.99
                ),
                OrderItem(
                    sku="ACC-SURGE-PROTECTOR",
                    product_name="Smart Surge Protector",
                    quantity=1,
                    unit_price=34.99,
                    total_price=34.99
                )
            ],
            subtotal=64.98,
            tax=5.20,
            shipping=0.00,
            total=70.18,
            shipping_address=sfdc_customer_2_address
        ))

        # Fourth order for second contact - EasyVac 180 (EOL) struggling with pet hair
        delivery_date_sfdc2_4 = datetime.now() - timedelta(days=5)
        order_date_sfdc2_4 = delivery_date_sfdc2_4 - timedelta(days=2)

        self.orders.append(Order(
            order_id="ORD-2025-008894",
            customer_id="0039Q00001VcSaVQAV",
            order_date=order_date_sfdc2_4,
            delivery_date=delivery_date_sfdc2_4,
            status=OrderStatus.DELIVERED,
            items=[
                OrderItem(
                    sku="VAC-EASY-180",
                    product_name="EasyVac 180",
                    quantity=1,
                    unit_price=179.99,
                    total_price=179.99
                )
            ],
            subtotal=179.99,
            tax=14.40,
            shipping=0.00,
            total=194.39,
            shipping_address=sfdc_customer_2_address
        ))

        # Duplicate orders for third Salesforce contact: 0039Q00001WsSE6QAN
        sfdc_customer_3_address = Address(
            street="135 Harbor Blvd",
            city="Los Angeles",
            state="CA",
            postal_code="90001",
            country="USA"
        )

        # First order - older one (Deluxe Router + accessories)
        delivery_date_sfdc3_1 = datetime.now() - timedelta(days=46)
        order_date_sfdc3_1 = delivery_date_sfdc3_1 - timedelta(days=2)

        self.orders.append(Order(
            order_id="ORD-2025-009891",
            customer_id="0039Q00001WsSE6QAN",
            order_date=order_date_sfdc3_1,
            delivery_date=delivery_date_sfdc3_1,
            status=OrderStatus.DELIVERED,
            items=[
                OrderItem(
                    sku="RTR-HS-DELUXE",
                    product_name="HomeStream Deluxe Router",
                    quantity=1,
                    unit_price=199.99,
                    total_price=199.99
                ),
                OrderItem(
                    sku="ACC-PWR-CABLE",
                    product_name="Replacement Power Cable",
                    quantity=2,
                    unit_price=15.99,
                    total_price=31.98
                )
            ],
            subtotal=231.97,
            tax=18.56,
            shipping=0.00,
            total=250.53,
            shipping_address=sfdc_customer_3_address
        ))

        # Second order - most recent (HomeStream Basic Router)
        delivery_date_sfdc3_2 = datetime.now() - timedelta(days=2)
        order_date_sfdc3_2 = delivery_date_sfdc3_2 - timedelta(days=2)

        self.orders.append(Order(
            order_id="ORD-2025-009892",
            customer_id="0039Q00001WsSE6QAN",
            order_date=order_date_sfdc3_2,
            delivery_date=delivery_date_sfdc3_2,
            status=OrderStatus.DELIVERED,
            items=[
                OrderItem(
                    sku="RTR-HS-BASIC",
                    product_name="HomeStream Basic Router",
                    quantity=1,
                    unit_price=149.99,
                    total_price=149.99
                ),
                OrderItem(
                    sku="ACC-ETHERNET",
                    product_name="CAT6 Ethernet Cable 10ft",
                    quantity=1,
                    unit_price=12.99,
                    total_price=12.99
                )
            ],
            subtotal=162.98,
            tax=13.04,
            shipping=0.00,
            total=175.02,
            shipping_address=sfdc_customer_3_address
        ))

        # Third order - accessories
        delivery_date_sfdc3_3 = datetime.now() - timedelta(days=13)
        order_date_sfdc3_3 = delivery_date_sfdc3_3 - timedelta(days=1)

        self.orders.append(Order(
            order_id="ORD-2025-009893",
            customer_id="0039Q00001WsSE6QAN",
            order_date=order_date_sfdc3_3,
            delivery_date=delivery_date_sfdc3_3,
            status=OrderStatus.DELIVERED,
            items=[
                OrderItem(
                    sku="ACC-WIFI-ADAPTER",
                    product_name="USB WiFi Adapter",
                    quantity=1,
                    unit_price=29.99,
                    total_price=29.99
                ),
                OrderItem(
                    sku="ACC-SURGE-PROTECTOR",
                    product_name="Smart Surge Protector",
                    quantity=1,
                    unit_price=34.99,
                    total_price=34.99
                )
            ],
            subtotal=64.98,
            tax=5.20,
            shipping=0.00,
            total=70.18,
            shipping_address=sfdc_customer_3_address
        ))

        # Fourth order - vacuum (EasyVac 180 EOL)
        delivery_date_sfdc3_4 = datetime.now() - timedelta(days=7)
        order_date_sfdc3_4 = delivery_date_sfdc3_4 - timedelta(days=2)

        self.orders.append(Order(
            order_id="ORD-2025-009894",
            customer_id="0039Q00001WsSE6QAN",
            order_date=order_date_sfdc3_4,
            delivery_date=delivery_date_sfdc3_4,
            status=OrderStatus.DELIVERED,
            items=[
                OrderItem(
                    sku="VAC-EASY-180",
                    product_name="EasyVac 180",
                    quantity=1,
                    unit_price=179.99,
                    total_price=179.99
                )
            ],
            subtotal=179.99,
            tax=14.40,
            shipping=0.00,
            total=194.39,
            shipping_address=sfdc_customer_3_address
        ))
    
    def generate_id(self, prefix: str) -> str:
        """Generate a unique ID with prefix"""
        return f"{prefix}-{uuid.uuid4().hex[:8].upper()}"

# Global data store instance
data_store = DataStore()
