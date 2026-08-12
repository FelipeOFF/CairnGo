"""Sales report totals — each function repeats the same filter-and-sum loop."""


def total_sales(records):
    total = 0
    for r in records:
        if r["kind"] == "sale":
            total += r["amount"]
    return total


def total_refunds(records):
    total = 0
    for r in records:
        if r["kind"] == "refund":
            total += r["amount"]
    return total


def total_tax(records):
    total = 0
    for r in records:
        if r["kind"] == "tax":
            total += r["amount"]
    return total
