"""Enemy system - zombies that spawn at night."""

import pygame
import math
import random
import heapq
from game.constants import (
    ZOMBIE_WIDTH, ZOMBIE_HEIGHT, ZOMBIE_SPEED, ZOMBIE_HEALTH,
    ZOMBIE_DAMAGE, TILE_SIZE, GRAVITY, MAX_FALL_SPEED,
    EYE_WIDTH, EYE_HEIGHT, EYE_SPEED, EYE_HEALTH, EYE_DAMAGE,
    EYE_KNOCKBACK_FORCE, EYE_PLAYER_DRAG_DISTANCE,
    ZOMBIE_SPAWN_INTERVAL, ZOMBIE_MAX_COUNT,
    EYE_SPAWN_INTERVAL, EYE_MAX_COUNT
)
from game.blocks import is_block_solid, BlockType


class PathNode:
    """Node for A* pathfinding."""
    __slots__ = ['x', 'y', 'g', 'h', 'f', 'parent']
    
    def __init__(self, x, y, g=0, h=0, parent=None):
        self.x = x
        self.y = y
        self.g = g  # Cost from start
        self.h = h  # Heuristic (estimated cost to goal)
        self.f = g + h  # Total cost
        self.parent = parent
    
    def __lt__(self, other):
        return self.f < other.f
    
    def __eq__(self, other):
        return self.x == other.x and self.y == other.y
    
    def __hash__(self):
        return hash((self.x, self.y))


def heuristic(a_x, a_y, b_x, b_y):
    """Octile distance heuristic for grid movement (allows diagonals)."""
    dx = abs(a_x - b_x)
    dy = abs(a_y - b_y)
    return max(dx, dy) + (math.sqrt(2) - 1) * min(dx, dy)


def is_tile_passable(world, tx, ty, require_clearance=False):
    """Check if a tile is passable for flying enemies.
    
    Args:
        world: The game world
        tx, ty: Tile coordinates
        require_clearance: If True, also check that the tile below is passable
                          (for flying enemies that are taller than 1 tile)
    """
    if not (0 <= tx < world.width and 0 <= ty < world.height):
        return False
    bt = world.get_block(tx, ty)
    # Flying enemies can pass through air, wood, and leaves
    passable = bt in (BlockType.WOOD, BlockType.LEAVES, BlockType.AIR)
    
    if passable and require_clearance:
        # Check tile below - the eye is 1.5 tiles tall, so it needs clearance below
        ty_below = ty + 1
        if 0 <= ty_below < world.height:
            bt_below = world.get_block(tx, ty_below)
            # Tile below must also be passable (or we adjust position later)
            passable = bt_below in (BlockType.WOOD, BlockType.LEAVES, BlockType.AIR)
    
    return passable


def find_path_astar(world, start_x, start_y, goal_x, goal_y, max_search_distance=50):
    """
    Find a path using A* algorithm.
    
    Args:
        world: The game world
        start_x, start_y: Starting tile coordinates
        goal_x, goal_y: Goal tile coordinates
        max_search_distance: Maximum search radius to limit computation
    
    Returns:
        List of (x, y) tile coordinates representing the path, or None if no path found
    """
    # Limit search to a reasonable area around start and goal for performance
    min_x = max(0, min(start_x, goal_x) - max_search_distance)
    max_x = min(world.width - 1, max(start_x, goal_x) + max_search_distance)
    min_y = max(0, min(start_y, goal_y) - max_search_distance)
    max_y = min(world.height - 1, max(start_y, goal_y) + max_search_distance)
    
    # Check if goal is passable
    if not is_tile_passable(world, goal_x, goal_y):
        # Try to find nearby passable tile
        found = False
        for radius in range(1, 5):
            for dx in range(-radius, radius + 1):
                for dy in range(-radius, radius + 1):
                    if abs(dx) + abs(dy) == radius:
                        check_x, check_y = goal_x + dx, goal_y + dy
                        if is_tile_passable(world, check_x, check_y):
                            goal_x, goal_y = check_x, check_y
                            found = True
                            break
                if found:
                    break
            if found:
                break
        if not found:
            return None
    
    start_node = PathNode(start_x, start_y, g=0, h=heuristic(start_x, start_y, goal_x, goal_y))
    goal_node = PathNode(goal_x, goal_y)
    
    open_set = []
    heapq.heappush(open_set, start_node)
    open_set_lookup = {(start_x, start_y): start_node}
    closed_set = set()
    
    # 8-directional movement (including diagonals)
    # Cost: 1 for cardinal, sqrt(2) for diagonal
    directions = [
        (0, -1, 1.0), (0, 1, 1.0), (-1, 0, 1.0), (1, 0, 1.0),  # Cardinal
        (-1, -1, 1.414), (1, -1, 1.414), (-1, 1, 1.414), (1, 1, 1.414)  # Diagonal
    ]
    
    nodes_examined = 0
    max_nodes = 2000  # Limit search to prevent lag spikes
    
    while open_set and nodes_examined < max_nodes:
        current = heapq.heappop(open_set)
        del open_set_lookup[(current.x, current.y)]
        
        if (current.x, current.y) == (goal_x, goal_y):
            # Reconstruct path
            path = []
            node = current
            while node:
                path.append((node.x, node.y))
                node = node.parent
            return path[::-1]  # Reverse to get start -> goal
        
        closed_set.add((current.x, current.y))
        nodes_examined += 1
        
        for dx, dy, move_cost in directions:
            neighbor_x = current.x + dx
            neighbor_y = current.y + dy
            
            # Bounds check
            if not (min_x <= neighbor_x <= max_x and min_y <= neighbor_y <= max_y):
                continue
            
            # Skip if already evaluated
            if (neighbor_x, neighbor_y) in closed_set:
                continue
            
            # Check passability
            if not is_tile_passable(world, neighbor_x, neighbor_y):
                continue
            
            # For diagonal movement, check that we don't cut corners
            if dx != 0 and dy != 0:
                if not (is_tile_passable(world, current.x + dx, current.y) or 
                        is_tile_passable(world, current.x, current.y + dy)):
                    continue
            
            g_score = current.g + move_cost
            
            if (neighbor_x, neighbor_y) in open_set_lookup:
                neighbor = open_set_lookup[(neighbor_x, neighbor_y)]
                if g_score < neighbor.g:
                    neighbor.g = g_score
                    neighbor.f = g_score + neighbor.h
                    neighbor.parent = current
                    # Re-heapify (remove and re-add)
                    open_set.remove(neighbor)
                    heapq.heapify(open_set)
                    heapq.heappush(open_set, neighbor)
            else:
                h_score = heuristic(neighbor_x, neighbor_y, goal_x, goal_y)
                neighbor = PathNode(neighbor_x, neighbor_y, g_score, h_score, current)
                open_set_lookup[(neighbor_x, neighbor_y)] = neighbor
                heapq.heappush(open_set, neighbor)
    
    # No path found within limits
    return None


