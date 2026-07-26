"""Order fulfillment logic."""

from inventory import Inventory


def fulfill_order(inventory: Inventory, order):
    """order: list of (sku, qty) tuples. Returns True if fully fulfilled.

    Raises ValueError if any line item cannot be reserved. BUG: never
    actually reserves stock, so inventory is never decremented.
    """
    for sku, qty in order:
        if inventory.available(sku) < qty:
            raise ValueError(f"insufficient stock for {sku}")
    return True
