"""
Seed data generator for demonstration and testing.
Creates realistic Indian e-commerce order data with various risk profiles.
"""

import uuid
import random
from datetime import datetime, timezone, timedelta

from sqlalchemy.orm import Session

from backend.database.connection import sync_engine, Base
from backend.database.models import (
    Customer, CustomerAddress, Product, Order, OrderItem,
    OrderStatus, PaymentMethod, RiskLevel, InventoryStatus
)


def generate_order_number() -> str:
    return f"ORD-{random.randint(100000, 999999)}"


# Indian city/pincode data for realistic addresses
CITY_PINCODE_MAP = {
    "Mumbai": ["400001", "400050", "400070", "400093"],
    "Delhi": ["110001", "110016", "110085", "110092"],
    "Bangalore": ["560001", "560034", "560068", "560100"],
    "Chennai": ["600001", "600017", "600042", "600096"],
    "Hyderabad": ["500001", "500034", "500072", "500081"],
    "Pune": ["411001", "411014", "411038", "411057"],
    "Kolkata": ["700001", "700019", "700054", "700091"],
    "Jaipur": ["302001", "302015", "302020", "302033"],
}

STATE_MAP = {
    "Mumbai": "Maharashtra",
    "Delhi": "Delhi",
    "Bangalore": "Karnataka",
    "Chennai": "Tamil Nadu",
    "Hyderabad": "Telangana",
    "Pune": "Maharashtra",
    "Kolkata": "West Bengal",
    "Jaipur": "Rajasthan",
}

VAGUE_ADDRESSES = [
    "Near the big tree, behind the temple",
    "Opposite the old building, ground floor",
    "Ask anyone for Sharma ji's house",
    "Near the neem tree, yellow gate",
    "3rd house from the paan shop",
    "Behind the water tank, village road",
    "Near railway crossing, red building",
]

NORMAL_ADDRESSES = [
    "Flat 302, Sai Krupa Apartments, MG Road",
    "12/A, Sector 15, DLF Colony",
    "House No. 456, 2nd Cross, JP Nagar",
    "B-104, Sunrise Towers, Ring Road",
    "Plot 78, Phase 2, Electronic City",
    "Flat 201, Green Valley Apartments, Baner Road",
    "15, Park Street, Block C",
    "A-23, Malviya Nagar, Opposite Metro Station",
]

PRODUCTS = [
    {"name": "Wireless Bluetooth Earbuds Pro", "sku": "ELEC-001", "price": 2499.0, "category": "Electronics", "weight": 120},
    {"name": "Cotton Kurta Set - Blue", "sku": "FASH-001", "price": 1299.0, "category": "Fashion", "weight": 350},
    {"name": "Stainless Steel Water Bottle 1L", "sku": "HOME-001", "price": 599.0, "category": "Home", "weight": 400},
    {"name": "Face Wash - Neem & Tulsi 200ml", "sku": "BEAU-001", "price": 349.0, "category": "Beauty", "weight": 250},
    {"name": "Programming Book - DSA Essentials", "sku": "BOOK-001", "price": 450.0, "category": "Books", "weight": 500},
    {"name": "Smartphone Back Cover - Premium", "sku": "ELEC-002", "price": 299.0, "category": "Electronics", "weight": 50},
    {"name": "Yoga Mat - Anti Slip 6mm", "sku": "FIT-001", "price": 899.0, "category": "Fitness", "weight": 1200},
    {"name": "LED Desk Lamp - Adjustable", "sku": "HOME-002", "price": 1199.0, "category": "Home", "weight": 800},
    {"name": "Men's Running Shoes - Black", "sku": "FASH-002", "price": 2999.0, "category": "Fashion", "weight": 700},
    {"name": "Organic Green Tea - 100 bags", "sku": "FOOD-001", "price": 399.0, "category": "Food", "weight": 200},
]


