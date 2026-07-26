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

    # TODO: implement pending() and summary() per prompt.md