class Zombie:
    """A zombie enemy that walks toward the player."""

    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)
        self.vx = 0.0
        self.vy = 0.0
        self.width = ZOMBIE_WIDTH
        self.height = ZOMBIE_HEIGHT
        self.health = ZOMBIE_HEALTH
        self.max_health = ZOMBIE_HEALTH
        self.on_ground = False
        self.facing_right = True
        self.hit_flash = 0.0  # Timer for hit flash effect
        self.attack_cooldown = 0.0
        self.walk_animation = 0.0
        self.knockback_timer = 0.0  # Timer to prevent AI overriding knockback

    @property
    def rect(self):
        """Return the zombie's pygame.Rect for collisions."""
        return pygame.Rect(int(self.x), int(self.y), self.width, self.height)

    def take_damage(self, amount):
        """Take damage and return True if dead."""
        self.health -= amount
        self.hit_flash = 0.2  # Flash for 0.2 seconds
        return self.health <= 0

    def apply_knockback(self, from_x, force=8):
        """Apply knockback away from a point (e.g., player)."""
        my_center_x = self.x + self.width / 2
        if my_center_x > from_x:
            self.vx = force  # Push right
        else:
            self.vx = -force  # Push left
        # No upward knockback - just horizontal push
        self.facing_right = self.vx > 0
        self.knockback_timer = 0.3  # AI won't override velocity for 0.3 seconds

    def update(self, dt, world, player_rect, is_night=True):
        """Update zombie physics and AI."""
        # Update timers
        if self.hit_flash > 0:
            self.hit_flash -= dt
        if self.attack_cooldown > 0:
            self.attack_cooldown -= dt
        if self.knockback_timer > 0:
            self.knockback_timer -= dt
        
        # Walk animation
        self.walk_animation += dt * 5

        # AI: Move toward player at night, run away during day
        # Skip AI movement if knockback is active
        if self.knockback_timer <= 0:
            player_center_x = player_rect.centerx
            my_center_x = self.x + self.width / 2
            
            if is_night:
                # Night: chase player
                if player_center_x > my_center_x + 10:
                    self.vx = ZOMBIE_SPEED
                    self.facing_right = True
                elif player_center_x < my_center_x - 10:
                    self.vx = -ZOMBIE_SPEED
                    self.facing_right = False
                else:
                    self.vx = 0
            else:
                # Day: run away from player
                if player_center_x > my_center_x + 10:
                    self.vx = -ZOMBIE_SPEED  # Run left (away)
                    self.facing_right = False
                elif player_center_x < my_center_x - 10:
                    self.vx = ZOMBIE_SPEED  # Run right (away)
                    self.facing_right = True
                else:
                    # If too close, run in a random direction
                    self.vx = ZOMBIE_SPEED if random.random() > 0.5 else -ZOMBIE_SPEED
                    self.facing_right = self.vx > 0

        # Apply gravity
        self.vy += GRAVITY
        if self.vy > MAX_FALL_SPEED:
            self.vy = MAX_FALL_SPEED

        # Apply friction when knockback is active
        if self.knockback_timer > 0:
            self.vx *= 0.9  # Friction slows down knockback

        # Horizontal movement with collision
        self.x += self.vx
        self._resolve_horizontal_collisions(world)

        # Vertical movement with collision
        self.y += self.vy
        self._resolve_vertical_collisions(world)

        # Check if can attack player
        if self.attack_cooldown <= 0 and self.rect.colliderect(player_rect):
            self.attack_cooldown = 1.0
            return ZOMBIE_DAMAGE  # Return damage to apply to player
        return 0

    def _resolve_horizontal_collisions(self, world):
        """Resolve collisions on the horizontal axis."""
        rect = self.rect
        left_tile = rect.left // TILE_SIZE
        right_tile = rect.right // TILE_SIZE
        top_tile = rect.top // TILE_SIZE
        bottom_tile = rect.bottom // TILE_SIZE

        for ty in range(top_tile, bottom_tile + 1):
            for tx in range(left_tile, right_tile + 1):
                if world.is_solid(tx, ty):
                    block_rect = pygame.Rect(
                        tx * TILE_SIZE,
                        ty * TILE_SIZE,
                        TILE_SIZE,
                        TILE_SIZE
                    )
                    if rect.colliderect(block_rect):
                        if self.vx > 0:
                            self.x = block_rect.left - self.width
                            # Try to jump over obstacle (can jump 2+ blocks)
                            if self.on_ground:
                                self.vy = -11
                            self.vx = 0
                        elif self.vx < 0:
                            self.x = block_rect.right
                            if self.on_ground:
                                self.vy = -11
                            self.vx = 0
                        rect = self.rect

    def _resolve_vertical_collisions(self, world):
        """Resolve collisions on the vertical axis."""
        rect = self.rect
        left_tile = rect.left // TILE_SIZE
        right_tile = rect.right // TILE_SIZE
        top_tile = rect.top // TILE_SIZE
        bottom_tile = rect.bottom // TILE_SIZE

        self.on_ground = False

        for ty in range(top_tile, bottom_tile + 1):
            for tx in range(left_tile, right_tile + 1):
                if world.is_solid(tx, ty):
                    block_rect = pygame.Rect(
                        tx * TILE_SIZE,
                        ty * TILE_SIZE,
                        TILE_SIZE,
                        TILE_SIZE
                    )
                    if rect.colliderect(block_rect):
                        if self.vy > 0:
                            self.y = block_rect.top - self.height
                            self.vy = 0
                            self.on_ground = True
                        elif self.vy < 0:
                            self.y = block_rect.bottom
                            self.vy = 0
                        rect = self.rect

    def draw(self, surface, camera):
        """Draw the zombie."""
        screen_rect = camera.apply(self.rect)
        zoom = camera.zoom
        
        def scale(val):
            return max(1, int(val * zoom))
        
        # Colors
        if self.hit_flash > 0:
            body_color = (255, 100, 100)  # Red flash when hit
        else:
            body_color = (80, 120, 80)  # Greenish zombie
        head_color = (100, 140, 100)
        pants_color = (50, 50, 70)
        
        # Body proportions
        head_height = scale(20)
        body_height = scale(28)
        leg_height = scale(24)
        
        # Draw legs with walk animation
        leg_y = screen_rect.y + head_height + body_height
        leg_width = screen_rect.width // 2 - scale(2)
        leg_offset = int(math.sin(self.walk_animation) * scale(3))
        
        # Left leg
        left_leg = pygame.Rect(
            screen_rect.x + scale(2) - leg_offset,
            leg_y,
            leg_width,
            leg_height
        )
        pygame.draw.rect(surface, pants_color, left_leg)
        
        # Right leg
        right_leg = pygame.Rect(
            screen_rect.x + screen_rect.width // 2 + leg_offset,
            leg_y,
            leg_width,
            leg_height
        )
        pygame.draw.rect(surface, pants_color, right_leg)
        
        # Body
        body_rect = pygame.Rect(
            screen_rect.x,
            screen_rect.y + head_height,
            screen_rect.width,
            body_height
        )
        pygame.draw.rect(surface, body_color, body_rect)
        
        # Arms (stretched forward like a zombie)
        arm_width = scale(8)
        arm_height = scale(24)
        arm_y = screen_rect.y + head_height + scale(4)
        
        if self.facing_right:
            # Right arm stretched forward
            arm_rect = pygame.Rect(
                screen_rect.right - scale(4),
                arm_y,
                arm_width + scale(8),
                arm_height
            )
            pygame.draw.rect(surface, body_color, arm_rect)
            # Left arm
            left_arm = pygame.Rect(
                screen_rect.x - arm_width + scale(4),
                arm_y,
                arm_width,
                arm_height
            )
            pygame.draw.rect(surface, body_color, left_arm)
        else:
            # Left arm stretched forward
            arm_rect = pygame.Rect(
                screen_rect.x - scale(4) - scale(8),
                arm_y,
                arm_width + scale(8),
                arm_height
            )
            pygame.draw.rect(surface, body_color, arm_rect)
            # Right arm
            right_arm = pygame.Rect(
                screen_rect.right - scale(4),
                arm_y,
                arm_width,
                arm_height
            )
            pygame.draw.rect(surface, body_color, right_arm)
        
        # Head
        head_rect = pygame.Rect(
            screen_rect.x + scale(4),
            screen_rect.y,
            screen_rect.width - scale(8),
            head_height
        )
        pygame.draw.rect(surface, head_color, head_rect)
        
        # Eyes (glowing red)
        eye_y = screen_rect.y + scale(8)
        eye_size = scale(4)
        eye_spacing = scale(6)
        
        left_eye = pygame.Rect(
            screen_rect.centerx - eye_spacing - eye_size // 2,
            eye_y,
            eye_size,
            eye_size
        )
        pygame.draw.rect(surface, (255, 50, 50), left_eye)
        
        right_eye = pygame.Rect(
            screen_rect.centerx + eye_spacing - eye_size // 2,
            eye_y,
            eye_size,
            eye_size
        )
        pygame.draw.rect(surface, (255, 50, 50), right_eye)
        
        # Health bar
        if self.health < self.max_health:
            bar_width = screen_rect.width
            bar_height = scale(4)
            bar_y = screen_rect.y - bar_height - scale(2)
            
            # Background
            pygame.draw.rect(surface, (50, 50, 50),
                           (screen_rect.x, bar_y, bar_width, bar_height))
            
            # Health fill
            health_width = int(bar_width * (self.health / self.max_health))
            pygame.draw.rect(surface, (255, 50, 50),
                           (screen_rect.x, bar_y, health_width, bar_height))


