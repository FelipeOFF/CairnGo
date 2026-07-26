#!/usr/bin/env bats
# bench-corpus.bats — two-direction verify.sh proof (unsolved fails, hand-
# solved passes) for the 5 new corpus tasks added in Phase 5 (bugfix-inventory,
# feature-todo, refactor-report, microedit-greet, longhorizon-notify). Mirrors
# tests/bench-verify.bats's pattern for smoke-convert. Zero agent or API
# involvement — every "solved" fixture below is hand-written.
#
# Assertion style note (same as bench-verify.bats): a failing `[[ ]]` or
# `! cmd` mid-test does NOT fail a bats test on this bash, so checks use
# explicit `[ "$status" -eq/-ne N ]`.

load 'helpers'

BENCH_TASKS_DIR="$CAIRN_REPO_ROOT/benchmarks/tasks"

# ---------------------------------------------------------------------------
# bugfix-inventory
# ---------------------------------------------------------------------------

@test "bugfix-inventory: verify.sh fails against the unsolved fixture" {
  cp -r "$BENCH_TASKS_DIR/bugfix-inventory/fixture" "$BATS_TEST_TMPDIR/unsolved"
  run bash "$BENCH_TASKS_DIR/bugfix-inventory/verify.sh" "$BATS_TEST_TMPDIR/unsolved"
  [ "$status" -ne 0 ]
}

@test "bugfix-inventory: verify.sh passes against a hand-solved fixture" {
  cp -r "$BENCH_TASKS_DIR/bugfix-inventory/fixture" "$BATS_TEST_TMPDIR/solved"
  cat > "$BATS_TEST_TMPDIR/solved/orders.py" <<'EOF'
"""Order fulfillment logic."""

from inventory import Inventory


def fulfill_order(inventory: Inventory, order):
    """order: list of (sku, qty) tuples. Returns True if fully fulfilled.

    Validates every line item before reserving anything, so a failing order
    leaves inventory completely unchanged.
    """
    for sku, qty in order:
        if inventory.available(sku) < qty:
            raise ValueError(f"insufficient stock for {sku}")
    for sku, qty in order:
        inventory.reserve(sku, qty)
    return True
EOF
  run bash "$BENCH_TASKS_DIR/bugfix-inventory/verify.sh" "$BATS_TEST_TMPDIR/solved"
  [ "$status" -eq 0 ]
}

# ---------------------------------------------------------------------------
# feature-todo
# ---------------------------------------------------------------------------

@test "feature-todo: verify.sh fails against the unsolved fixture" {
  cp -r "$BENCH_TASKS_DIR/feature-todo/fixture" "$BATS_TEST_TMPDIR/unsolved"
  run bash "$BENCH_TASKS_DIR/feature-todo/verify.sh" "$BATS_TEST_TMPDIR/unsolved"
  [ "$status" -ne 0 ]
}

@test "feature-todo: verify.sh passes against a hand-solved fixture" {
  cp -r "$BENCH_TASKS_DIR/feature-todo/fixture" "$BATS_TEST_TMPDIR/solved"
  cat > "$BATS_TEST_TMPDIR/solved/todo.py" <<'EOF'
"""A minimal todo list."""


class TodoItem:
    def __init__(self, text, priority=0):
        self.text = text
        self.priority = priority
        self.done = False


class TodoList:
    def __init__(self):
        self.items = []

    def add(self, text, priority=0):
        item = TodoItem(text, priority=priority)
        self.items.append(item)
        return item

    def complete(self, text):
        for item in self.items:
            if item.text == text:
                item.done = True
                return True
        return False

    def pending(self):
        return sorted((item for item in self.items if not item.done),
                      key=lambda item: item.priority, reverse=True)

    def summary(self):
        done = sum(1 for item in self.items if item.done)
        return {"total": len(self.items), "pending": len(self.items) - done,
                "done": done}
EOF
  run bash "$BENCH_TASKS_DIR/feature-todo/verify.sh" "$BATS_TEST_TMPDIR/solved"
  [ "$status" -eq 0 ]
}
