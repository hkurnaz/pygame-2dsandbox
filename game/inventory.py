"""Inventory system for the player."""

import pygame
from game.constants import (
    INVENTORY_SLOTS, INVENTORY_COLS, INVENTORY_ROWS,
    INVENTORY_SLOT_SIZE, INVENTORY_PADDING,
    SCREEN_WIDTH, SCREEN_HEIGHT, YELLOW, WHITE, BLACK
)
from game.blocks import (
    get_item_color, get_item_name, BlockType, is_tool, ToolType,
    CRAFTING_RECIPES, get_craftable_items, ItemType
)


def draw_tool(surface, tool_type, rect):
    """Draw a tool with its specific shape inside the given rect."""
    # Get colors
    blade_color = (200, 200, 210)  # Silver/metal color for blades
    handle_color = (139, 90, 43)   # Brown for handles
    head_color = (120, 120, 130)   # Darker metal for tool heads
    
    cx = rect.centerx
    cy = rect.centery
    w = rect.width
    h = rect.height
    
    if tool_type == ToolType.SWORD:
        # Draw sword - blade pointing up
        blade_width = w // 5
        blade_height = int(h * 0.65)
        handle_width = w // 4
        handle_height = h // 4
        
        # Blade (pointed at top)
        blade_points = [
            (cx, rect.top + 2),  # Point
            (cx - blade_width // 2, rect.top + blade_height // 2),
            (cx - blade_width // 2, rect.top + blade_height),
            (cx + blade_width // 2, rect.top + blade_height),
            (cx + blade_width // 2, rect.top + blade_height // 2),
        ]
        pygame.draw.polygon(surface, blade_color, blade_points)
        pygame.draw.polygon(surface, (150, 150, 160), blade_points, 1)
        
        # Guard (cross piece)
        guard_rect = pygame.Rect(cx - w // 3, rect.top + blade_height, w * 2 // 3, h // 10)
        pygame.draw.rect(surface, (180, 150, 50), guard_rect)  # Gold guard
        pygame.draw.rect(surface, (150, 120, 30), guard_rect, 1)
        
        # Handle
        handle_rect = pygame.Rect(cx - handle_width // 2, rect.top + blade_height + h // 10, 
                                  handle_width, handle_height)
        pygame.draw.rect(surface, handle_color, handle_rect)
        pygame.draw.rect(surface, (100, 60, 30), handle_rect, 1)
        
        # Pommel
        pommel_rect = pygame.Rect(cx - handle_width // 2 - 1, rect.top + blade_height + h // 10 + handle_height,
                                  handle_width + 2, h // 12)
        pygame.draw.rect(surface, (180, 150, 50), pommel_rect)
    
    elif tool_type == ToolType.PICKAXE:
        # Draw pickaxe - diagonal head with handle
        handle_width = w // 5
        handle_height = int(h * 0.75)
        
        # Handle (diagonal)
        handle_rect = pygame.Rect(cx - handle_width // 2, rect.top + h // 8,
                                  handle_width, handle_height)
        pygame.draw.rect(surface, handle_color, handle_rect)
        pygame.draw.rect(surface, (100, 60, 30), handle_rect, 1)
        
        # Pick head (two pointed ends)
        head_y = rect.top + h // 6
        
        # Left point
        left_points = [
            (rect.left + 2, head_y - h // 8),
            (cx - handle_width // 2 - 2, head_y + h // 10),
            (rect.left + 2, head_y + h // 6),
        ]
        pygame.draw.polygon(surface, head_color, left_points)
        pygame.draw.polygon(surface, (90, 90, 100), left_points, 1)
        
        # Right point
        right_points = [
            (rect.right - 2, head_y - h // 8),
            (cx + handle_width // 2 + 2, head_y + h // 10),
            (rect.right - 2, head_y + h // 6),
        ]
        pygame.draw.polygon(surface, head_color, right_points)
        pygame.draw.polygon(surface, (90, 90, 100), right_points, 1)
        
        # Center piece
        center_rect = pygame.Rect(cx - w // 6, head_y - h // 12, w // 3, h // 6)
        pygame.draw.rect(surface, head_color, center_rect)
        pygame.draw.rect(surface, (90, 90, 100), center_rect, 1)
    
    elif tool_type == ToolType.AXE:
        # Draw axe - blade on one side
        handle_width = w // 5
        handle_height = int(h * 0.75)
        
        # Handle
        handle_rect = pygame.Rect(cx - handle_width // 2, rect.top + h // 8,
                                  handle_width, handle_height)
        pygame.draw.rect(surface, handle_color, handle_rect)
        pygame.draw.rect(surface, (100, 60, 30), handle_rect, 1)
        
        # Axe head
        head_y = rect.top + h // 6
        blade_width = w // 2
        blade_height = h // 3
        
        # Blade (curved on one side, straight on other)
        blade_points = [
            (cx - handle_width // 2 - 2, head_y),  # Inner top
            (cx + blade_width, head_y - h // 12),  # Outer top
            (cx + blade_width + w // 8, head_y + blade_height // 2),  # Outer middle (curve)
            (cx + blade_width, head_y + blade_height),  # Outer bottom
            (cx - handle_width // 2 - 2, head_y + blade_height),  # Inner bottom
        ]
        pygame.draw.polygon(surface, head_color, blade_points)
        pygame.draw.polygon(surface, (90, 90, 100), blade_points, 1)
        
        # Blade edge highlight
        pygame.draw.line(surface, blade_color, 
                        (cx + blade_width, head_y - h // 12),
                        (cx + blade_width + w // 8 - 2, head_y + blade_height // 2), 2)
    
    elif tool_type == ToolType.SHOVEL:
        # Draw shovel - spade head with handle
        handle_width = w // 5
        handle_height = int(h * 0.6)
        
        # Handle
        handle_rect = pygame.Rect(cx - handle_width // 2, rect.top + h // 4,
                                  handle_width, handle_height)
        pygame.draw.rect(surface, handle_color, handle_rect)
        pygame.draw.rect(surface, (100, 60, 30), handle_rect, 1)
        
        # Shovel head (spade shape)
        head_y = rect.top + h // 5
        head_width = w // 3
        head_height = h // 3
        
        # Spade-shaped blade
        blade_points = [
            (cx, rect.top + 2),  # Top point
            (cx + head_width, head_y + head_height // 3),  # Right
            (cx + head_width // 2, head_y + head_height),  # Bottom right
            (cx - head_width // 2, head_y + head_height),  # Bottom left
            (cx - head_width, head_y + head_height // 3),  # Left
        ]
        pygame.draw.polygon(surface, head_color, blade_points)
        pygame.draw.polygon(surface, (90, 90, 100), blade_points, 1)
        
        # Highlight on blade
        pygame.draw.line(surface, blade_color, (cx, rect.top + 4), (cx, head_y + head_height // 2), 2)
    
    elif tool_type == ToolType.BOW:
        # Draw bow - curved wooden bow with string
        bow_color = (139, 90, 43)  # Brown wood
        string_color = (200, 200, 200)  # Light string
        
        # Draw curved bow body
        # Left side of bow (curved)
        bow_points = [
            (rect.left + 4, rect.top + 4),  # Top left
            (cx - w // 6, rect.top + h // 4),  # Upper curve
            (cx - w // 8, cy),  # Middle curve
            (cx - w // 6, rect.bottom - h // 4),  # Lower curve
            (rect.left + 4, rect.bottom - 4),  # Bottom left
        ]
        pygame.draw.lines(surface, bow_color, False, bow_points, 3)
        
        # Bow string
        string_points = [
            (rect.left + 4, rect.top + 4),
            (cx + w // 6, cy),  # String pulled back slightly
            (rect.left + 4, rect.bottom - 4),
        ]
        pygame.draw.lines(surface, string_color, False, string_points, 1)
        
        # Arrow nocked on string
        arrow_color = (150, 140, 100)
        # Arrow shaft
        pygame.draw.line(surface, arrow_color, 
                        (cx + w // 6, cy), (rect.right - 4, cy), 2)
        # Arrow head
        pygame.draw.polygon(surface, (150, 150, 150), [
            (rect.right - 4, cy),
            (rect.right - 8, cy - 3),
            (rect.right - 8, cy + 3),
        ])
        # Fletching
        pygame.draw.polygon(surface, (100, 50, 50), [
            (cx + w // 6, cy),
            (cx + w // 6 - 6, cy - 4),
            (cx + w // 6 - 6, cy + 4),
        ])


def draw_item(surface, item_type, rect):
    """Draw a non-tool item (blocks, arrows, etc.) with custom graphics."""
    cx = rect.centerx
    cy = rect.centery
    
    if item_type == ItemType.ARROW:
        # Draw arrow
        arrow_color = (150, 140, 100)  # Wood shaft
        head_color = (150, 150, 150)  # Metal head
        fletch_color = (100, 50, 50)  # Red fletching
        
        # Shaft (horizontal)
        pygame.draw.line(surface, arrow_color, 
                        (rect.left + 4, cy), (rect.right - 8, cy), 2)
        
        # Arrow head
        pygame.draw.polygon(surface, head_color, [
            (rect.right - 4, cy),
            (rect.right - 10, cy - 4),
            (rect.right - 10, cy + 4),
        ])
        
        # Fletching
        pygame.draw.polygon(surface, fletch_color, [
            (rect.left + 6, cy),
            (rect.left + 2, cy - 5),
            (rect.left + 2, cy + 5),
        ])
        
    elif item_type == BlockType.PLANKS:
        # Draw planks with wood grain
        base_color = (180, 140, 80)
        pygame.draw.rect(surface, base_color, rect)
        
        # Wood grain lines
        grain_color = (150, 110, 50)
        for i in range(3):
            y = rect.top + rect.height * (i + 1) // 4
            pygame.draw.line(surface, grain_color, 
                           (rect.left, int(y)), (rect.right, int(y)), 1)
        
        # Vertical grain marks
        for i in range(4):
            x = rect.left + rect.width * (i + 1) // 5
            pygame.draw.line(surface, grain_color,
                           (int(x), rect.top), (int(x), rect.bottom), 1)
        
        pygame.draw.rect(surface, (120, 80, 40), rect, 1)
        
    elif item_type == BlockType.DOOR:
        # Draw door icon (mini door)
        door_color = (139, 90, 43)
        panel_color = (100, 60, 30)
        
        # Door frame
        pygame.draw.rect(surface, door_color, rect)
        
        # Door panels
        panel_margin = rect.width // 6
        panel_rect = pygame.Rect(
            rect.left + panel_margin,
            rect.top + panel_margin,
            rect.width - panel_margin * 2,
            rect.height - panel_margin * 2
        )
        pygame.draw.rect(surface, panel_color, panel_rect)
        
        # Door handle
        handle_x = rect.right - rect.width // 4
        handle_y = cy
        handle_size = max(2, rect.width // 8)
        pygame.draw.circle(surface, (200, 180, 50), (handle_x, handle_y), handle_size)
        
    else:
        # Default: draw colored block
        color = get_item_color(item_type)
        pygame.draw.rect(surface, color, rect)
        pygame.draw.rect(surface, BLACK, rect, 1)


def draw_item_in_slot(surface, item_type, rect, is_tool_item=False):
    """Draw an item (block or tool) in a slot rect."""
    if is_tool_item:
        draw_tool(surface, item_type, rect)
    else:
        draw_item(surface, item_type, rect)


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
        
        # Crafting
        self.craftable_items = []  # List of craftable (result_item, result_count, ingredients)
        self.hovered_craft = -1  # Index of hovered craft item

    def add_item(self, item_type, count=1):
        """Add an item to the inventory. Returns True if successful."""
        # Tools don't stack - find an empty slot
        if is_tool(item_type):
            for i, slot in enumerate(self.hotbar):
                if slot is None:
                    self.hotbar[i] = (item_type, 1)
                    return True
            for row in range(INVENTORY_ROWS):
                for col in range(INVENTORY_COLS):
                    if self.storage[row][col] is None:
                        self.storage[row][col] = (item_type, 1)
                        return True
            return False
        
        # For blocks: First, try to stack with existing items in hotbar
        for i, slot in enumerate(self.hotbar):
            if slot is not None and slot[0] == item_type:
                self.hotbar[i] = (item_type, slot[1] + count)
                return True

        # Try to stack in storage
        for row in range(INVENTORY_ROWS):
            for col in range(INVENTORY_COLS):
                slot = self.storage[row][col]
                if slot is not None and slot[0] == item_type:
                    self.storage[row][col] = (item_type, slot[1] + count)
                    return True

        # Otherwise, find an empty slot in hotbar
        for i, slot in enumerate(self.hotbar):
            if slot is None:
                self.hotbar[i] = (item_type, count)
                return True

        # Then try storage
        for row in range(INVENTORY_ROWS):
            for col in range(INVENTORY_COLS):
                if self.storage[row][col] is None:
                    self.storage[row][col] = (item_type, count)
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
        # Add extra height at top for title (30 pixels)
        return pygame.Rect(start_x - 10, start_y - 40, total_width + 20, total_height + 50)

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

    def get_all_items(self):
        """Get all items in inventory as a dict {item_type: count}."""
        items = {}
        for slot in self.hotbar:
            if slot is not None:
                item_type, count = slot
                items[item_type] = items.get(item_type, 0) + count
        for row in self.storage:
            for slot in row:
                if slot is not None:
                    item_type, count = slot
                    items[item_type] = items.get(item_type, 0) + count
        return items

    def update_craftable(self):
        """Update the list of craftable items based on current inventory."""
        items = self.get_all_items()
        self.craftable_items = get_craftable_items(items)

    def craft_item(self, result_item):
        """Craft an item. Returns True if successful."""
        if result_item not in CRAFTING_RECIPES:
            return False
        
        result_count, ingredients = CRAFTING_RECIPES[result_item]
        
        # Check if we have all ingredients
        items = self.get_all_items()
        for ingredient, needed_count in ingredients:
            if items.get(ingredient, 0) < needed_count:
                return False
        
        # Remove ingredients from inventory
        for ingredient, needed_count in ingredients:
            removed = 0
            # Remove from hotbar first
            for i, slot in enumerate(self.hotbar):
                if removed >= needed_count:
                    break
                if slot is not None and slot[0] == ingredient:
                    item_type, count = slot
                    to_remove = min(count, needed_count - removed)
                    if to_remove >= count:
                        self.hotbar[i] = None
                    else:
                        self.hotbar[i] = (item_type, count - to_remove)
                    removed += to_remove
            # Then remove from storage
            for row in range(INVENTORY_ROWS):
                if removed >= needed_count:
                    break
                for col in range(INVENTORY_COLS):
                    if removed >= needed_count:
                        break
                    slot = self.storage[row][col]
                    if slot is not None and slot[0] == ingredient:
                        item_type, count = slot
                        to_remove = min(count, needed_count - removed)
                        if to_remove >= count:
                            self.storage[row][col] = None
                        else:
                            self.storage[row][col] = (item_type, count - to_remove)
                        removed += to_remove
        
        # Add result to inventory
        self.add_item(result_item, result_count)
        self.update_craftable()
        return True

    def get_craft_slot_rect(self, index):
        """Get the screen rect for a crafting slot on the left side."""
        craft_panel_x = 10
        craft_panel_y = 80
        craft_slot_size = 36
        craft_padding = 5
        
        y = craft_panel_y + index * (craft_slot_size + craft_padding)
        return pygame.Rect(craft_panel_x, y, craft_slot_size, craft_slot_size)

    def check_craft_hover(self, mouse_x, mouse_y):
        """Check which craft slot is being hovered. Returns index or -1."""
        for i in range(len(self.craftable_items)):
            if self.get_craft_slot_rect(i).collidepoint(mouse_x, mouse_y):
                return i
        return -1

    def handle_click(self, mouse_x, mouse_y, button=1):
        """Handle mouse click. Returns clicked slot info or None."""
        # Check crafting panel if inventory is open
        if self.is_open:
            craft_slot = self.check_craft_hover(mouse_x, mouse_y)
            if craft_slot >= 0 and craft_slot < len(self.craftable_items):
                result_item, result_count, ingredients = self.craftable_items[craft_slot]
                self.craft_item(result_item)
                return ('craft', craft_slot)
        
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
                item_type, count = slot_data
                
                # Draw item (smaller than slot)
                item_margin = 4
                item_rect = pygame.Rect(
                    rect.x + item_margin,
                    rect.y + item_margin,
                    rect.width - item_margin * 2,
                    rect.height - item_margin * 2
                )
                draw_item_in_slot(surface, item_type, item_rect, is_tool(item_type))

                # Draw count (don't show count for tools)
                if not is_tool(item_type):
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
                    item_type, count = slot_data

                    item_margin = 4
                    item_rect = pygame.Rect(
                        rect.x + item_margin,
                        rect.y + item_margin,
                        rect.width - item_margin * 2,
                        rect.height - item_margin * 2
                    )
                    draw_item_in_slot(surface, item_type, item_rect, is_tool(item_type))

                    # Draw count (don't show count for tools)
                    if not is_tool(item_type):
                        count_text = font.render(str(count), True, WHITE)
                        surface.blit(count_text, (rect.right - count_text.get_width() - 2,
                                                  rect.bottom - count_text.get_height() - 2))

    def draw_crafting_panel(self, surface, mouse_x, mouse_y):
        """Draw the crafting panel on the left side."""
        if not self.is_open:
            return
        
        # Update craftable items
        self.update_craftable()
        
        # Panel background
        panel_x = 5
        panel_y = 60
        panel_width = 200  # Wider for item names
        panel_height = 40 + len(self.craftable_items) * 50
        if panel_height < 100:
            panel_height = 100
        
        panel_rect = pygame.Rect(panel_x, panel_y, panel_width, panel_height)
        pygame.draw.rect(surface, (30, 30, 40), panel_rect)
        pygame.draw.rect(surface, (100, 100, 120), panel_rect, 2)
        
        # Title
        title_font = pygame.font.SysFont(None, 22)
        title = title_font.render("Crafting", True, WHITE)
        surface.blit(title, (panel_x + 10, panel_y + 5))
        
        # Draw craftable items
        font = pygame.font.SysFont(None, 16)
        name_font = pygame.font.SysFont(None, 18)
        craft_slot_size = 36
        
        self.hovered_craft = self.check_craft_hover(mouse_x, mouse_y)
        
        for i, (result_item, result_count, ingredients) in enumerate(self.craftable_items):
            slot_rect = self.get_craft_slot_rect(i)
            
            # Highlight if hovered
            if i == self.hovered_craft:
                pygame.draw.rect(surface, (80, 80, 100), slot_rect)
                pygame.draw.rect(surface, YELLOW, slot_rect, 2)
            else:
                pygame.draw.rect(surface, (60, 60, 70), slot_rect)
                pygame.draw.rect(surface, (100, 100, 110), slot_rect, 1)
            
            # Draw result item
            item_margin = 3
            item_rect = pygame.Rect(
                slot_rect.x + item_margin,
                slot_rect.y + item_margin,
                slot_rect.width - item_margin * 2,
                slot_rect.height - item_margin * 2
            )
            draw_item_in_slot(surface, result_item, item_rect, is_tool(result_item))
            
            # Draw result item name and count
            result_name = get_item_name(result_item)
            name_text = name_font.render(f"{result_name} x{result_count}", True, WHITE)
            surface.blit(name_text, (slot_rect.right + 5, slot_rect.y + 2))
            
            # Draw ingredient hint
            ingredient_text = "Needs: "
            for ing, cnt in ingredients:
                ing_name = get_item_name(ing)
                ingredient_text += f"{cnt} {ing_name}, "
            ingredient_text = ingredient_text.rstrip(", ")
            ing_surface = font.render(ingredient_text, True, (180, 180, 180))
            surface.blit(ing_surface, (slot_rect.right + 5, slot_rect.y + 20))
        
        # Show "No recipes" if nothing craftable
        if not self.craftable_items:
            no_craft = font.render("No items to craft", True, (150, 150, 150))
            surface.blit(no_craft, (panel_x + 10, panel_y + 35))

    def draw_drag_item(self, surface, mouse_x, mouse_y):
        """Draw the item being dragged at mouse position."""
        if self.dragging and self.drag_item is not None:
            item_type, count = self.drag_item

            # Draw item following mouse
            item_rect = pygame.Rect(
                mouse_x - INVENTORY_SLOT_SIZE // 2,
                mouse_y - INVENTORY_SLOT_SIZE // 2,
                INVENTORY_SLOT_SIZE,
                INVENTORY_SLOT_SIZE
            )
            draw_item_in_slot(surface, item_type, item_rect, is_tool(item_type))
            pygame.draw.rect(surface, YELLOW, item_rect, 2)

            # Draw count (don't show for tools)
            if not is_tool(item_type):
                font = pygame.font.SysFont(None, 18)
                count_text = font.render(str(count), True, WHITE)
                surface.blit(count_text, (item_rect.right - count_text.get_width() - 2,
                                          item_rect.bottom - count_text.get_height() - 2))

    def draw(self, surface, mouse_x=0, mouse_y=0):
        """Draw the inventory (hotbar always, storage if open)."""
        self.draw_hotbar(surface)
        if self.is_open:
            self.draw_crafting_panel(surface, mouse_x, mouse_y)
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
            item_type, count = item_data
            name = get_item_name(item_type)

            font = pygame.font.SysFont(None, 24)
            if is_tool(item_type):
                text = font.render(f"{name}", True, WHITE)
            else:
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