class FlyingEye:
    """A flying eye enemy that floats and chases the player at night using A* pathfinding."""

    # Class-level path cache to share paths between eyes when targeting same area
    _path_cache = {}
    _cache_clear_timer = 0.0
    
    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)
        self.vx = 0.0
        self.vy = 0.0
        self.width = EYE_WIDTH
        self.height = EYE_HEIGHT
        self.health = EYE_HEALTH
        self.max_health = EYE_HEALTH
        self.facing_right = True
        self.hit_flash = 0.0
        self.attack_cooldown = 0.0
        self.knockback_timer = 0.0
        self.float_animation = 0.0  # For floating effect
        self.pulse_animation = 0.0  # For eye pulsing
        # Nerve/tail segments (relative positions)
        self.tail_segments = [(0, 0) for _ in range(5)]
        self.tail_wave = 0.0
        
        # A* Pathfinding system
        self.path = []  # List of (x, y) tile waypoints
        self.current_waypoint_index = 0  # Index of current waypoint in path
        self.path_recalculation_timer = 0.0  # Time until next path recalculation
        self.path_recalculation_interval = 0.5  # Recalculate path every 0.5 seconds
        self.stuck_timer = 0.0
        self.last_x = x
        self.last_y = y
        self.waypoint_reached_distance = TILE_SIZE * 0.5  # Distance to consider waypoint reached
        self.pathfinding_fail_count = 0  # Track consecutive failures
        
        # Smooth steering
        self.target_x = None  # Current target position (world coords)
        self.target_y = None
        self.steering_force_x = 0.0
        self.steering_force_y = 0.0
        self.max_force = 0.5  # Maximum steering force
        self.arrival_distance = TILE_SIZE * 3  # Distance to start slowing down

    @property
    def rect(self):
        """Return the flying eye's pygame.Rect for collisions."""
        return pygame.Rect(int(self.x), int(self.y), self.width, self.height)

    def take_damage(self, amount):
        """Take damage and return True if dead."""
        self.health -= amount
        self.hit_flash = 0.2
        return self.health <= 0

    def apply_knockback(self, from_x, force=EYE_KNOCKBACK_FORCE):
        """Apply knockback away from a point."""
        my_center_x = self.x + self.width / 2
        if my_center_x > from_x:
            self.vx = force
        else:
            self.vx = -force
        self.knockback_timer = 0.3

    def _check_path_clear(self, world, dx, dy, distance_tiles=2):
        """Check if a path is clear in the given direction."""
        # Check tiles ahead in the direction
        my_center_x = self.x + self.width / 2
        my_center_y = self.y + self.height / 2
        
        for i in range(1, distance_tiles + 1):
            check_x = int((my_center_x + dx * i * TILE_SIZE) // TILE_SIZE)
            check_y = int((my_center_y + dy * i * TILE_SIZE) // TILE_SIZE)
            
            if 0 <= check_x < world.width and 0 <= check_y < world.height:
                bt = world.get_block(check_x, check_y)
                if bt not in (BlockType.WOOD, BlockType.LEAVES, BlockType.AIR) and world.is_solid(check_x, check_y):
                    return False
        return True
    
    def _find_obstacle_height(self, world, dx):
        """Find the height of the obstacle ahead and if there's a clear route over it.
        
        Returns (obstacle_height_tiles, can_go_over, max_height_needed)
        - obstacle_height_tiles: how many tiles tall the wall is
        - can_go_over: True if there's open air above the wall
        - max_height_needed: tiles of vertical clearance needed to fly over
        """
        my_center_x = self.x + self.width / 2
        my_center_y = self.y + self.height / 2
        my_tile_y = int(my_center_y // TILE_SIZE)
        
        # Look ahead 1-4 tiles horizontally
        check_x = int((my_center_x + dx * 2 * TILE_SIZE) // TILE_SIZE)
        if not (0 <= check_x < world.width):
            return (0, True, 0)
        
        # Scan vertically to find the top of the obstacle
        # Start from eye's level and scan up/down
        obstacle_top = my_tile_y
        obstacle_bottom = my_tile_y
        
        # Find bottom of obstacle (scan down)
        for ty in range(my_tile_y, min(my_tile_y + 10, world.height)):
            bt = world.get_block(check_x, ty)
            if bt not in (BlockType.WOOD, BlockType.LEAVES, BlockType.AIR) and world.is_solid(check_x, ty):
                obstacle_bottom = ty
            else:
                break
        
        # Find top of obstacle (scan up from eye level)
        for ty in range(my_tile_y, max(my_tile_y - 10, 0), -1):
            bt = world.get_block(check_x, ty)
            if bt not in (BlockType.WOOD, BlockType.LEAVES, BlockType.AIR) and world.is_solid(check_x, ty):
                obstacle_top = ty
            else:
                break
        
        obstacle_height = obstacle_bottom - obstacle_top + 1
        
        # Check if there's clear space above the obstacle
        clear_above = True
        for ty in range(obstacle_top - 1, max(obstacle_top - 4, 0), -1):
            bt = world.get_block(check_x, ty)
            if bt not in (BlockType.WOOD, BlockType.LEAVES, BlockType.AIR) and world.is_solid(check_x, ty):
                clear_above = False
                break
        
        # Height needed to clear: we need to be above the obstacle top by at least 1 tile
        height_needed = obstacle_top - my_tile_y - 1  # negative means we need to go up
        
        return (obstacle_height, clear_above, height_needed)

    def _get_path_cache_key(self, start_tile, goal_tile):
        """Generate a cache key for path lookup."""
        # Round positions to reduce cache fragmentation
        return (start_tile[0] // 3, start_tile[1] // 3, goal_tile[0] // 3, goal_tile[1] // 3)
    
    def _request_path(self, world, start_tile, goal_tile):
        """Request a path, using cache if available."""
        cache_key = self._get_path_cache_key(start_tile, goal_tile)
        
        # Check cache
        if cache_key in FlyingEye._path_cache:
            cached_path, timestamp = FlyingEye._path_cache[cache_key]
            # Cache valid for 2 seconds
            if pygame.time.get_ticks() - timestamp < 2000:
                return cached_path
        
        # Calculate new path with dynamic search distance based on target distance
        target_dist = abs(goal_tile[0] - start_tile[0]) + abs(goal_tile[1] - start_tile[1])
        search_dist = max(80, min(target_dist + 20, 150))  # 80-150 tile search radius
        path = find_path_astar(world, start_tile[0], start_tile[1], 
                               goal_tile[0], goal_tile[1], max_search_distance=search_dist)
        
        if path:
            FlyingEye._path_cache[cache_key] = (path, pygame.time.get_ticks())
        
        return path
    
    def _smooth_path(self, world, path):
        """Simplify path by removing unnecessary waypoints using line-of-sight checks."""
        if len(path) <= 2:
            return path
        
        smoothed = [path[0]]  # Always keep start
        i = 0
        
        while i < len(path) - 1:
            # Try to skip ahead as far as possible
            furthest = i + 1
            for j in range(min(i + 5, len(path) - 1), i, -1):
                if self._has_line_of_sight(world, path[i], path[j]):
                    furthest = j
                    break
            smoothed.append(path[furthest])
            i = furthest
        
        return smoothed
    
    def _has_line_of_sight(self, world, start, end):
        """Check if there's a clear line of sight between two tile coordinates."""
        x0, y0 = start
        x1, y1 = end
        
        # Bresenham's line algorithm to check tiles
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        
        x, y = x0, y0
        steps = 0
        max_steps = max(dx, dy) + 1
        
        while steps < max_steps:
            if not is_tile_passable(world, x, y):
                return False
            if x == x1 and y == y1:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x += sx
            if e2 < dx:
                err += dx
                y += sy
            steps += 1
        
        return True
    
    def _get_current_waypoint(self, world=None):
        """Get the current waypoint world coordinates, adjusted for eye height.
        
        The eye is 1.5 tiles tall, so if the waypoint is in AIR above solid ground,
        we need to position the eye so its body doesn't overlap solid tiles below.
        """
        if not self.path or self.current_waypoint_index >= len(self.path):
            return None
        
        tile_x, tile_y = self.path[self.current_waypoint_index]
        
        # Check if this tile is passable and if the tile below is solid
        # If so, we need to position the eye higher so it doesn't clip into ground
        if world is not None:
            # Check if tile below is solid (not passable for flying)
            tile_below_y = tile_y + 1
            if (0 <= tile_below_y < world.height and 
                not is_tile_passable(world, tile_x, tile_below_y)):
                # Tile below is solid - position eye so its bottom is above the solid tile
                # Eye center should be at least EYE_HEIGHT/2 above the solid tile's top
                solid_tile_top = tile_below_y * TILE_SIZE
                eye_center_y = solid_tile_top - (EYE_HEIGHT / 2) - 2  # Small margin
                return (tile_x * TILE_SIZE + TILE_SIZE / 2, eye_center_y)
        
        # Default: center of tile
        return (tile_x * TILE_SIZE + TILE_SIZE / 2, 
                tile_y * TILE_SIZE + TILE_SIZE / 2)
    
    def _advance_waypoint(self):
        """Move to next waypoint."""
        self.current_waypoint_index += 1
        if self.current_waypoint_index >= len(self.path):
            self.path = []
            self.current_waypoint_index = 0
    
    def _raycast_obstacle(self, world, direction_x, direction_y, max_distance=64):
        """Cast a ray in the given direction to detect obstacles.
        
        Returns (obstacle_detected, obstacle_distance, obstacle_tile) or (False, max_distance, None).
        Only checks non-passable tiles (AIR/WOOD/LEAVES are passable).
        """
        my_center_x = self.x + self.width / 2
        my_center_y = self.y + self.height / 2
        
        # Normalize direction
        mag = math.sqrt(direction_x**2 + direction_y**2)
        if mag == 0:
            return (False, max_distance, None)
        
        dx = direction_x / mag
        dy = direction_y / mag
        
        # Step along the ray
        step_size = TILE_SIZE / 4  # Check every 8 pixels
        current_dist = 0
        
        while current_dist < max_distance:
            check_x = my_center_x + dx * current_dist
            check_y = my_center_y + dy * current_dist
            
            tile_x = int(check_x // TILE_SIZE)
            tile_y = int(check_y // TILE_SIZE)
            
            if 0 <= tile_x < world.width and 0 <= tile_y < world.height:
                if not is_tile_passable(world, tile_x, tile_y):
                    return (True, current_dist, (tile_x, tile_y))
            
            current_dist += step_size
        
        return (False, max_distance, None)
    
    def _apply_obstacle_avoidance(self, world, desired_vx, desired_vy):
        """Apply steering to avoid obstacles using raycasting.
        
        Returns adjusted (vx, vy) that avoids obstacles.
        """
        # Only apply if we have some desired movement
        if desired_vx == 0 and desired_vy == 0:
            return (0, 0)
        
        # Cast rays in movement direction
        obstacle_detected, dist, tile = self._raycast_obstacle(world, desired_vx, desired_vy, max_distance=48)
        
        if obstacle_detected and dist < 32:
            # Obstacle ahead - apply avoidance steering
            # Calculate perpendicular avoidance direction
            mag = math.sqrt(desired_vx**2 + desired_vy**2)
            if mag > 0:
                # Perpendicular left
                avoid_x = -desired_vy / mag
                avoid_y = desired_vx / mag
                
                # Blend avoidance into desired direction
                avoidance_strength = (32 - dist) / 32  # Stronger as we get closer
                
                adjusted_vx = desired_vx * 0.3 + avoid_x * EYE_SPEED * avoidance_strength
                adjusted_vy = desired_vy * 0.3 + avoid_y * EYE_SPEED * avoidance_strength
                
                return (adjusted_vx, adjusted_vy)
        
        return (desired_vx, desired_vy)
    
    def update(self, dt, world, player_rect, is_night=True):
        """Update flying eye physics and AI using A* pathfinding."""
        # Update class-level cache clear timer
        FlyingEye._cache_clear_timer += dt
        if FlyingEye._cache_clear_timer > 5.0:  # Clear cache every 5 seconds
            FlyingEye._path_cache.clear()
            FlyingEye._cache_clear_timer = 0.0
        
        # Update timers
        if self.hit_flash > 0:
            self.hit_flash -= dt
        if self.attack_cooldown > 0:
            self.attack_cooldown -= dt
        if self.knockback_timer > 0:
            self.knockback_timer -= dt
        
        # Update path recalculation timer
        self.path_recalculation_timer -= dt

        # Animations
        self.float_animation += dt * 3
        self.pulse_animation += dt * 4
        self.tail_wave += dt * 8

        # Check if stuck (not moving much)
        moved_distance = math.sqrt((self.x - self.last_x)**2 + (self.y - self.last_y)**2)
        self.last_x = self.x
        self.last_y = self.y
        
        if moved_distance < 0.5:
            self.stuck_timer += dt
        else:
            self.stuck_timer = 0
            self.pathfinding_fail_count = 0  # Reset on successful movement

        # AI: During day, run away from player; at night, chase player
        if self.knockback_timer <= 0:
            player_center_x = player_rect.centerx
            player_center_y = player_rect.centery
            my_center_x = self.x + self.width / 2
            my_center_y = self.y + self.height / 2
            
            # Calculate direction to player
            dx = player_center_x - my_center_x
            dy = player_center_y - my_center_y
            distance = math.sqrt(dx * dx + dy * dy)
            
            # Determine flee direction (away from player during day, toward at night)
            if is_night:
                # Night: move TOWARD player
                move_dx = dx
                move_dy = dy
            else:
                # Day: move AWAY from player (flee)
                move_dx = -dx
                move_dy = -dy
            
            if distance > 10:
                # Determine target position - flee point or chase point
                if is_night:
                    target_x = player_center_x
                    target_y = player_center_y
                else:
                    # Flee target: extend in direction away from player
                    target_x = my_center_x + move_dx * 3  # Target 3x distance away
                    target_y = my_center_y + move_dy * 3
                
                # Convert to tile coordinates
                my_tile_x = int(my_center_x // TILE_SIZE)
                my_tile_y = int(my_center_y // TILE_SIZE)
                target_tile_x = int(target_x // TILE_SIZE)
                target_tile_y = int(target_y // TILE_SIZE)
                
                # Check if we need to recalculate path
                need_new_path = (
                    not self.path or  # No path
                    self.current_waypoint_index >= len(self.path) or  # Reached end
                    self.stuck_timer > 0.5 or  # Stuck
                    self.path_recalculation_timer <= 0  # Time to refresh
                )
                
                if need_new_path and self.pathfinding_fail_count < 3:
                    # Request new path
                    new_path = self._request_path(
                        world, 
                        (my_tile_x, my_tile_y), 
                        (target_tile_x, target_tile_y)
                    )
                    
                    if new_path and len(new_path) > 1:
                        self.path = self._smooth_path(world, new_path)
                        self.current_waypoint_index = 1  # Start at index 1 (skip start tile)
                        self.path_recalculation_timer = self.path_recalculation_interval
                        self.pathfinding_fail_count = 0
                    else:
                        self.pathfinding_fail_count += 1
                        self.path_recalculation_timer = 0.2  # Retry sooner on failure
                
                # Follow the path
                if self.path and self.current_waypoint_index < len(self.path):
                    waypoint = self._get_current_waypoint(world)
                    
                    if waypoint:
                        wx, wy = waypoint
                        wdx = wx - my_center_x
                        wdy = wy - my_center_y
                        wdist = math.sqrt(wdx * wdx + wdy * wdy)
                        
                        # Check if waypoint reached
                        if wdist < self.waypoint_reached_distance:
                            self._advance_waypoint()
                            if self.current_waypoint_index < len(self.path):
                                waypoint = self._get_current_waypoint(world)
                                if waypoint:
                                    wx, wy = waypoint
                                    wdx = wx - my_center_x
                                    wdy = wy - my_center_y
                                    wdist = math.sqrt(wdx * wdx + wdy * wdy)
                        
                        if wdist > 0:
                            # Steering behavior with arrival slowing
                            if wdist < self.arrival_distance and self.current_waypoint_index >= len(self.path) - 1:
                                # Arrival behavior - slow down near final target
                                speed_factor = wdist / self.arrival_distance
                                desired_vx = (wdx / wdist) * EYE_SPEED * speed_factor
                                desired_vy = (wdy / wdist) * EYE_SPEED * speed_factor
                            else:
                                # Normal movement
                                desired_vx = (wdx / wdist) * EYE_SPEED
                                desired_vy = (wdy / wdist) * EYE_SPEED
                            
                            # Apply raycast-based obstacle avoidance
                            desired_vx, desired_vy = self._apply_obstacle_avoidance(world, desired_vx, desired_vy)
                            
                            # Smooth steering
                            self.steering_force_x = desired_vx - self.vx
                            self.steering_force_y = desired_vy - self.vy
                            
                            # Clamp steering force
                            steer_mag = math.sqrt(self.steering_force_x**2 + self.steering_force_y**2)
                            if steer_mag > self.max_force:
                                self.steering_force_x = (self.steering_force_x / steer_mag) * self.max_force
                                self.steering_force_y = (self.steering_force_y / steer_mag) * self.max_force
                            
                            # Apply steering
                            self.vx += self.steering_force_x
                            self.vy += self.steering_force_y
                            
                            # Clamp velocity
                            vel_mag = math.sqrt(self.vx**2 + self.vy**2)
                            if vel_mag > EYE_SPEED * 1.2:
                                self.vx = (self.vx / vel_mag) * EYE_SPEED * 1.2
                                self.vy = (self.vy / vel_mag) * EYE_SPEED * 1.2
                            
                            self.facing_right = self.vx > 0
                        else:
                            self._advance_waypoint()
                else:
                    # Fallback: direct movement when no path available
                    # STILL apply obstacle avoidance even in fallback!
                    if distance > 0:
                        # Use move_dx/move_dy which is already correctly oriented (flee or chase)
                        desired_vx = (move_dx / distance) * EYE_SPEED
                        desired_vy = (move_dy / distance) * EYE_SPEED
                        desired_vx, desired_vy = self._apply_obstacle_avoidance(world, desired_vx, desired_vy)
                        self.vx = desired_vx
                        self.vy = desired_vy
                        self.facing_right = self.vx > 0
            else:
                self.vx = 0
                self.vy = 0
                self.stuck_timer = 0
                self.path = []

        # Apply friction when knockback is active
        if self.knockback_timer > 0:
            self.vx *= 0.9
            self.vy *= 0.9

        # Move horizontally with collision
        self.x += self.vx
        self._resolve_horizontal_collisions(world)

        # Move vertically with collision
        self.y += self.vy
        self._resolve_vertical_collisions(world)

        # Update tail segments (follow behind the eye)
        tail_base_x = self.x + self.width / 2
        tail_base_y = self.y + self.height / 2
        for i in range(len(self.tail_segments)):
            # Each segment follows behind with wave motion
            offset_x = -12 * (i + 1) if self.facing_right else 12 * (i + 1)
            offset_y = math.sin(self.tail_wave + i * 0.8) * (4 + i * 2)
            self.tail_segments[i] = (tail_base_x + offset_x, tail_base_y + offset_y)

        # Check if can attack player
        if self.attack_cooldown <= 0 and self.rect.colliderect(player_rect):
            self.attack_cooldown = 1.0
            # Return damage and collision info for special handling
            return (EYE_DAMAGE, self.vx, self.vy, self.x + self.width / 2)
        return None

    def _resolve_horizontal_collisions(self, world):
        """Resolve collisions on the horizontal axis."""
        rect = self.rect
        left_tile = rect.left // TILE_SIZE
        right_tile = rect.right // TILE_SIZE
        top_tile = rect.top // TILE_SIZE
        bottom_tile = rect.bottom // TILE_SIZE

        for ty in range(top_tile, bottom_tile + 1):
            for tx in range(left_tile, right_tile + 1):
                bt = world.get_block(tx, ty)
                # Skip tree blocks (WOOD, LEAVES) - flying eye can pass through like player
                if bt in (BlockType.WOOD, BlockType.LEAVES):
                    continue
                if world.is_solid(tx, ty):
                    block_rect = pygame.Rect(
                        tx * TILE_SIZE,
                        ty * TILE_SIZE,
                        TILE_SIZE,
                        TILE_SIZE
                    )
                    if rect.colliderect(block_rect):
                        if self.vx > 0:
                            self.x = block_rect.left - self.width
                            self.vx = 0
                        elif self.vx < 0:
                            self.x = block_rect.right
                            self.vx = 0
                        rect = self.rect

    def _resolve_vertical_collisions(self, world):
        """Resolve collisions on the vertical axis."""
        rect = self.rect
        left_tile = rect.left // TILE_SIZE
        right_tile = rect.right // TILE_SIZE
        top_tile = rect.top // TILE_SIZE
        bottom_tile = rect.bottom // TILE_SIZE

        for ty in range(top_tile, bottom_tile + 1):
            for tx in range(left_tile, right_tile + 1):
                bt = world.get_block(tx, ty)
                # Skip tree blocks (WOOD, LEAVES) - flying eye can pass through like player
                if bt in (BlockType.WOOD, BlockType.LEAVES):
                    continue
                if world.is_solid(tx, ty):
                    block_rect = pygame.Rect(
                        tx * TILE_SIZE,
                        ty * TILE_SIZE,
                        TILE_SIZE,
                        TILE_SIZE
                    )
                    if rect.colliderect(block_rect):
                        if self.vy > 0:
                            self.y = block_rect.top - self.height
                            self.vy = 0
                        elif self.vy < 0:
                            self.y = block_rect.bottom
                            self.vy = 0
                        rect = self.rect

    def draw(self, surface, camera):
        """Draw the flying eye with nerves/tail."""
        screen_rect = camera.apply(self.rect)
        zoom = camera.zoom
        
        def scale(val):
            return max(1, int(val * zoom))
        
        # Float offset
        float_offset = math.sin(self.float_animation) * scale(3)
        
        # Colors
        if self.hit_flash > 0:
            eye_color = (255, 100, 100)
            nerve_color = (200, 80, 80)
        else:
            eye_color = (220, 200, 180)  # Pale eye color
            nerve_color = (180, 80, 100)  # Reddish nerves
        
        center_x = screen_rect.centerx
        center_y = screen_rect.centery + float_offset
        
        # Draw tail/nerves first (behind the eye)
        nerve_width = scale(4)
        for i, (seg_x, seg_y) in enumerate(self.tail_segments):
            screen_seg_x, screen_seg_y = camera.world_to_screen(seg_x, seg_y)
            # Nerves get thinner towards the end
            width = max(1, nerve_width - scale(i))
            # Nerve color fades
            alpha = 255 - i * 40
            nerve_c = (
                min(255, nerve_color[0] + i * 10),
                max(0, nerve_color[1] - i * 10),
                max(0, nerve_color[2] - i * 10)
            )
            if i == 0:
                # Draw from eye to first segment
                pygame.draw.line(surface, nerve_c,
                               (center_x, center_y),
                               (int(screen_seg_x), int(screen_seg_y)), width)
            else:
                # Draw from previous segment to this one
                prev_x, prev_y = camera.world_to_screen(
                    self.tail_segments[i-1][0], self.tail_segments[i-1][1])
                pygame.draw.line(surface, nerve_c,
                               (int(prev_x), int(prev_y)),
                               (int(screen_seg_x), int(screen_seg_y)), width)
        
        # Draw main eye body (large oval)
        eye_radius_x = scale(self.width // 2)
        eye_radius_y = scale(self.height // 2 - 4)
        pulse = math.sin(self.pulse_animation) * scale(2)
        
        # Eye white (main body)
        eye_rect = pygame.Rect(
            center_x - eye_radius_x - pulse,
            center_y - eye_radius_y - pulse,
            (eye_radius_x + pulse) * 2,
            (eye_radius_y + pulse) * 2
        )
        pygame.draw.ellipse(surface, eye_color, eye_rect)
        
        # Eye outline
        pygame.draw.ellipse(surface, (100, 80, 80), eye_rect, scale(2))
        
        # Iris (colored part)
        iris_radius = scale(12)
        iris_color = (100, 50, 120)  # Purple iris
        iris_rect = pygame.Rect(
            center_x - iris_radius,
            center_y - iris_radius,
            iris_radius * 2,
            iris_radius * 2
        )
        pygame.draw.ellipse(surface, iris_color, iris_rect)
        
        # Pupil (black center) - follows movement direction
        pupil_offset_x = scale(3) if self.vx > 0 else -scale(3) if self.vx < 0 else 0
        pupil_offset_y = scale(2) if self.vy > 0 else -scale(2) if self.vy < 0 else 0
        pupil_radius = scale(6)
        pygame.draw.circle(surface, (20, 20, 30),
                          (int(center_x + pupil_offset_x), int(center_y + pupil_offset_y)),
                          pupil_radius)
        
        # Eye highlight
        highlight_offset = scale(4)
        highlight_radius = scale(3)
        pygame.draw.circle(surface, (255, 255, 255),
                          (int(center_x - highlight_offset), int(center_y - highlight_offset)),
                          highlight_radius)
        
        # Veins in eye (red lines)
        for i in range(4):
            angle = i * math.pi / 2 + self.float_animation * 0.5
            vein_len = scale(8)
            vein_x = center_x + math.cos(angle) * (eye_radius_x - scale(4))
            vein_y = center_y + math.sin(angle) * (eye_radius_y - scale(4))
            vein_end_x = vein_x + math.cos(angle) * vein_len
            vein_end_y = vein_y + math.sin(angle) * vein_len
            pygame.draw.line(surface, (180, 80, 80),
                           (int(vein_x), int(vein_y)),
                           (int(vein_end_x), int(vein_end_y)), max(1, scale(1)))
        
        # Health bar
        if self.health < self.max_health:
            bar_width = screen_rect.width
            bar_height = scale(4)
            bar_y = screen_rect.y - bar_height - scale(2)
            
            pygame.draw.rect(surface, (50, 50, 50),
                           (screen_rect.x, bar_y, bar_width, bar_height))
            
            health_width = int(bar_width * (self.health / self.max_health))
            pygame.draw.rect(surface, (255, 50, 50),
                           (screen_rect.x, bar_y, health_width, bar_height))


class EnemyManager:
    """Manages all enemies in the game."""

    def __init__(self):
        self.enemies = []  # Zombies
        self.flying_eyes = []  # Flying eyes
        self.zombie_spawn_timer = 0.0
        self.eye_spawn_timer = 0.0

    def spawn_zombie(self, player_x, player_y, world):
        """Spawn a zombie at a valid position near the player (not inside blocks)."""
        # Try up to 10 times to find a valid spawn position
        for _ in range(10):
            # Random angle around player
            angle = random.uniform(0, 2 * math.pi)
            distance = random.uniform(300, 500)
            
            spawn_x = player_x + math.cos(angle) * distance
            spawn_y = player_y + math.sin(angle) * distance
            
            # Convert to tile coordinates
            tile_x = int(spawn_x // TILE_SIZE)
            tile_y = int(spawn_y // TILE_SIZE)
            
            # Find ground level at spawn position
            for check_y in range(max(0, tile_y - 20), min(world.height, tile_y + 20)):
                if world.is_solid(tile_x, check_y):
                    # Found ground, spawn above it
                    spawn_y = (check_y - 1) * TILE_SIZE - ZOMBIE_HEIGHT
                    
                    # Check if spawn position is valid (not inside block)
                    spawn_tile_y = int(spawn_y // TILE_SIZE)
                    if spawn_tile_y >= 0 and spawn_tile_y < world.height:
                        spawn_block = world.get_block(tile_x, spawn_tile_y)
                        if spawn_block not in (BlockType.WOOD, BlockType.LEAVES, BlockType.AIR) and world.is_solid(tile_x, spawn_tile_y):
                            # Try a different position
                            break
                    
                    zombie = Zombie(spawn_x, spawn_y)
                    self.enemies.append(zombie)
                    return True
        
        return False

    def spawn_flying_eye(self, player_x, player_y, world):
        """Spawn a flying eye at a valid position near the player (not inside blocks)."""
        # Try up to 10 times to find a valid spawn position
        for _ in range(10):
            # Random angle around player
            angle = random.uniform(0, 2 * math.pi)
            distance = random.uniform(250, 400)
            
            spawn_x = player_x + math.cos(angle) * distance
            spawn_y = player_y + random.uniform(-100, 50)
            
            # Check if spawn position is inside a solid block (excluding trees)
            tile_x = int(spawn_x // TILE_SIZE)
            tile_y = int(spawn_y // TILE_SIZE)
            
            block = world.get_block(tile_x, tile_y)
            # Skip if spawning inside solid block (not trees)
            if block not in (BlockType.WOOD, BlockType.LEAVES, BlockType.AIR) and world.is_solid(tile_x, tile_y):
                continue
            
            # Also check nearby tiles to ensure there's room
            is_valid = True
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    check_x = tile_x + dx
                    check_y = tile_y + dy
                    if 0 <= check_x < world.width and 0 <= check_y < world.height:
                        check_block = world.get_block(check_x, check_y)
                        if check_block not in (BlockType.WOOD, BlockType.LEAVES, BlockType.AIR) and world.is_solid(check_x, check_y):
                            # If majority of nearby tiles are solid, skip
                            is_valid = False
                            break
                if not is_valid:
                    break
            
            if is_valid:
                eye = FlyingEye(spawn_x, spawn_y)
                self.flying_eyes.append(eye)
                return True
        
        # Fallback: spawn above player in air
        spawn_x = player_x + random.uniform(-100, 100)
        spawn_y = player_y - 100  # Well above player
        eye = FlyingEye(spawn_x, spawn_y)
        self.flying_eyes.append(eye)
        return True

    def update(self, dt, world, player_rect, is_night):
        """Update all enemies and handle spawning."""
        # Spawn zombies at night
        if is_night and len(self.enemies) < ZOMBIE_MAX_COUNT:
            self.zombie_spawn_timer += dt
            if self.zombie_spawn_timer >= ZOMBIE_SPAWN_INTERVAL:
                self.zombie_spawn_timer = 0.0
                self.spawn_zombie(player_rect.centerx, player_rect.centery, world)
        
        # Spawn flying eyes at night
        if is_night and len(self.flying_eyes) < EYE_MAX_COUNT:
            self.eye_spawn_timer += dt
            if self.eye_spawn_timer >= EYE_SPAWN_INTERVAL:
                self.eye_spawn_timer = 0.0
                self.spawn_flying_eye(player_rect.centerx, player_rect.centery, world)
        
        # Update all zombies
        damage_to_player = 0
        player_drag = None  # (drag_distance, direction_x, direction_y)
        dead_enemies = []
        
        for zombie in self.enemies:
            damage = zombie.update(dt, world, player_rect, is_night)
            if damage > 0:
                damage_to_player += damage
            
            if zombie.health <= 0:
                dead_enemies.append(zombie)
        
        # Remove dead zombies
        for zombie in dead_enemies:
            self.enemies.remove(zombie)
        
        # Update all flying eyes
        dead_eyes = []
        for eye in self.flying_eyes:
            result = eye.update(dt, world, player_rect, is_night)
            if result is not None:
                # Flying eye hit player - return special collision info
                damage, eye_vx, eye_vy, eye_x = result
                damage_to_player += damage
                
                # Calculate knockback direction: opposite of eye's movement direction
                # (player should be pushed away from the eye)
                speed = math.sqrt(eye_vx * eye_vx + eye_vy * eye_vy)
                if speed > 0:
                    # Opposite of eye's direction = push player away
                    drag_dir_x = -eye_vx / speed
                    drag_dir_y = -eye_vy / speed
                else:
                    # Default: push player away from eye position
                    drag_dir_x = -1 if player_rect.centerx > eye_x else 1
                    drag_dir_y = 0
                
                player_drag = (EYE_PLAYER_DRAG_DISTANCE, drag_dir_x, drag_dir_y)
                
                # Apply knockback to eye in opposite direction (away from player)
                eye.apply_knockback(player_rect.centerx, EYE_KNOCKBACK_FORCE)
                # Also apply vertical knockback
                eye.vy = -drag_dir_y * EYE_KNOCKBACK_FORCE  # This is now away from player vertically
            
            if eye.health <= 0:
                dead_eyes.append(eye)
        
        # Remove dead flying eyes
        for eye in dead_eyes:
            self.flying_eyes.remove(eye)
        
        return damage_to_player, player_drag

    def check_sword_hit(self, player_rect, swing_angle, swing_range):
        """Check if sword swing hits any enemy."""
        hit_enemies = []
        player_center = (player_rect.centerx, player_rect.centery)
        
        # Check zombies
        for zombie in self.enemies:
            zombie_center = (zombie.x + zombie.width / 2, zombie.y + zombie.height / 2)
            
            # Calculate distance
            dx = zombie_center[0] - player_center[0]
            dy = zombie_center[1] - player_center[1]
            distance = math.sqrt(dx * dx + dy * dy)
            
            if distance <= swing_range:
                hit_enemies.append(zombie)
        
        # Check flying eyes
        for eye in self.flying_eyes:
            eye_center = (eye.x + eye.width / 2, eye.y + eye.height / 2)
            
            # Calculate distance
            dx = eye_center[0] - player_center[0]
            dy = eye_center[1] - player_center[1]
            distance = math.sqrt(dx * dx + dy * dy)
            
            if distance <= swing_range:
                hit_enemies.append(eye)
        
        return hit_enemies

    def draw(self, surface, camera):
        """Draw all enemies."""
        for enemy in self.enemies:
            enemy.draw(surface, camera)
        for eye in self.flying_eyes:
            eye.draw(surface, camera)
