"""Inventory stock tracking."""


class Inventory:
    def __init__(self, stock):
        self.stock = dict(stock)

    def available(self, sku):
        return self.stock.get(sku, 0)

    def reserve(self, sku, qty):
        """Deduct qty from stock. Raises ValueError if insufficient stock."""
        current = self.available(sku)
        if qty > current:
            raise ValueError(f"insufficient stock for {sku}")
        self.stock[sku] = current - qty
