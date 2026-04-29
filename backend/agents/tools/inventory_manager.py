"""
Inventory Management Tool
Updates product inventory status through the RTO lifecycle:
dispatched → in_transit_return → pending_inspection → restocked/damaged
"""

import json
from datetime import datetime, timezone
from crewai.tools import BaseTool
from sqlalchemy import select

from backend.database.connection import SyncSessionLocal
from backend.database.models import (
    Product, Order, OrderItem, InventoryStatus, OrderStatus
)


class InventoryManagerTool(BaseTool):
    name: str = "inventory_manager"
    description: str = (
        "Manages inventory status for products involved in RTO orders. "
        "Can update product status to: in_transit_return, pending_inspection, restocked, damaged. "
        "Input should be a JSON string with fields: order_id, action (mark_return_transit|"
        "mark_pending_inspection|restock|mark_damaged), and optional notes."
    )

    def _run(self, inventory_json: str) -> str:
        """Update inventory based on RTO lifecycle events."""
        try:
            data = json.loads(inventory_json) if isinstance(inventory_json, str) else inventory_json

            order_id = data.get("order_id")
            action = data.get("action", "")
            notes = data.get("notes", "")

            if not order_id:
                return json.dumps({
                    "success": False,
                    "error": "order_id is required",
                })

            # Valid actions
            valid_actions = {
                "mark_return_transit": InventoryStatus.IN_TRANSIT_RETURN,
                "mark_pending_inspection": InventoryStatus.PENDING_INSPECTION,
                "restock": InventoryStatus.RESTOCKED,
                "mark_damaged": InventoryStatus.DAMAGED,
            }

            if action not in valid_actions:
                return json.dumps({
                    "success": False,
                    "error": f"Invalid action '{action}'. Valid: {list(valid_actions.keys())}",
                })

            new_status = valid_actions[action]

            session = SyncSessionLocal()
            try:
                # Get order and its items
                order = session.query(Order).filter(Order.id == order_id).first()
                if not order:
                    return json.dumps({
                        "success": False,
                        "error": f"Order {order_id} not found",
                    })

                order_items = session.query(OrderItem).filter(
                    OrderItem.order_id == order_id
                ).all()

                if not order_items:
                    return json.dumps({
                        "success": False,
                        "error": f"No items found for order {order_id}",
                    })

                updated_products = []
                for item in order_items:
                    product = session.query(Product).filter(
                        Product.id == item.product_id
                    ).first()

                    if product:
                        old_status = product.inventory_status
                        product.inventory_status = new_status

                        # If restocking, increment quantity
                        if action == "restock":
                            product.stock_quantity += item.quantity

                        updated_products.append({
                            "product_id": str(product.id),
                            "product_name": product.name,
                            "sku": product.sku,
                            "old_status": old_status.value if old_status else "unknown",
                            "new_status": new_status.value,
                            "quantity_affected": item.quantity,
                            "new_stock_quantity": product.stock_quantity,
                        })

                session.commit()

                return json.dumps({
                    "success": True,
                    "order_id": str(order_id),
                    "order_number": order.order_number,
                    "action": action,
                    "products_updated": updated_products,
                    "total_products_affected": len(updated_products),
                    "notes": notes,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }, indent=2)

            finally:
                session.close()

        except json.JSONDecodeError:
            return json.dumps({
                "success": False,
                "error": "Invalid JSON input",
            })
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": str(e),
            })