def create_seed_data(session: Session):
    """Generate comprehensive seed data."""
    print("🌱 Seeding database...")

    # Create products
    products = []
    for p_data in PRODUCTS:
        product = Product(
            name=p_data["name"],
            sku=p_data["sku"],
            price=p_data["price"],
            category=p_data["category"],
            weight_grams=p_data["weight"],
            inventory_status=InventoryStatus.IN_STOCK,
            stock_quantity=random.randint(50, 500),
        )
        products.append(product)
        session.add(product)

    session.flush()

    # Create customers with various risk profiles
    customers_data = [
        # Low risk customers (good history)
        {
            "name": "Priya Sharma", "phone": "+919876543210", "email": "priya.sharma@gmail.com",
            "total_orders": 25, "successful_deliveries": 24, "rto_count": 1,
            "failed_payment_attempts": 0, "account_age_days": 730, "is_verified": True,
            "address_type": "normal", "city": "Mumbai"
        },
        {
            "name": "Rajesh Kumar", "phone": "+919876543211", "email": "rajesh.k@outlook.com",
            "total_orders": 42, "successful_deliveries": 40, "rto_count": 2,
            "failed_payment_attempts": 1, "account_age_days": 1095, "is_verified": True,
            "address_type": "normal", "city": "Delhi"
        },
        {
            "name": "Ananya Iyer", "phone": "+919876543212", "email": "ananya.i@yahoo.com",
            "total_orders": 15, "successful_deliveries": 15, "rto_count": 0,
            "failed_payment_attempts": 0, "account_age_days": 365, "is_verified": True,
            "address_type": "normal", "city": "Chennai"
        },
        # Medium risk customers
        {
            "name": "Vikram Patel", "phone": "+919876543213", "email": "vikram.p@gmail.com",
            "total_orders": 8, "successful_deliveries": 5, "rto_count": 3,
            "failed_payment_attempts": 2, "account_age_days": 90, "is_verified": True,
            "address_type": "normal", "city": "Bangalore"
        },
        {
            "name": "Meera Desai", "phone": "+919876543214", "email": None,
            "total_orders": 3, "successful_deliveries": 2, "rto_count": 1,
            "failed_payment_attempts": 3, "account_age_days": 30, "is_verified": False,
            "address_type": "normal", "city": "Pune"
        },
        # High risk customers
        {
            "name": "Suresh Singh", "phone": "+919876543215", "email": None,
            "total_orders": 6, "successful_deliveries": 1, "rto_count": 5,
            "failed_payment_attempts": 4, "account_age_days": 14, "is_verified": False,
            "address_type": "vague", "city": "Jaipur"
        },
        {
            "name": "New User 7891", "phone": "+919876543216", "email": None,
            "total_orders": 0, "successful_deliveries": 0, "rto_count": 0,
            "failed_payment_attempts": 2, "account_age_days": 1, "is_verified": False,
            "address_type": "vague", "city": "Kolkata"
        },
        {
            "name": "Rohit Gupta", "phone": "+919876543217", "email": "temp_email@tempmail.com",
            "total_orders": 4, "successful_deliveries": 0, "rto_count": 4,
            "failed_payment_attempts": 5, "account_age_days": 7, "is_verified": False,
            "address_type": "vague", "city": "Hyderabad"
        },
        # Edge cases
        {
            "name": "Deepa Menon", "phone": "+919876543218", "email": "deepa.m@corporate.co.in",
            "total_orders": 100, "successful_deliveries": 98, "rto_count": 2,
            "failed_payment_attempts": 0, "account_age_days": 2000, "is_verified": True,
            "address_type": "normal", "city": "Bangalore"
        },
        {
            "name": "Arjun Reddy", "phone": "+919876543219", "email": "arjun.r@gmail.com",
            "total_orders": 12, "successful_deliveries": 8, "rto_count": 4,
            "failed_payment_attempts": 1, "account_age_days": 180, "is_verified": True,
            "address_type": "normal", "city": "Hyderabad"
        },
    ]

    customers = []
    addresses = []

    for c_data in customers_data:
        customer = Customer(
            name=c_data["name"],
            phone=c_data["phone"],
            email=c_data["email"],
            total_orders=c_data["total_orders"],
            successful_deliveries=c_data["successful_deliveries"],
            rto_count=c_data["rto_count"],
            failed_payment_attempts=c_data["failed_payment_attempts"],
            account_age_days=c_data["account_age_days"],
            is_verified=c_data["is_verified"],
        )
        session.add(customer)
        session.flush()

        # Create address
        city = c_data["city"]
        if c_data["address_type"] == "vague":
            addr_line = random.choice(VAGUE_ADDRESSES)
            # Sometimes use mismatched pincode for high-risk
            pincode = random.choice(
                CITY_PINCODE_MAP.get(random.choice(list(CITY_PINCODE_MAP.keys())), ["000000"])
            )
        else:
            addr_line = random.choice(NORMAL_ADDRESSES)
            pincode = random.choice(CITY_PINCODE_MAP.get(city, ["000000"]))

        address = CustomerAddress(
            customer_id=customer.id,
            address_line_1=addr_line,
            city=city,
            state=STATE_MAP.get(city, "Unknown"),
            pincode=pincode,
            is_default=True,
        )
        session.add(address)
        session.flush()

        customers.append(customer)
        addresses.append(address)

    # Create orders in various states
    for i, (customer, address) in enumerate(zip(customers, addresses)):
        num_orders = random.randint(1, 3)
        for _ in range(num_orders):
            # Select random products
            order_products = random.sample(products, random.randint(1, 3))
            total = sum(p.price for p in order_products)

            # Determine order status based on customer risk
            if customer.rto_count > 3:
                status = random.choice([
                    OrderStatus.PENDING,
                    OrderStatus.RTO_INITIATED,
                    OrderStatus.RTO_RECEIVED,
                ])
            elif customer.rto_count > 1:
                status = random.choice([
                    OrderStatus.PENDING,
                    OrderStatus.DISPATCHED,
                    OrderStatus.RTO_INITIATED,
                ])
            else:
                status = random.choice([
                    OrderStatus.PENDING,
                    OrderStatus.APPROVED,
                    OrderStatus.DISPATCHED,
                    OrderStatus.DELIVERED,
                ])

            order = Order(
                order_number=generate_order_number(),
                customer_id=customer.id,
                shipping_address_id=address.id,
                total_amount=total,
                payment_method=PaymentMethod.COD,
                status=status,
                created_at=datetime.now(timezone.utc) - timedelta(days=random.randint(0, 30)),
                forward_shipping_cost=random.uniform(40, 120),
                reverse_shipping_cost=random.uniform(40, 120) if "rto" in status.value else 0,
            )

            if "rto" in status.value:
                order.rto_initiated_at = datetime.now(timezone.utc) - timedelta(days=random.randint(1, 5))
                order.total_rto_cost = order.forward_shipping_cost + order.reverse_shipping_cost

            session.add(order)
            session.flush()

            # Add order items
            for product in order_products:
                qty = random.randint(1, 2)
                item = OrderItem(
                    order_id=order.id,
                    product_id=product.id,
                    quantity=qty,
                    unit_price=product.price,
                    total_price=product.price * qty,
                )
                session.add(item)

    session.commit()
    print("✅ Seed data created successfully!")
    print(f"   📦 Products: {len(products)}")
    print(f"   👤 Customers: {len(customers)}")
    print(f"   📍 Addresses: {len(addresses)}")
    print(f"   🛒 Orders: created across all customers")


def run_seed():
    """Entry point for seeding."""
    Base.metadata.create_all(bind=sync_engine)
    session = next(iter([session := Session(sync_engine)]))
    try:
        # Check if data already exists
        existing = session.query(Customer).count()
        if existing > 0:
            print("⚠️  Data already exists. Skipping seed.")
            return
        create_seed_data(session)
    finally:
        session.close()


if __name__ == "__main__":
    from backend.database.connection import SyncSessionLocal
    session = SyncSessionLocal()
    try:
        create_seed_data(session)
    finally:
        session.close()