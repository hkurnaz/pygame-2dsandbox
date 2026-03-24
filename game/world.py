"""World generation and management for MyArea."""

import math
import random
import pygame
from game.constants import (
    WORLD_WIDTH, WORLD_HEIGHT, TILE_SIZE,
    GRASS_LAYER_DEPTH, DIRT_LAYER_DEPTH, TREE_CHANCE, MIN_TREE_SPACING,
    PLATFORM_THICKNESS
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
        """Generate the world: smooth linear terrain, occasional mountains with caves, and trees."""
        if self._generated:
            return
        self._generated = True

        # Generate smooth base terrain height using a combination of sine waves
        # for linear, realistic terrain with occasional mountains
        terrain_heights = [0] * self.width
        
        # Base smooth terrain (gentle rolling hills)
        for x in range(self.width):
            # Primary gentle wave
            base = 24 + int(2 * math.sin(x * 0.02))
            # Secondary smaller wave for variation
            variation = int(1.5 * math.sin(x * 0.08 + 1.5))
            terrain_heights[x] = base + variation
        
        # Add occasional mountains (large elevations)
        mountain_centers = []
        x = 20
        while x < self.width - 20:
            # Mountain every ~60-100 tiles
            if random.random() < 0.25:  # ~25% chance to have a mountain
                mountain_centers.append(x)
                # Skip ahead so mountains aren't too close
                x += random.randint(55, 85)
            else:
                x += random.randint(20, 35)
        
        # Generate mountain shapes
        for center_x in mountain_centers:
            # Mountain width and height
            mountain_width = random.randint(20, 35)
            mountain_height = random.randint(12, 22)  # Tall mountains
            
            # Generate mountain profile (triangular-ish with some noise)
            for dx in range(-mountain_width // 2, mountain_width // 2 + 1):
                x = center_x + dx
                if 0 <= x < self.width:
                    # Distance from center as fraction
                    frac = abs(dx) / (mountain_width / 2)
                    # Mountain height falls off toward edges
                    height_offset = int(mountain_height * (1 - frac * frac * 0.9))
                    # Add some jaggedness to mountain slopes
                    height_offset += random.randint(-1, 1)
                    terrain_heights[x] = min(terrain_heights[x], 24 - height_offset)
        
        # Smooth the terrain slightly to avoid jaggedness
        smoothed = list(terrain_heights)
        for x in range(1, self.width - 1):
            smoothed[x] = int((terrain_heights[x-1] + terrain_heights[x] * 2 + terrain_heights[x+1]) / 4)
        terrain_heights = smoothed
        
        # Ensure terrain stays within reasonable bounds
        for x in range(self.width):
            terrain_heights[x] = max(8, min(terrain_heights[x], 35))

        # Generate terrain blocks
        for x in range(self.width):
            base_height = terrain_heights[x]

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

        # Generate ores in stone layers (coal, iron, gold)
        for x in range(self.width):
            for y in range(0, self.height):
                if self.grid[y][x] == BlockType.STONE:
                    # Coal: common, spawns at any depth
                    if random.random() < 0.03:  # 3% chance
                        self.grid[y][x] = BlockType.COAL_ORE
                    # Iron: medium rare, deeper layers
                    elif y > 20 and random.random() < 0.015:  # 1.5% chance in deeper stone
                        self.grid[y][x] = BlockType.IRON_ORE
                    # Gold: rare, very deep
                    elif y > 35 and random.random() < 0.008:  # 0.8% chance in very deep stone
                        self.grid[y][x] = BlockType.GOLD_ORE

        # Generate cave system (Terraria-like)
        self._generate_cave_system()

        # Generate trees with spacing (skip mountain peaks and cave entrances)
        last_tree_x = -MIN_TREE_SPACING
        for x in range(3, self.width - 3):
            if x - last_tree_x < MIN_TREE_SPACING:
                continue
            # Skip if this is near a mountain center (trees would look odd on peaks)
            near_mountain = False
            for mx in mountain_centers:
                if abs(x - mx) < 8:
                    near_mountain = True
                    break
            if near_mountain:
                continue
            if random.random() < TREE_CHANCE:
                self._generate_tree(x)
                last_tree_x = x
    
    def _generate_cave_system(self):
        """Generate a Terraria-like cave system with natural chambers and tunnels.
        
        Features:
        - Multiple cave networks that can interconnect
        - Large chambers connected by narrow tunnels
        - Some caves connect to surface, others are deep underground
        - Irregular but navigable structure
        """
        # Generate several cave networks
        num_cave_networks = random.randint(4, 7)
        
        for network in range(num_cave_networks):
            # Each network has a main chamber with branches
            network_x = random.randint(20, self.width - 20)
            network_y = random.randint(30, self.height - 20)
            
            # Create main chamber
            self._create_cave_chamber(network_x, network_y, random.randint(5, 10))
            
            # Create branching tunnels from the main chamber
            num_branches = random.randint(2, 5)
            for _ in range(num_branches):
                branch_direction = random.uniform(0, 2 * math.pi)
                branch_length = random.randint(15, 40)
                self._create_cave_tunnel(
                    network_x, network_y,
                    branch_direction, branch_length
                )
        
        # Create some surface entrances
        num_entrances = random.randint(3, 5)
        for _ in range(num_entrances):
            entrance_x = random.randint(10, self.width - 10)
            # Find surface at this x
            surface_y = None
            for y in range(self.height):
                if self.grid[y][entrance_x] == BlockType.GRASS:
                    surface_y = y
                    break
            if surface_y:
                self._create_surface_entrance(entrance_x, surface_y)
        
        # Connect nearby caves (create passages between them)
        self._connect_nearby_caves()
    
    def _create_cave_chamber(self, cx, cy, radius):
        """Create a roughly circular cave chamber."""
        # Use noise to make it irregular
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                dist = math.sqrt(dx * dx + dy * dy)
                # Add irregularity
                noise = random.uniform(0.7, 1.3)
                if dist * noise < radius:
                    tx = cx + dx
                    ty = cy + dy
                    if 0 <= tx < self.width and 0 <= ty < self.height:
                        # Don't clear surface blocks
                        if self.grid[ty][tx] not in (BlockType.AIR, BlockType.GRASS):
                            # Keep some blocks for visual interest (stalactites, etc.)
                            if random.random() < 0.95:
                                self.grid[ty][tx] = BlockType.AIR
    
    def _create_cave_tunnel(self, start_x, start_y, direction, length):
        """Create a winding tunnel from a starting point."""
        current_x = float(start_x)
        current_y = float(start_y)
        
        # Tunnel width varies
        base_width = random.uniform(1.5, 3.0)
        
        for step in range(length):
            # Add some waviness to the tunnel
            direction += random.uniform(-0.3, 0.3)
            
            # Move along the tunnel
            current_x += math.cos(direction) * 1.5
            current_y += math.sin(direction) * 1.5
            
            # Clamp to bounds
            if current_x < 5 or current_x >= self.width - 5:
                break
            if current_y < 10 or current_y >= self.height - 5:
                break
            
            # Carve tunnel at current position
            width = base_width + random.uniform(-0.5, 0.5)
            self._carve_tunnel_section(int(current_x), int(current_y), width)
            
            # Occasionally create a small chamber
            if random.random() < 0.05:
                chamber_radius = random.randint(2, 4)
                self._create_cave_chamber(int(current_x), int(current_y), chamber_radius)
    
    def _carve_tunnel_section(self, cx, cy, width):
        """Carve a roughly circular section of tunnel."""
        radius = int(width)
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                if dx * dx + dy * dy <= width * width:
                    tx = cx + dx
                    ty = cy + dy
                    if 0 <= tx < self.width and 0 <= ty < self.height:
                        if self.grid[ty][tx] not in (BlockType.AIR, BlockType.GRASS):
                            self.grid[ty][tx] = BlockType.AIR
    
    def _create_surface_entrance(self, entrance_x, surface_y):
        """Create a cave entrance that connects to the surface."""
        # Create a shaft going down
        shaft_width = random.randint(2, 4)
        shaft_depth = random.randint(8, 15)
        
        start_x = entrance_x - shaft_width // 2
        
        # Clear entrance shaft
        for dy in range(shaft_depth):
            for dx in range(shaft_width):
                tx = start_x + dx
                ty = surface_y + dy
                if 0 <= tx < self.width and 0 <= ty < self.height:
                    self.grid[ty][tx] = BlockType.AIR
        
        # At the bottom, create a small chamber
        chamber_y = surface_y + shaft_depth
        self._create_cave_chamber(entrance_x, chamber_y, random.randint(3, 5))
        
        # Create a tunnel going somewhere from the chamber
        tunnel_direction = random.uniform(-math.pi/4, math.pi/4) + math.pi/2  # Mostly downward
        self._create_cave_tunnel(entrance_x, chamber_y, tunnel_direction, random.randint(20, 40))
    
    def _connect_nearby_caves(self):
        """Connect caves that are close to each other."""
        # Find air pockets and try to connect nearby ones
        for _ in range(10):  # Try 10 random connections
            # Pick a random underground air block
            x = random.randint(10, self.width - 10)
            y = random.randint(30, self.height - 10)
            
            if self.grid[y][x] != BlockType.AIR:
                continue
            
            # Try to find another air pocket nearby
            for direction in range(8):
                angle = direction * math.pi / 4
                check_dist = random.randint(10, 25)
                tx = int(x + math.cos(angle) * check_dist)
                ty = int(y + math.sin(angle) * check_dist)
                
                if 0 <= tx < self.width and 0 <= ty < self.height:
                    if self.grid[ty][tx] == BlockType.AIR:
                        # Found nearby cave - create a connecting tunnel
                        self._create_direct_tunnel(x, y, tx, ty)
                        break
    
    def _create_direct_tunnel(self, x1, y1, x2, y2):
        """Create a direct tunnel between two points."""
        dx = x2 - x1
        dy = y2 - y1
        distance = math.sqrt(dx * dx + dy * dy)
        
        if distance < 1:
            return
        
        # Normalize direction
        dx /= distance
        dy /= distance
        
        # Carve tunnel along the line
        for step in range(int(distance)):
            tx = int(x1 + dx * step)
            ty = int(y1 + dy * step)
            
            # Carve a small section
            for ox in range(-1, 2):
                for oy in range(-1, 2):
                    cx = tx + ox
                    cy = ty + oy
                    if 0 <= cx < self.width and 0 <= cy < self.height:
                        if self.grid[cy][cx] not in (BlockType.AIR, BlockType.GRASS):
                            self.grid[cy][cx] = BlockType.AIR

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
                    has_door_below = (y + 1 < self.height and self.grid[y + 1][x] == BlockType.DOOR)
                    has_door_above = (y - 1 >= 0 and self.grid[y - 1][x] == BlockType.DOOR)
                    
                    if is_open:
                        # Draw open door - thin vertical strip on side
                        pygame.draw.rect(surface, color, rect)
                        # Draw opening (darker inner area)
                        inner_rect = pygame.Rect(int(sx) + int(scaled_size * 0.7), int(sy), 
                                                int(scaled_size * 0.3) + 1, int(scaled_size) + 1)
                        pygame.draw.rect(surface, (60, 40, 20), inner_rect)
                    else:
                        # Draw closed door with 3D wooden look
                        pygame.draw.rect(surface, color, rect)
                        
                        # Darker frame
                        frame_color = (100, 60, 30)
                        pygame.draw.rect(surface, frame_color, rect, width=max(1, int(scaled_size * 0.1)))
                        
                        # Inner panel (slightly inset)
                        inset = int(scaled_size * 0.15)
                        panel_rect = pygame.Rect(int(sx) + inset, int(sy) + inset,
                                                int(scaled_size) - inset * 2 + 1, 
                                                int(scaled_size) - inset * 2 + 1)
                        pygame.draw.rect(surface, (120, 80, 40), panel_rect)
                        
                        # Wood grain lines
                        grain_color = (90, 55, 25)
                        for i in range(3):
                            gy = int(sy) + inset + int((scaled_size - inset*2) * (i + 1) / 4)
                            pygame.draw.line(surface, grain_color,
                                           (int(sx) + inset, gy),
                                           (int(sx) + int(scaled_size) - inset, gy),
                                           max(1, int(camera.zoom)))
                        
                        # Handle - centered horizontally, middle of the whole 3-block door
                        # Find if this is the middle block
                        is_middle = has_door_below and has_door_above
                        is_top = not has_door_above
                        is_bottom = not has_door_below
                        
                        # Draw handle on middle block (or top if no middle)
                        if is_middle:
                            handle_x = int(sx) + int(scaled_size * 0.5)  # Center
                            handle_y = int(sy) + int(scaled_size * 0.5)
                            handle_size = max(2, int(scaled_size * 0.1))
                            # Handle base
                            pygame.draw.circle(surface, (60, 60, 60), (handle_x, handle_y), handle_size)
                            # Handle highlight
                            pygame.draw.circle(surface, (200, 180, 50), (handle_x, handle_y), handle_size - 1)
                        elif is_top and not has_door_below:
                            # Single-block door - handle in center
                            handle_x = int(sx) + int(scaled_size * 0.5)
                            handle_y = int(sy) + int(scaled_size * 0.5)
                            handle_size = max(2, int(scaled_size * 0.1))
                            pygame.draw.circle(surface, (60, 60, 60), (handle_x, handle_y), handle_size)
                            pygame.draw.circle(surface, (200, 180, 50), (handle_x, handle_y), handle_size - 1)
                elif block_type == BlockType.PLATFORM:
                    # Draw platform - thin horizontal plank at top of tile
                    platform_height = int(PLATFORM_THICKNESS * camera.zoom)
                    platform_rect = pygame.Rect(int(sx), int(sy), int(scaled_size) + 1, platform_height)
                    pygame.draw.rect(surface, color, platform_rect)
                    # Draw wood grain lines
                    grain_color = (130, 90, 40)
                    for i in range(3):
                        line_y = int(sy) + int(platform_height * (i + 1) / 4)
                        pygame.draw.line(surface, grain_color, 
                                        (int(sx), line_y), 
                                        (int(sx) + int(scaled_size), line_y), 
                                        max(1, int(camera.zoom)))
                    # Draw darker edge at bottom
                    pygame.draw.line(surface, (100, 70, 30),
                                    (int(sx), int(sy) + platform_height - 1),
                                    (int(sx) + int(scaled_size), int(sy) + platform_height - 1),
                                    max(1, int(camera.zoom)))
                elif block_type == BlockType.TORCH:
                    # Draw torch - wooden stick with flame on top
                    center_x = int(sx) + int(scaled_size // 2)
                    center_y = int(sy) + int(scaled_size // 2)
                    
                    # Draw wooden stick (vertical rectangle in center)
                    stick_width = max(2, int(scaled_size * 0.2))
                    stick_height = int(scaled_size * 0.6)
                    stick_rect = pygame.Rect(
                        center_x - stick_width // 2,
                        center_y - int(scaled_size * 0.1),
                        stick_width,
                        stick_height
                    )
                    pygame.draw.rect(surface, (101, 67, 33), stick_rect)  # Brown wood color
                    
                    # Draw flame on top (animated-ish with multiple circles)
                    flame_base_y = center_y - int(scaled_size * 0.2)
                    flame_size = int(scaled_size * 0.35)
                    
                    # Outer flame (orange-red)
                    pygame.draw.circle(surface, (255, 100, 0), 
                                      (center_x, flame_base_y), flame_size)
                    # Middle flame (orange)
                    pygame.draw.circle(surface, (255, 165, 0), 
                                      (center_x, flame_base_y - 2), int(flame_size * 0.7))
                    # Inner flame (yellow)
                    pygame.draw.circle(surface, (255, 255, 100), 
                                      (center_x, flame_base_y - 4), int(flame_size * 0.4))
                    # Bright center
                    pygame.draw.circle(surface, (255, 255, 200), 
                                      (center_x, flame_base_y - 5), int(flame_size * 0.2))
                elif block_type == BlockType.COAL_ORE:
                    # Draw coal ore - dark with black specks
                    pygame.draw.rect(surface, (60, 60, 60), rect)  # Dark gray base
                    # Coal chunks
                    pygame.draw.rect(surface, (30, 30, 30), 
                                    (int(sx) + 4, int(sy) + 4, int(scaled_size * 0.3), int(scaled_size * 0.3)))
                    pygame.draw.rect(surface, (40, 40, 40),
                                    (int(sx) + int(scaled_size * 0.5), int(sy) + int(scaled_size * 0.4), 
                                     int(scaled_size * 0.4), int(scaled_size * 0.4)))
                elif block_type == BlockType.IRON_ORE:
                    # Draw iron ore - brownish with metallic flecks
                    pygame.draw.rect(surface, (120, 100, 80), rect)  # Brownish stone
                    # Iron flecks
                    pygame.draw.circle(surface, (180, 160, 140), 
                                      (int(sx) + int(scaled_size * 0.3), int(sy) + int(scaled_size * 0.3)), 4)
                    pygame.draw.circle(surface, (170, 150, 130),
                                      (int(sx) + int(scaled_size * 0.7), int(sy) + int(scaled_size * 0.6)), 3)
                    pygame.draw.circle(surface, (160, 140, 120),
                                      (int(sx) + int(scaled_size * 0.5), int(sy) + int(scaled_size * 0.8)), 3)
                elif block_type == BlockType.GOLD_ORE:
                    # Draw gold ore - yellowish metallic
                    pygame.draw.rect(surface, (160, 140, 80), rect)  # Yellowish base
                    # Gold nuggets
                    pygame.draw.circle(surface, (255, 215, 0), 
                                      (int(sx) + int(scaled_size * 0.35), int(sy) + int(scaled_size * 0.3)), 5)
                    pygame.draw.circle(surface, (240, 200, 0),
                                      (int(sx) + int(scaled_size * 0.65), int(sy) + int(scaled_size * 0.7)), 4)
                elif block_type == BlockType.FURNACE:
                    # Draw furnace - stone block with opening
                    pygame.draw.rect(surface, (80, 80, 80), rect)  # Dark gray stone
                    # Frame
                    pygame.draw.rect(surface, (60, 60, 60), rect, width=max(2, int(scaled_size * 0.1)))
                    # Furnace opening (dark interior)
                    opening = pygame.Rect(int(sx) + int(scaled_size * 0.2), int(sy) + int(scaled_size * 0.2),
                                         int(scaled_size * 0.6), int(scaled_size * 0.6))
                    pygame.draw.rect(surface, (30, 30, 30), opening)
                    # Glowing embers inside
                    pygame.draw.circle(surface, (255, 100, 0),
                                      (int(sx) + int(scaled_size * 0.5), int(sy) + int(scaled_size * 0.5)), 3)
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
