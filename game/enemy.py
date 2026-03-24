"""Enemy system - zombies that spawn at night."""

import pygame
import math
import random
from game.constants import (
    ZOMBIE_WIDTH, ZOMBIE_HEIGHT, ZOMBIE_SPEED, ZOMBIE_HEALTH,
    ZOMBIE_DAMAGE, TILE_SIZE, GRAVITY, MAX_FALL_SPEED,
    EYE_WIDTH, EYE_HEIGHT, EYE_SPEED, EYE_HEALTH, EYE_DAMAGE,
    EYE_KNOCKBACK_FORCE, EYE_PLAYER_DRAG_DISTANCE,
    ZOMBIE_SPAWN_INTERVAL, ZOMBIE_MAX_COUNT,
    EYE_SPAWN_INTERVAL, EYE_MAX_COUNT
)
from game.blocks import is_block_solid, BlockType


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
    """A flying eye enemy that floats and chases the player at night."""

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
        # Pathfinding - track if stuck
        self.stuck_timer = 0.0
        self.last_x = x
        self.last_y = y
        self.avoidance_direction = 0  # -1 = up, 1 = down

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

    def update(self, dt, world, player_rect, is_night=True):
        """Update flying eye physics and AI."""
        # Update timers
        if self.hit_flash > 0:
            self.hit_flash -= dt
        if self.attack_cooldown > 0:
            self.attack_cooldown -= dt
        if self.knockback_timer > 0:
            self.knockback_timer -= dt

        # Animations
        self.float_animation += dt * 3
        self.pulse_animation += dt * 4
        self.tail_wave += dt * 8

        # Check if stuck (not moving much)
        moved_distance = math.sqrt((self.x - self.last_x)**2 + (self.y - self.last_y)**2)
        self.last_x = self.x
        self.last_y = self.y
        
        if moved_distance < 1.0:
            self.stuck_timer += dt
        else:
            self.stuck_timer = 0

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
            
            if distance > 10:
                # During daytime: run AWAY from player
                if not is_night:
                    dx = -dx
                    dy = -dy
                
                # Normalize and apply speed
                target_vx = (dx / distance) * EYE_SPEED
                target_vy = (dy / distance) * EYE_SPEED
                
                # Direction we want to move horizontally
                h_dir = 1 if dx > 0 else -1
                
                # Check if path ahead is clear at current level and above
                path_clear_at_level = self._check_path_clear(world, h_dir, 0, distance_tiles=4)
                path_clear_above = self._check_path_clear(world, h_dir, -1, distance_tiles=4)
                path_clear_2above = self._check_path_clear(world, h_dir, -2, distance_tiles=4)
                path_clear_3above = self._check_path_clear(world, h_dir, -3, distance_tiles=4)
                
                # If stuck or blocked, navigate properly over obstacles
                if self.stuck_timer > 0.3 or not path_clear_at_level:
                    # Find obstacle info
                    obstacle_height, clear_above, height_needed = self._find_obstacle_height(world, h_dir)
                    
                    # Check if we can go up
                    can_go_up = self._check_path_clear(world, 0, -1, distance_tiles=3)
                    
                    # Navigation strategy:
                    # We need to fly UP and OVER the obstacle
                    # Key insight: always move horizontally while climbing, don't stop
                    
                    if clear_above:
                        # There's clear space above the wall - we can go over
                        # Calculate how many tiles up we need to be to clear
                        # height_needed is negative when we need to go UP
                        tiles_to_climb = -height_needed if height_needed < 0 else 0
                        
                        if tiles_to_climb > 0 or not path_clear_3above:
                            # We need to climb AND move forward simultaneously
                            # Move up strongly while still moving horizontally
                            target_vy = -EYE_SPEED * 1.5  # Strong upward
                            target_vx = (dx / distance) * EYE_SPEED * 0.6  # Reduced but still moving forward
                            self.avoidance_direction = -1
                        elif not path_clear_at_level and path_clear_above:
                            # We're at wall level, climb one tile
                            target_vy = -EYE_SPEED * 1.5
                            target_vx = (dx / distance) * EYE_SPEED * 0.5
                            self.avoidance_direction = -1
                        elif not path_clear_above and path_clear_2above:
                            # Need to climb 2 tiles
                            target_vy = -EYE_SPEED * 1.5
                            target_vx = (dx / distance) * EYE_SPEED * 0.5
                            self.avoidance_direction = -1
                        else:
                            # We should be clear now - fly forward
                            target_vy = 0
                            target_vx = (dx / distance) * EYE_SPEED * 1.1
                            self.avoidance_direction = 0
                    elif can_go_up:
                        # Try going up to find a route
                        target_vy = -EYE_SPEED * 1.5
                        target_vx = (dx / distance) * EYE_SPEED * 0.4
                        self.avoidance_direction = -1
                    else:
                        # Try going down
                        can_go_down = self._check_path_clear(world, 0, 1, distance_tiles=3)
                        if can_go_down:
                            target_vy = EYE_SPEED * 1.3
                            target_vx *= 0.5
                            self.avoidance_direction = 1
                        else:
                            # Back up slightly
                            target_vx *= -0.3
                            target_vy = (dy / distance) * EYE_SPEED * 0.5
                else:
                    # Clear path, reset avoidance
                    self.avoidance_direction = 0
                
                self.vx = target_vx
                self.vy = target_vy
                self.facing_right = dx > 0
            else:
                self.vx = 0
                self.vy = 0
                self.stuck_timer = 0

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
