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
        # Track open doors: set of (x, y) tuples for doors that are open
        self.open_doors = set()

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

        # Tree trunk (wood) - very tall trees (12-18 blocks)
        trunk_height = random.randint(12, 18)
        for ty in range(trunk_height):
            y = ground_y - 1 - ty
            if 0 <= y < self.height:
                self.grid[y][x] = BlockType.WOOD

        # Tree leaves (a larger canopy)
        canopy_y = ground_y - trunk_height - 1
        canopy_size = 3
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
        block = self.get_block(x, y)
        # Open doors are not solid
        if block == BlockType.DOOR and (x, y) in self.open_doors:
            return False
        return is_block_solid(block)
    
    def toggle_door(self, x, y):
        """Toggle a door open/closed. Toggles all 3 blocks of a door. Returns True if successful."""
        if 0 <= x < self.width and 0 <= y < self.height:
            if self.grid[y][x] == BlockType.DOOR:
                # Find all door blocks in this column (up to 3)
                door_positions = []
                # Check current position
                door_positions.append((x, y))
                # Check above
                for dy in range(1, 3):
                    check_y = y - dy
                    if 0 <= check_y < self.height and self.grid[check_y][x] == BlockType.DOOR:
                        door_positions.append((x, check_y))
                # Check below
                for dy in range(1, 3):
                    check_y = y + dy
                    if 0 <= check_y < self.height and self.grid[check_y][x] == BlockType.DOOR:
                        door_positions.append((x, check_y))
                
                # Toggle all door blocks
                is_open = (x, y) in self.open_doors
                for dx, dy in door_positions:
                    if is_open:
                        self.open_doors.discard((dx, dy))
                    else:
                        self.open_doors.add((dx, dy))
                return True
        return False
    
    def break_door(self, x, y):
        """Break all blocks of a door. Returns list of (x, y) positions broken."""
        if 0 <= x < self.width and 0 <= y < self.height:
            if self.grid[y][x] == BlockType.DOOR:
                # Find all door blocks in this column
                door_positions = []
                door_positions.append((x, y))
                # Check above
                for dy in range(1, 3):
                    check_y = y - dy
                    if 0 <= check_y < self.height and self.grid[check_y][x] == BlockType.DOOR:
                        door_positions.append((x, check_y))
                # Check below
                for dy in range(1, 3):
                    check_y = y + dy
                    if 0 <= check_y < self.height and self.grid[check_y][x] == BlockType.DOOR:
                        door_positions.append((x, check_y))
                
                # Remove all door blocks
                for dx, dy in door_positions:
                    self.grid[dy][dx] = BlockType.AIR
                    self.open_doors.discard((dx, dy))
                
                return door_positions
        return []
    
    def is_door_open(self, x, y):
        """Check if a door at (x, y) is open."""
        return (x, y) in self.open_doors

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

                # Draw block (no border to avoid micro gaps)
                color = get_block_color(block_type)
                rect = pygame.Rect(int(sx), int(sy), int(scaled_size) + 1, int(scaled_size) + 1)
                
                # Special drawing for doors
                if block_type == BlockType.DOOR:
                    is_open = (x, y) in self.open_doors
                    
                    # Determine which part of the door this is
                    # Check if there's a door block below (this is top or middle)
                    has_door_below = (y + 1 < self.height and self.grid[y + 1][x] == BlockType.DOOR)
                    # Check if there's a door block above (this is bottom or middle)
                    has_door_above = (y - 1 >= 0 and self.grid[y - 1][x] == BlockType.DOOR)
                    
                    if is_open:
                        # Draw open door - thin vertical strip
                        pygame.draw.rect(surface, color, rect)
                        # Draw opening (darker inner area)
                        inner_rect = pygame.Rect(int(sx) + int(scaled_size * 0.7), int(sy), 
                                                int(scaled_size * 0.3) + 1, int(scaled_size) + 1)
                        pygame.draw.rect(surface, (60, 40, 20), inner_rect)
                    else:
                        # Draw closed door - only draw details on bottom block
                        pygame.draw.rect(surface, color, rect)
                        
                        if not has_door_below:
                            # This is the bottom of the door - draw handle and bottom panel
                            panel_color = (100, 60, 30)
                            panel_margin = int(scaled_size * 0.08)
                            panel_rect = pygame.Rect(int(sx) + panel_margin, int(sy) + panel_margin,
                                                    int(scaled_size) - panel_margin * 2 + 1, 
                                                    int(scaled_size) - panel_margin * 2 + 1)
                            pygame.draw.rect(surface, panel_color, panel_rect)
                            
                            # Draw handle
                            handle_x = int(sx) + int(scaled_size * 0.75)
                            handle_y = int(sy) + int(scaled_size * 0.5)
                            handle_size = max(2, int(scaled_size * 0.08))
                            pygame.draw.circle(surface, (200, 180, 50), (handle_x, handle_y), handle_size)
                        else:
                            # Middle or top - just draw wood grain
                            panel_color = (100, 60, 30)
                            panel_margin = int(scaled_size * 0.08)
                            panel_rect = pygame.Rect(int(sx) + panel_margin, int(sy) + panel_margin,
                                                    int(scaled_size) - panel_margin * 2 + 1, 
                                                    int(scaled_size) - panel_margin * 2 + 1)
                            pygame.draw.rect(surface, panel_color, panel_rect)
                else:
                    pygame.draw.rect(surface, color, rect)

    def get_player_spawn(self):
        """Find a spawn point for the player."""
        mid_x = self.width // 2
        for y in range(5, self.height):
            if self.is_solid(mid_x, y):
                # Spawn above ground (player is 64x96, so 3 tiles tall)
                return mid_x * TILE_SIZE, (y - 3) * TILE_SIZE
        return mid_x * TILE_SIZE, 100
