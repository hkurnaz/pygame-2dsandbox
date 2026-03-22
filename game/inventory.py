"""Inventory system for the player."""

import pygame
from game.constants import (
    INVENTORY_SLOTS, INVENTORY_COLS, INVENTORY_ROWS,
    INVENTORY_SLOT_SIZE, INVENTORY_PADDING,
    SCREEN_WIDTH, SCREEN_HEIGHT, YELLOW, WHITE, BLACK
)
from game.blocks import get_block_color, get_block_name, BlockType


class Inventory:
    """Player inventory that stores collected items."""

    def __init__(self):
        # Hotbar (9 slots)
        self.hotbar = [None] * INVENTORY_SLOTS
        # Full inventory (3 rows x 9 cols = 27 slots)
        self.storage = [[None for _ in range(INVENTORY_COLS)] for _ in range(INVENTORY_ROWS)]
        self.selected_slot = 0
        self.hovered_slot = -1
        self.is_open = False  # Big inventory open state

        # Drag and drop
        self.dragging = False
        self.drag_item = None  # (block_type, count)
        self.drag_source = None  # ('hotbar', index) or ('storage', row, col)

    def add_item(self, block_type, count=1):
        """Add an item to the inventory. Returns True if successful."""
        # First, try to stack with existing items in hotbar
        for i, slot in enumerate(self.hotbar):
            if slot is not None and slot[0] == block_type:
                self.hotbar[i] = (block_type, slot[1] + count)
                return True

        # Try to stack in storage
        for row in range(INVENTORY_ROWS):
            for col in range(INVENTORY_COLS):
                slot = self.storage[row][col]
                if slot is not None and slot[0] == block_type:
                    self.storage[row][col] = (block_type, slot[1] + count)
                    return True

        # Otherwise, find an empty slot in hotbar
        for i, slot in enumerate(self.hotbar):
            if slot is None:
                self.hotbar[i] = (block_type, count)
                return True

        # Then try storage
        for row in range(INVENTORY_ROWS):
            for col in range(INVENTORY_COLS):
                if self.storage[row][col] is None:
                    self.storage[row][col] = (block_type, count)
                    return True

        return False  # Inventory full

    def remove_item(self, slot_index, count=1):
        """Remove items from hotbar slot. Returns (block_type, count) or None."""
        if 0 <= slot_index < INVENTORY_SLOTS and self.hotbar[slot_index] is not None:
            block_type, current_count = self.hotbar[slot_index]
            if current_count <= count:
                self.hotbar[slot_index] = None
                return (block_type, current_count)
            else:
                self.hotbar[slot_index] = (block_type, current_count - count)
                return (block_type, count)
        return None

    def get_selected_item(self):
        """Get the item in the selected hotbar slot."""
        return self.hotbar[self.selected_slot]

    def select_slot(self, index):
        """Select a hotbar slot by index."""
        if 0 <= index < INVENTORY_SLOTS:
            self.selected_slot = index

    def scroll_selection(self, direction):
        """Scroll through hotbar slots. direction: 1 = right, -1 = left."""
        self.selected_slot = (self.selected_slot + direction) % INVENTORY_SLOTS

    def get_hotbar_slot_rect(self, index):
        """Get the screen rect for a hotbar slot (top left)."""
        start_x = 10
        start_y = 10
        x = start_x + index * (INVENTORY_SLOT_SIZE + INVENTORY_PADDING)
        return pygame.Rect(x, start_y, INVENTORY_SLOT_SIZE, INVENTORY_SLOT_SIZE)

    def get_storage_slot_rect(self, row, col):
        """Get the screen rect for a storage slot (centered when inventory open)."""
        # Calculate total inventory dimensions
        total_width = INVENTORY_COLS * (INVENTORY_SLOT_SIZE + INVENTORY_PADDING) - INVENTORY_PADDING
        total_height = INVENTORY_ROWS * (INVENTORY_SLOT_SIZE + INVENTORY_PADDING) - INVENTORY_PADDING

        # Center on screen
        start_x = (SCREEN_WIDTH - total_width) // 2
        start_y = (SCREEN_HEIGHT - total_height) // 2

        x = start_x + col * (INVENTORY_SLOT_SIZE + INVENTORY_PADDING)
        y = start_y + row * (INVENTORY_SLOT_SIZE + INVENTORY_PADDING)
        return pygame.Rect(x, y, INVENTORY_SLOT_SIZE, INVENTORY_SLOT_SIZE)

    def get_inventory_background_rect(self):
        """Get the background rect for the big inventory."""
        total_width = INVENTORY_COLS * (INVENTORY_SLOT_SIZE + INVENTORY_PADDING) - INVENTORY_PADDING
        total_height = INVENTORY_ROWS * (INVENTORY_SLOT_SIZE + INVENTORY_PADDING) - INVENTORY_PADDING
        start_x = (SCREEN_WIDTH - total_width) // 2
        start_y = (SCREEN_HEIGHT - total_height) // 2
        return pygame.Rect(start_x - 10, start_y - 10, total_width + 20, total_height + 20)

    def check_hotbar_hover(self, mouse_x, mouse_y):
        """Check which hotbar slot is being hovered. Returns slot index or -1."""
        for i in range(INVENTORY_SLOTS):
            if self.get_hotbar_slot_rect(i).collidepoint(mouse_x, mouse_y):
                return i
        return -1

    def check_storage_hover(self, mouse_x, mouse_y):
        """Check which storage slot is being hovered. Returns (row, col) or None."""
        for row in range(INVENTORY_ROWS):
            for col in range(INVENTORY_COLS):
                if self.get_storage_slot_rect(row, col).collidepoint(mouse_x, mouse_y):
                    return (row, col)
        return None

    def start_drag(self, source_type, *args):
        """Start dragging an item. source_type: 'hotbar' or 'storage'."""
        if source_type == 'hotbar':
            index = args[0]
            if self.hotbar[index] is not None:
                self.drag_item = self.hotbar[index]
                self.drag_source = ('hotbar', index)
                self.hotbar[index] = None
                self.dragging = True
        elif source_type == 'storage':
            row, col = args[0], args[1]
            if self.storage[row][col] is not None:
                self.drag_item = self.storage[row][col]
                self.drag_source = ('storage', row, col)
                self.storage[row][col] = None
                self.dragging = True

    def end_drag(self, target_type, *args):
        """End dragging and place item. Returns True if successful."""
        if not self.dragging or self.drag_item is None:
            return False

        block_type, count = self.drag_item

        if target_type == 'hotbar':
            index = args[0]
            if self.hotbar[index] is None:
                self.hotbar[index] = self.drag_item
            elif self.hotbar[index][0] == block_type:
                # Stack items
                self.hotbar[index] = (block_type, self.hotbar[index][1] + count)
            else:
                # Swap items
                old_item = self.hotbar[index]
                self.hotbar[index] = self.drag_item
                if self.drag_source[0] == 'hotbar':
                    self.hotbar[self.drag_source[1]] = old_item
                elif self.drag_source[0] == 'storage':
                    self.storage[self.drag_source[1]][self.drag_source[2]] = old_item

        elif target_type == 'storage':
            row, col = args[0], args[1]
            if self.storage[row][col] is None:
                self.storage[row][col] = self.drag_item
            elif self.storage[row][col][0] == block_type:
                # Stack items
                self.storage[row][col] = (block_type, self.storage[row][col][1] + count)
            else:
                # Swap items
                old_item = self.storage[row][col]
                self.storage[row][col] = self.drag_item
                if self.drag_source[0] == 'hotbar':
                    self.hotbar[self.drag_source[1]] = old_item
                elif self.drag_source[0] == 'storage':
                    self.storage[self.drag_source[1]][self.drag_source[2]] = old_item

        self.dragging = False
        self.drag_item = None
        self.drag_source = None
        return True

    def cancel_drag(self):
        """Cancel dragging and return item to source."""
        if self.dragging and self.drag_item is not None and self.drag_source is not None:
            if self.drag_source[0] == 'hotbar':
                self.hotbar[self.drag_source[1]] = self.drag_item
            elif self.drag_source[0] == 'storage':
                self.storage[self.drag_source[1]][self.drag_source[2]] = self.drag_item
        self.dragging = False
        self.drag_item = None
        self.drag_source = None

    def handle_click(self, mouse_x, mouse_y, button=1):
        """Handle mouse click. Returns clicked slot info or None."""
        # Check hotbar
        hotbar_slot = self.check_hotbar_hover(mouse_x, mouse_y)
        if hotbar_slot >= 0:
            if button == 1:  # Left click
                if self.dragging:
                    self.end_drag('hotbar', hotbar_slot)
                else:
                    self.start_drag('hotbar', hotbar_slot)
            return ('hotbar', hotbar_slot)

        # Check storage if inventory is open
        if self.is_open:
            storage_slot = self.check_storage_hover(mouse_x, mouse_y)
            if storage_slot:
                row, col = storage_slot
                if button == 1:  # Left click
                    if self.dragging:
                        self.end_drag('storage', row, col)
                    else:
                        self.start_drag('storage', row, col)
                return ('storage', row, col)

        return None

    def draw_hotbar(self, surface):
        """Draw the hotbar at top left."""
        font = pygame.font.SysFont(None, 18)

        for i in range(INVENTORY_SLOTS):
            rect = self.get_hotbar_slot_rect(i)

            # Draw slot background
            bg_color = (50, 50, 50) if i == self.selected_slot else (70, 70, 70)
            pygame.draw.rect(surface, bg_color, rect)

            # Draw border (white if selected, gray otherwise)
            if i == self.selected_slot:
                border_color = WHITE
            else:
                border_color = (100, 100, 100)
            pygame.draw.rect(surface, border_color, rect, 2)

            # Draw item if present
            slot_data = self.hotbar[i]
            if slot_data is not None:
                block_type, count = slot_data
                color = get_block_color(block_type)

                # Draw item (smaller than slot)
                item_margin = 4
                item_rect = pygame.Rect(
                    rect.x + item_margin,
                    rect.y + item_margin,
                    rect.width - item_margin * 2,
                    rect.height - item_margin * 2
                )
                pygame.draw.rect(surface, color, item_rect)
                pygame.draw.rect(surface, BLACK, item_rect, 1)

                # Draw count
                count_text = font.render(str(count), True, WHITE)
                surface.blit(count_text, (rect.right - count_text.get_width() - 2,
                                          rect.bottom - count_text.get_height() - 2))

            # Draw slot number
            num_text = font.render(str(i + 1), True, (150, 150, 150))
            surface.blit(num_text, (rect.x + 2, rect.y + 2))

    def draw_storage(self, surface):
        """Draw the big inventory storage."""
        font = pygame.font.SysFont(None, 18)

        # Draw background
        bg_rect = self.get_inventory_background_rect()
        pygame.draw.rect(surface, (40, 40, 40), bg_rect)
        pygame.draw.rect(surface, WHITE, bg_rect, 2)

        # Draw title
        title_font = pygame.font.SysFont(None, 24)
        title = title_font.render("Inventory (Tab to close)", True, WHITE)
        surface.blit(title, (bg_rect.x + 10, bg_rect.y + 5))

        # Draw storage slots
        for row in range(INVENTORY_ROWS):
            for col in range(INVENTORY_COLS):
                rect = self.get_storage_slot_rect(row, col)

                # Draw slot background
                pygame.draw.rect(surface, (70, 70, 70), rect)
                pygame.draw.rect(surface, (100, 100, 100), rect, 1)

                # Draw item if present
                slot_data = self.storage[row][col]
                if slot_data is not None:
                    block_type, count = slot_data
                    color = get_block_color(block_type)

                    item_margin = 4
                    item_rect = pygame.Rect(
                        rect.x + item_margin,
                        rect.y + item_margin,
                        rect.width - item_margin * 2,
                        rect.height - item_margin * 2
                    )
                    pygame.draw.rect(surface, color, item_rect)
                    pygame.draw.rect(surface, BLACK, item_rect, 1)

                    # Draw count
                    count_text = font.render(str(count), True, WHITE)
                    surface.blit(count_text, (rect.right - count_text.get_width() - 2,
                                              rect.bottom - count_text.get_height() - 2))

    def draw_drag_item(self, surface, mouse_x, mouse_y):
        """Draw the item being dragged at mouse position."""
        if self.dragging and self.drag_item is not None:
            block_type, count = self.drag_item
            color = get_block_color(block_type)

            # Draw item following mouse
            item_rect = pygame.Rect(
                mouse_x - INVENTORY_SLOT_SIZE // 2,
                mouse_y - INVENTORY_SLOT_SIZE // 2,
                INVENTORY_SLOT_SIZE,
                INVENTORY_SLOT_SIZE
            )
            pygame.draw.rect(surface, color, item_rect)
            pygame.draw.rect(surface, YELLOW, item_rect, 2)

            # Draw count
            font = pygame.font.SysFont(None, 18)
            count_text = font.render(str(count), True, WHITE)
            surface.blit(count_text, (item_rect.right - count_text.get_width() - 2,
                                      item_rect.bottom - count_text.get_height() - 2))

    def draw(self, surface):
        """Draw the inventory (hotbar always, storage if open)."""
        self.draw_hotbar(surface)
        if self.is_open:
            self.draw_storage(surface)

    def draw_tooltip(self, surface, mouse_x, mouse_y):
        """Draw tooltip for hovered item."""
        item_data = None

        # Check hotbar hover
        hotbar_slot = self.check_hotbar_hover(mouse_x, mouse_y)
        if hotbar_slot >= 0 and self.hotbar[hotbar_slot] is not None:
            item_data = self.hotbar[hotbar_slot]

        # Check storage hover if open
        if self.is_open and item_data is None:
            storage_slot = self.check_storage_hover(mouse_x, mouse_y)
            if storage_slot and self.storage[storage_slot[0]][storage_slot[1]] is not None:
                item_data = self.storage[storage_slot[0]][storage_slot[1]]

        if item_data is not None:
            block_type, count = item_data
            name = get_block_name(block_type)

            font = pygame.font.SysFont(None, 24)
            text = font.render(f"{name} x{count}", True, WHITE)

            # Position tooltip near mouse
            tooltip_rect = pygame.Rect(
                mouse_x + 15,
                mouse_y + 15,
                text.get_width() + 10,
                text.get_height() + 6
            )

            # Draw tooltip background
            pygame.draw.rect(surface, (30, 30, 30), tooltip_rect)
            pygame.draw.rect(surface, YELLOW, tooltip_rect, 1)

            # Draw text
            surface.blit(text, (tooltip_rect.x + 5, tooltip_rect.y + 3))
