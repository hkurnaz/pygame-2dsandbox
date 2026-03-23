"""Enemy system - zombies that spawn at night."""

import pygame
import math
import random
from game.constants import (
    ZOMBIE_WIDTH, ZOMBIE_HEIGHT, ZOMBIE_SPEED, ZOMBIE_HEALTH,
    ZOMBIE_DAMAGE, TILE_SIZE, GRAVITY, MAX_FALL_SPEED
)
from game.blocks import is_block_solid


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
                            # Try to jump over obstacle
                            if self.on_ground:
                                self.vy = -8
                            self.vx = 0
                        elif self.vx < 0:
                            self.x = block_rect.right
                            if self.on_ground:
                                self.vy = -8
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


class EnemyManager:
    """Manages all enemies in the game."""

    def __init__(self):
        self.enemies = []
        self.spawn_timer = 0.0

    def spawn_zombie(self, player_x, player_y, world):
        """Spawn a zombie at a valid position near the player."""
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
                zombie = Zombie(spawn_x, spawn_y)
                self.enemies.append(zombie)
                return True
        
        return False

    def update(self, dt, world, player_rect, is_night):
        """Update all enemies and handle spawning."""
        # Spawn zombies at night
        if is_night and len(self.enemies) < 10:
            self.spawn_timer += dt
            if self.spawn_timer >= 5.0:
                self.spawn_timer = 0.0
                self.spawn_zombie(player_rect.centerx, player_rect.centery, world)
        
        # Update all zombies
        damage_to_player = 0
        dead_enemies = []
        
        for zombie in self.enemies:
            damage = zombie.update(dt, world, player_rect, is_night)
            if damage > 0:
                damage_to_player += damage
            
            if zombie.health <= 0:
                dead_enemies.append(zombie)
        
        # Remove dead enemies
        for zombie in dead_enemies:
            self.enemies.remove(zombie)
        
        return damage_to_player

    def check_sword_hit(self, player_rect, swing_angle, swing_range):
        """Check if sword swing hits any zombie."""
        hit_enemies = []
        player_center = (player_rect.centerx, player_rect.centery)
        
        for zombie in self.enemies:
            zombie_center = (zombie.x + zombie.width / 2, zombie.y + zombie.height / 2)
            
            # Calculate distance
            dx = zombie_center[0] - player_center[0]
            dy = zombie_center[1] - player_center[1]
            distance = math.sqrt(dx * dx + dy * dy)
            
            if distance <= swing_range:
                # Check if zombie is in front of player (based on facing direction)
                # Simplified: just check if within range
                hit_enemies.append(zombie)
        
        return hit_enemies

    def draw(self, surface, camera):
        """Draw all enemies."""
        for enemy in self.enemies:
            enemy.draw(surface, camera)
