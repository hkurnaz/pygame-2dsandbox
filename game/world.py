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


class SimplexNoise:
    """Simplex noise implementation for organic cave generation."""
    
    def __init__(self, seed=None):
        if seed is None:
            seed = random.randint(0, 100000)
        self.seed = seed
        # Permutation table for noise
        self.perm = list(range(256))
        random.seed(seed)
        random.shuffle(self.perm)
        self.perm = self.perm * 2  # Extend to avoid overflow
        
        # Gradient vectors for 2D
        self.gradients = [
            (1, 1), (-1, 1), (1, -1), (-1, -1),
            (1, 0), (-1, 0), (1, 0), (-1, 0),
            (0, 1), (0, -1), (0, 1), (0, -1)
        ]
    
    def _dot(self, g, x, y):
        """Dot product of gradient vector and position."""
        return g[0] * x + g[1] * y
    
    def _fade(self, t):
        """Fade function: 6t^5 - 15t^4 + 10t^3"""
        return t * t * t * (t * (t * 6 - 15) + 10)
    
    def noise_2d(self, x, y):
        """Generate 2D simplex noise value (-1 to 1)."""
        # Skew the input space to determine which simplex cell we're in
        F2 = 0.5 * (math.sqrt(3.0) - 1.0)
        s = (x + y) * F2
        i = int(x + s)
        j = int(y + s)
        
        # Unskew the cell origin back to (x,y) space
        G2 = (3.0 - math.sqrt(3.0)) / 6.0
        t = (i + j) * G2
        X0 = i - t
        Y0 = j - t
        x0 = x - X0
        y0 = y - Y0
        
        # Determine which simplex we are in
        if x0 > y0:
            i1, j1 = 1, 0  # Lower triangle, XY order
        else:
            i1, j1 = 0, 1  # Upper triangle, YX order
        
        # Offsets for middle and last corners
        x1 = x0 - i1 + G2
        y1 = y0 - j1 + G2
        x2 = x0 - 1.0 + 2.0 * G2
        y2 = y0 - 1.0 + 2.0 * G2
        
        # Hash coordinates of the corners
        ii = i & 255
        jj = j & 255
        gi0 = self.perm[ii + self.perm[jj]] % 12
        gi1 = self.perm[ii + i1 + self.perm[jj + j1]] % 12
        gi2 = self.perm[ii + 1 + self.perm[jj + 1]] % 12
        
        # Calculate contributions from the three corners
        n0 = n1 = n2 = 0.0
        
        # Corner 0
        t0 = 0.5 - x0 * x0 - y0 * y0
        if t0 >= 0:
            t0 *= t0
            n0 = t0 * t0 * self._dot(self.gradients[gi0], x0, y0)
        
        # Corner 1
        t1 = 0.5 - x1 * x1 - y1 * y1
        if t1 >= 0:
            t1 *= t1
            n1 = t1 * t1 * self._dot(self.gradients[gi1], x1, y1)
        
        # Corner 2
        t2 = 0.5 - x2 * x2 - y2 * y2
        if t2 >= 0:
            t2 *= t2
            n2 = t2 * t2 * self._dot(self.gradients[gi2], x2, y2)
        
        # Add contributions and scale to [-1, 1] range
        return 70.0 * (n0 + n1 + n2)
    
    def fractal_noise(self, x, y, octaves=4, persistence=0.5, lacunarity=2.0):
        """Generate fractal noise by combining multiple octaves."""
        total = 0.0
        amplitude = 1.0
        frequency = 1.0
        max_value = 0.0
        
        for _ in range(octaves):
            total += self.noise_2d(x * frequency, y * frequency) * amplitude
            max_value += amplitude
            amplitude *= persistence
            frequency *= lacunarity
        
        return total / max_value  # Normalize to [-1, 1]


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

        # Generate ores in veins (grouped clusters) - coal, iron, gold
        self._generate_ore_veins()

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
        """Generate an improved cave system with noise-based organic shapes,
        depth layers, biomes, water/lava pools, and large caverns.
        """
        # Initialize noise generators with different seeds for variation
        cave_noise = SimplexNoise(seed=random.randint(0, 100000))
        detail_noise = SimplexNoise(seed=random.randint(0, 100000))
        biome_noise = SimplexNoise(seed=random.randint(0, 100000))
        
        # Generate caves in three depth layers
        self._generate_shallow_caves(cave_noise, detail_noise, biome_noise)
        self._generate_mid_caves(cave_noise, detail_noise, biome_noise)
        self._generate_deep_caves(cave_noise, detail_noise, biome_noise)
        
        # Add surface entrances
        self._create_surface_entrances()
        
        # Add water and lava pools
        self._add_fluid_pools()
        
        # Add large vertical caverns
        self._add_large_caverns(cave_noise)
    
    def _generate_shallow_caves(self, cave_noise, detail_noise, biome_noise):
        """Generate shallow caves (y=18-30): small, fragmented, with ice biome."""
        y_start, y_end = 18, 30
        scale = 40  # Smaller caves
        threshold = 0.45  # Higher threshold = less caves
        
        for y in range(y_start, y_end):
            for x in range(5, self.width - 5):
                if self.grid[y][x] in (BlockType.AIR, BlockType.GRASS):
                    continue
                
                # Fractal noise for organic shape
                noise_val = cave_noise.fractal_noise(x / scale, y / scale, octaves=3)
                detail_val = detail_noise.fractal_noise(x / 15, y / 15, octaves=2)
                combined = noise_val * 0.7 + detail_val * 0.3
                
                if combined > threshold:
                    # Determine biome
                    biome_val = biome_noise.noise_2d(x / 80, y / 80)
                    
                    if biome_val > 0.3:
                        # Ice biome - replace stone with ice
                        if self.grid[y][x] == BlockType.STONE:
                            self.grid[y][x] = BlockType.ICE
                    elif biome_val < -0.3:
                        # Mossy biome
                        if self.grid[y][x] == BlockType.STONE:
                            self.grid[y][x] = BlockType.MOSSY_STONE
                    
                    # Carve cave
                    if self.grid[y][x] not in (BlockType.AIR, BlockType.GRASS):
                        self.grid[y][x] = BlockType.AIR
    
    def _generate_mid_caves(self, cave_noise, detail_noise, biome_noise):
        """Generate mid-level caves (y=30-45): larger, water pools, crystal biome."""
        y_start, y_end = 30, 45
        scale = 55  # Medium caves
        threshold = 0.35  # More caves at this level
        
        for y in range(y_start, y_end):
            for x in range(5, self.width - 5):
                if self.grid[y][x] in (BlockType.AIR, BlockType.GRASS):
                    continue
                
                # Fractal noise
                noise_val = cave_noise.fractal_noise(x / scale, y / scale, octaves=4)
                detail_val = detail_noise.fractal_noise(x / 20, y / 20, octaves=2)
                combined = noise_val * 0.6 + detail_val * 0.4
                
                if combined > threshold:
                    # Determine biome
                    biome_val = biome_noise.noise_2d(x / 100, y / 100)
                    
                    if biome_val > 0.4:
                        # Crystal biome
                        if self.grid[y][x] == BlockType.STONE and random.random() < 0.3:
                            self.grid[y][x] = BlockType.CRYSTAL
                    elif biome_val < -0.4:
                        # Mossy biome
                        if self.grid[y][x] == BlockType.STONE:
                            self.grid[y][x] = BlockType.MOSSY_STONE
                    
                    # Carve cave
                    if self.grid[y][x] not in (BlockType.AIR, BlockType.GRASS):
                        self.grid[y][x] = BlockType.AIR
    
    def _generate_deep_caves(self, cave_noise, detail_noise, biome_noise):
        """Generate deep caves (y=45+): huge caverns, lava pools, crystal biome."""
        y_start = 45
        scale = 70  # Large caves
        threshold = 0.25  # Most open at this level
        
        for y in range(y_start, self.height - 5):
            for x in range(5, self.width - 5):
                if self.grid[y][x] in (BlockType.AIR, BlockType.GRASS):
                    continue
                
                # Fractal noise with lower frequency for bigger caves
                noise_val = cave_noise.fractal_noise(x / scale, y / scale, octaves=4, persistence=0.6)
                detail_val = detail_noise.fractal_noise(x / 25, y / 25, octaves=3)
                combined = noise_val * 0.5 + detail_val * 0.5
                
                if combined > threshold:
                    # Deep caves favor crystal biome
                    biome_val = biome_noise.noise_2d(x / 120, y / 120)
                    
                    if biome_val > 0.2:
                        # Crystal biome - more common deep
                        if self.grid[y][x] == BlockType.STONE and random.random() < 0.4:
                            self.grid[y][x] = BlockType.CRYSTAL
                    
                    # Carve cave
                    if self.grid[y][x] not in (BlockType.AIR, BlockType.GRASS):
                        self.grid[y][x] = BlockType.AIR
    
    def _create_surface_entrances(self):
        """Create cave entrances that connect surface to underground.
        Not too frequent - 2-4 entrances per world, some from mountains."""
        num_entrances = random.randint(2, 4)
        
        for _ in range(num_entrances):
            entrance_x = random.randint(15, self.width - 15)
            
            # Find surface at this x
            surface_y = None
            for y in range(self.height):
                if self.grid[y][entrance_x] == BlockType.GRASS:
                    surface_y = y
                    break
            
            if surface_y is None:
                continue
            
            # Create entrance shaft using noise for organic shape
            shaft_depth = random.randint(10, 20)
            width = random.randint(2, 4)
            
            for dy in range(shaft_depth):
                y = surface_y + dy
                if y >= self.height:
                    break
                
                # Vary width slightly
                current_width = width + random.randint(-1, 1)
                for dx in range(-current_width // 2, current_width // 2 + 1):
                    x = entrance_x + dx
                    if 0 <= x < self.width:
                        if self.grid[y][x] not in (BlockType.AIR, BlockType.GRASS):
                            self.grid[y][x] = BlockType.AIR
    
    def _add_fluid_pools(self):
        """Add water pools in mid caves and lava pools in deep caves."""
        # Water pools in mid-level caves (y=32-42)
        num_water_pools = random.randint(5, 10)
        for _ in range(num_water_pools):
            pool_x = random.randint(10, self.width - 10)
            pool_y = random.randint(32, 42)
            pool_radius = random.randint(3, 6)
            self._create_fluid_pool(pool_x, pool_y, pool_radius, BlockType.WATER)
        
        # Lava pools in deep caves (y=48+)
        num_lava_pools = random.randint(4, 8)
        for _ in range(num_lava_pools):
            pool_x = random.randint(10, self.width - 10)
            pool_y = random.randint(48, self.height - 10)
            pool_radius = random.randint(4, 8)
            self._create_fluid_pool(pool_x, pool_y, pool_radius, BlockType.LAVA)
    
    def _create_fluid_pool(self, cx, cy, radius, fluid_type):
        """Create a pool of fluid with organic shape."""
        noise = SimplexNoise(seed=random.randint(0, 100000))
        
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                dist = math.sqrt(dx * dx + dy * dy)
                
                # Add noise for irregular edge
                edge_noise = noise.noise_2d((cx + dx) / 8, (cy + dy) / 8)
                effective_radius = radius + edge_noise * 2
                
                if dist < effective_radius:
                    x, y = cx + dx, cy + dy
                    if 0 <= x < self.width and 0 <= y < self.height:
                        # Only place fluid in air pockets (caves)
                        if self.grid[y][x] == BlockType.AIR:
                            self.grid[y][x] = fluid_type
    
    def _add_large_caverns(self, noise):
        """Add massive open caverns with vertical drops."""
        num_caverns = random.randint(2, 4)
        
        for _ in range(num_caverns):
            # Place caverns in deep area
            cx = random.randint(30, self.width - 30)
            cy = random.randint(50, self.height - 20)
            
            # Large radius for cavern
            radius_x = random.randint(15, 25)
            radius_y = random.randint(20, 35)
            
            for dy in range(-radius_y, radius_y + 1):
                for dx in range(-radius_x, radius_x + 1):
                    # Elliptical shape with noise
                    dist = math.sqrt((dx / radius_x) ** 2 + (dy / radius_y) ** 2)
                    
                    # Large noise for irregular massive cavern
                    cavern_noise = noise.fractal_noise((cx + dx) / 30, (cy + dy) / 30, octaves=3)
                    threshold = 0.8 + cavern_noise * 0.3
                    
                    if dist < threshold:
                        x, y = cx + dx, cy + dy
                        if 0 <= x < self.width and 0 <= y < self.height:
                            if self.grid[y][x] not in (BlockType.GRASS, BlockType.WATER, BlockType.LAVA):
                                self.grid[y][x] = BlockType.AIR
            
            # Add some crystal formations in the cavern
            self._add_crystal_formations(cx, cy, radius_x, radius_y)
    
    def _add_crystal_formations(self, cx, cy, radius_x, radius_y):
        """Add crystal formations at the edges of a cavern."""
        num_crystals = random.randint(5, 12)
        
        for _ in range(num_crystals):
            # Random position on cavern edge
            angle = random.uniform(0, 2 * math.pi)
            dist = random.uniform(0.7, 1.0) * min(radius_x, radius_y)
            
            x = int(cx + math.cos(angle) * radius_x * (dist / min(radius_x, radius_y)))
            y = int(cy + math.sin(angle) * radius_y * (dist / min(radius_x, radius_y)))
            
            if 0 <= x < self.width and 0 <= y < self.height:
                # Place crystal if it's stone
                if self.grid[y][x] == BlockType.STONE:
                    self.grid[y][x] = BlockType.CRYSTAL
                    # Sometimes extend inward
                    if random.random() < 0.5:
                        dx = int(math.cos(angle) * -1)
                        dy = int(math.sin(angle) * -1)
                        nx, ny = x + dx, y + dy
                        if 0 <= nx < self.width and 0 <= ny < self.height:
                            if self.grid[ny][nx] == BlockType.STONE:
                                self.grid[ny][nx] = BlockType.CRYSTAL

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

    def _generate_ore_veins(self):
        """Generate ore veins - grouped clusters of 3-4 ore blocks.
        
        Instead of scattered individual ores, this creates veins that are
        more realistic and rewarding to find.
        """
        # Coal veins: common, any depth, 8-15 veins per world
        num_coal_veins = random.randint(8, 15)
        for _ in range(num_coal_veins):
            self._create_ore_vein(BlockType.COAL_ORE, min_depth=5, max_depth=self.height - 5, 
                                  vein_size=random.randint(3, 5))
        
        # Iron veins: less common, deeper only (y>20), 5-10 veins
        num_iron_veins = random.randint(5, 10)
        for _ in range(num_iron_veins):
            self._create_ore_vein(BlockType.IRON_ORE, min_depth=20, max_depth=self.height - 5,
                                  vein_size=random.randint(3, 4))
        
        # Gold veins: rare, very deep (y>35), 3-6 veins
        num_gold_veins = random.randint(3, 6)
        for _ in range(num_gold_veins):
            self._create_ore_vein(BlockType.GOLD_ORE, min_depth=35, max_depth=self.height - 5,
                                  vein_size=random.randint(3, 4))
    
    def _create_ore_vein(self, ore_type, min_depth, max_depth, vein_size):
        """Create a single ore vein at a random location.
        
        Args:
            ore_type: The type of ore to place (COAL_ORE, IRON_ORE, GOLD_ORE)
            min_depth: Minimum Y coordinate for the vein
            max_depth: Maximum Y coordinate for the vein
            vein_size: Number of ore blocks in the vein (3-5)
        """
        # Find a valid starting position in stone
        attempts = 0
        while attempts < 50:  # Limit attempts to avoid infinite loops
            start_x = random.randint(5, self.width - 5)
            start_y = random.randint(min_depth, max_depth)
            
            if self.grid[start_y][start_x] == BlockType.STONE:
                break
            attempts += 1
        
        if attempts >= 50:
            return  # Couldn't find valid position
        
        # Create the vein by growing from the starting position
        vein_blocks = [(start_x, start_y)]
        self.grid[start_y][start_x] = ore_type
        
        # Grow the vein by adding adjacent stone blocks
        for _ in range(vein_size - 1):
            if not vein_blocks:
                break
            
            # Pick a random block from the existing vein
            base_x, base_y = random.choice(vein_blocks)
            
            # Try to add an adjacent stone block
            directions = [(0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (-1, -1), (1, -1), (-1, 1)]
            random.shuffle(directions)
            
            for dx, dy in directions:
                new_x = base_x + dx
                new_y = base_y + dy
                
                # Check bounds
                if 0 <= new_x < self.width and 0 <= new_y < self.height:
                    # Only replace stone, not other ores or air
                    if self.grid[new_y][new_x] == BlockType.STONE:
                        self.grid[new_y][new_x] = ore_type
                        vein_blocks.append((new_x, new_y))
                        break

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
                elif block_type == BlockType.WATER:
                    # Draw water - blue with surface highlight
                    pygame.draw.rect(surface, (50, 100, 200), rect)
                    # Surface shimmer (lighter top)
                    shimmer_rect = pygame.Rect(int(sx), int(sy), int(scaled_size) + 1, int(scaled_size * 0.3))
                    pygame.draw.rect(surface, (80, 140, 220), shimmer_rect)
                    # Bubbles
                    if random.random() < 0.1:
                        bubble_x = int(sx) + random.randint(2, int(scaled_size) - 2)
                        bubble_y = int(sy) + random.randint(2, int(scaled_size) - 2)
                        pygame.draw.circle(surface, (100, 160, 240), (bubble_x, bubble_y), 1)
                elif block_type == BlockType.LAVA:
                    # Draw lava - orange-red with glow
                    pygame.draw.rect(surface, (255, 80, 20), rect)
                    # Surface crust (darker orange)
                    crust_rect = pygame.Rect(int(sx), int(sy), int(scaled_size) + 1, int(scaled_size * 0.25))
                    pygame.draw.rect(surface, (255, 120, 40), crust_rect)
                    # Glow spots
                    if random.random() < 0.15:
                        glow_x = int(sx) + random.randint(3, int(scaled_size) - 3)
                        glow_y = int(sy) + random.randint(3, int(scaled_size) - 3)
                        pygame.draw.circle(surface, (255, 180, 60), (glow_x, glow_y), 2)
                elif block_type == BlockType.ICE:
                    # Draw ice - light blue with transparency effect
                    pygame.draw.rect(surface, (180, 220, 255), rect)
                    # Ice crystal highlights
                    pygame.draw.line(surface, (220, 240, 255),
                                    (int(sx) + 2, int(sy) + 2),
                                    (int(sx) + int(scaled_size * 0.4), int(sy) + int(scaled_size * 0.4)), 2)
                    pygame.draw.line(surface, (200, 230, 255),
                                    (int(sx) + int(scaled_size * 0.6), int(sy) + 2),
                                    (int(sx) + int(scaled_size) - 2, int(sy) + int(scaled_size * 0.5)), 2)
                    # Border
                    pygame.draw.rect(surface, (150, 200, 240), rect, 1)
                elif block_type == BlockType.MOSSY_STONE:
                    # Draw mossy stone - gray-green with moss patches
                    pygame.draw.rect(surface, (100, 120, 80), rect)
                    # Moss patches
                    pygame.draw.ellipse(surface, (80, 140, 60),
                                       (int(sx) + 2, int(sy) + 2, int(scaled_size * 0.5), int(scaled_size * 0.4)))
                    pygame.draw.ellipse(surface, (70, 130, 50),
                                       (int(sx) + int(scaled_size * 0.4), int(sy) + int(scaled_size * 0.3),
                                        int(scaled_size * 0.5), int(scaled_size * 0.5)))
                elif block_type == BlockType.CRYSTAL:
                    # Draw crystal - purple with facets
                    pygame.draw.rect(surface, (200, 150, 255), rect)
                    # Crystal facets (diamond pattern)
                    center_x = int(sx) + int(scaled_size // 2)
                    center_y = int(sy) + int(scaled_size // 2)
                    # Draw X pattern for crystal facets
                    pygame.draw.line(surface, (220, 180, 255),
                                    (int(sx) + 2, int(sy) + 2),
                                    (int(sx) + int(scaled_size) - 2, int(sy) + int(scaled_size) - 2), 2)
                    pygame.draw.line(surface, (220, 180, 255),
                                    (int(sx) + int(scaled_size) - 2, int(sy) + 2),
                                    (int(sx) + 2, int(sy) + int(scaled_size) - 2), 2)
                    # Center highlight
                    pygame.draw.circle(surface, (240, 210, 255), (center_x, center_y), 2)
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
