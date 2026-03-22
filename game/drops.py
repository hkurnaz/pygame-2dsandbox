"""Dropped items system - items that drop from broken blocks."""

import pygame
import math
from game.constants import (
    DROP_SIZE, DROP_COLLECT_RANGE, DROP_BOB_SPEED, DROP_BOB_AMOUNT,
    TILE_SIZE, YELLOW
)
from game.blocks import get_block_color, get_block_name


class DroppedItem:
    """A dropped item that can be collected by the player."""

    def __init__(self, x, y, block_type):
        self.x = float(x)
        self.y = float(y)
        self.block_type = block_type
        self.size = DROP_SIZE
        self.collected = False
        self.time = 0.0  # For bobbing animation
        self.base_y = y
        self.hovered = False  # For hover effect

    @property
    def rect(self):
        """Return the item's pygame.Rect for collision/collection."""
        return pygame.Rect(
            int(self.x - self.size // 2),
            int(self.y - self.size // 2),
            self.size,
            self.size
        )

    def update(self, dt):
        """Update the dropped item (bobbing animation)."""
        self.time += dt * DROP_BOB_SPEED
        self.y = self.base_y + math.sin(self.time) * DROP_BOB_AMOUNT

    def can_collect(self, player_rect):
        """Check if player is close enough to collect this item."""
        # Check distance from player center to item center
        player_center = player_rect.center
        item_center = (int(self.x), int(self.y))
        dx = player_center[0] - item_center[0]
        dy = player_center[1] - item_center[1]
        distance = math.sqrt(dx * dx + dy * dy)
        return distance < DROP_COLLECT_RANGE

    def check_hover(self, mouse_world_x, mouse_world_y):
        """Check if mouse is hovering over this item."""
        half_size = self.size // 2
        return (self.x - half_size <= mouse_world_x <= self.x + half_size and
                self.y - half_size <= mouse_world_y <= self.y + half_size)

    def draw(self, surface, camera):
        """Draw the dropped item."""
        # Use camera zoom for positioning
        screen_x, screen_y = camera.world_to_screen(self.x, self.y)
        scaled_size = self.size * camera.zoom

        # Draw the item (smaller version of block)
        color = get_block_color(self.block_type)
        rect = pygame.Rect(
            int(screen_x - scaled_size // 2),
            int(screen_y - scaled_size // 2),
            int(scaled_size),
            int(scaled_size)
        )
        pygame.draw.rect(surface, color, rect)

        # Draw yellow border if hovered
        if self.hovered:
            pygame.draw.rect(surface, YELLOW, rect, 2)
        else:
            pygame.draw.rect(surface, (0, 0, 0), rect, 1)


class DropManager:
    """Manages all dropped items in the world."""

    def __init__(self):
        self.drops = []

    def spawn_drop(self, x, y, block_type):
        """Spawn a new dropped item at the given position."""
        # Center the drop in the tile
        drop = DroppedItem(
            x * TILE_SIZE + TILE_SIZE // 2,
            y * TILE_SIZE + TILE_SIZE // 2,
            block_type
        )
        self.drops.append(drop)

    def update(self, dt, player_rect):
        """Update all drops and check for collection."""
        collected = []
        for drop in self.drops:
            drop.update(dt)
            if drop.can_collect(player_rect):
                drop.collected = True
                collected.append(drop)
        return collected

    def check_hover(self, mouse_world_x, mouse_world_y):
        """Check hover state for all drops."""
        for drop in self.drops:
            drop.hovered = drop.check_hover(mouse_world_x, mouse_world_y)

    def remove_drop(self, drop):
        """Remove a collected drop."""
        if drop in self.drops:
            self.drops.remove(drop)

    def draw(self, surface, camera):
        """Draw all dropped items."""
        for drop in self.drops:
            drop.draw(surface, camera)
