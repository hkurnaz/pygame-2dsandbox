"""World generation and management for MyArea."""

import random
import pygame
from game.constants import (
    WORLD_WIDTH, WORLD_HEIGHT, TILE_SIZE,
    GRASS_LAYER_DEPTH, DIRT_LAYER_DEPTH, TREE_CHANCE, MIN_TREE_SPACING
)
from game.blocks import (
    BlockType, get_block_color, is_block_solid, is_block_breakable, is_block_air
)


class World:
    """The game world composed of blocks."""

    def __init__(self):
        self.width = WORLD_WIDTH
        self.height = WORLD_HEIGHT
        # 2D grid: world[y][x] = block_type
        self.grid = [[BlockType.AIR for _ in range(self.width)] for _ in range(self.height)]
        self._generated = False

    def generate(self):
        """Generate the world: grass layer, dirt layer, and trees."""
        if self._generated:
            return
        self._generated = True

        # First, generate the terrain base (grass + dirt)
        for x in range(self.width):
            # Random terrain height variation
            base_height = 25 + random.randint(-2, 2)

            # Place grass layer
            for dy in range(GRASS_LAYER_DEPTH):
                y = base_height + dy
                if 0 <= y < self.height:
                    self.grid[y][x] = BlockType.GRASS

            # Place dirt layers below grass
            for dy in range(1, DIRT_LAYER_DEPTH + 1):
                y = base_height + GRASS_LAYER_DEPTH + dy - 1
                if 0 <= y < self.height:
                    self.grid[y][x] = BlockType.DIRT

            # Fill the rest with stone
            for y in range(base_height + GRASS_LAYER_DEPTH + DIRT_LAYER_DEPTH, self.height):
                self.grid[y][x] = BlockType.STONE

        # Generate trees with spacing
        last_tree_x = -MIN_TREE_SPACING
        for x in range(3, self.width - 3):
            if x - last_tree_x < MIN_TREE_SPACING:
                continue
            if random.random() < TREE_CHANCE:
                self._generate_tree(x)
                last_tree_x = x

    def _generate_tree(self, x):
        """Generate a tree at column x."""
        # Find the top of the ground at this column
        ground_y = None
        for y in range(self.height):
            if self.grid[y][x] == BlockType.GRASS:
                ground_y = y
                break
        if ground_y is None:
            return

        # Tree trunk (wood)
        trunk_height = random.randint(4, 6)
        for ty in range(trunk_height):
            y = ground_y - 1 - ty
            if 0 <= y < self.height:
                self.grid[y][x] = BlockType.WOOD

        # Tree leaves (a simple canopy)
        canopy_y = ground_y - trunk_height - 1
        canopy_size = 2
        for dy in range(-canopy_size, canopy_size + 1):
            for dx in range(-canopy_size, canopy_size + 1):
                # Make a rounded canopy
                dist = abs(dx) + abs(dy) * 0.7
                if dist <= canopy_size:
                    y = canopy_y + dy
                    xx = x + dx
                    if 0 <= y < self.height and 0 <= xx < self.width:
                        # Don't overwrite the trunk
                        if self.grid[y][xx] == BlockType.AIR:
                            self.grid[y][xx] = BlockType.LEAVES

    def get_block(self, x, y):
        """Get block type at (x, y). Returns AIR if out of bounds."""
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.grid[y][x]
        return BlockType.AIR

    def set_block(self, x, y, block_type):
        """Set block type at (x, y)."""
        if 0 <= x < self.width and 0 <= y < self.height:
            self.grid[y][x] = block_type

    def is_solid(self, x, y):
        """Check if block at (x, y) is solid."""
        return is_block_solid(self.get_block(x, y))

    def break_block(self, x, y):
        """Break (remove) a block at (x, y) if breakable."""
        if 0 <= x < self.width and 0 <= y < self.height:
            bt = self.grid[y][x]
            if is_block_breakable(bt):
                self.grid[y][x] = BlockType.AIR
                return True
        return False

    def draw(self, surface, camera):
        """Draw the visible portion of the world."""
        left, right, top, bottom = camera.get_visible_tiles()

        # Clamp to valid ranges
        left = max(0, left)
        right = min(self.width, right)
        top = max(0, top)
        bottom = min(self.height, bottom)

        for y in range(top, bottom):
            for x in range(left, right):
                block_type = self.grid[y][x]
                if is_block_air(block_type):
                    continue

                # Compute screen position with zoom
                world_x = x * TILE_SIZE
                world_y = y * TILE_SIZE
                sx, sy = camera.world_to_screen(world_x, world_y)
                scaled_size = TILE_SIZE * camera.zoom

                # Draw block
                color = get_block_color(block_type)
                rect = pygame.Rect(int(sx), int(sy), int(scaled_size), int(scaled_size))
                pygame.draw.rect(surface, color, rect)

                # Draw a subtle border for definition
                pygame.draw.rect(surface, (0, 0, 0), rect, 1)

    def get_player_spawn(self):
        """Find a spawn point for the player."""
        mid_x = self.width // 2
        for y in range(5, self.height):
            if self.is_solid(mid_x, y):
                # Spawn above ground (player is 64x96, so 3 tiles tall)
                return mid_x * TILE_SIZE, (y - 3) * TILE_SIZE
        return mid_x * TILE_SIZE, 100
