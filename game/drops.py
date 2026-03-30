"""Dropped items system - items that drop from broken blocks."""

import pygame
import math
import random
from game.constants import (
    DROP_SIZE, DROP_COLLECT_RANGE, DROP_BOB_SPEED, DROP_BOB_AMOUNT,
    TILE_SIZE, YELLOW, GRAVITY, MAX_FALL_SPEED, LEAVES_COLOR,
    SCREEN_WIDTH
)
from game.blocks import get_item_color, get_item_name, is_block_solid, is_tool, ToolType, BlockType


class Particle:
    """A small particle for visual effects like leaf debris."""

    def __init__(self, x, y, color, size=4, lifetime=1.0):
        self.x = float(x)
        self.y = float(y)
        self.color = color
        self.size = size
        self.lifetime = lifetime
        self.max_lifetime = lifetime
        
        # Random initial velocity
        self.vx = random.uniform(-3, 3)
        self.vy = random.uniform(-5, -1)
        
        # Random rotation effect
        self.rotation = random.uniform(0, 360)
        self.rotation_speed = random.uniform(-180, 180)

    def update(self, dt):
        """Update particle physics."""
        self.lifetime -= dt
        
        # Apply gravity
        self.vy += GRAVITY * 1.5
        
        # Move
        self.x += self.vx
        self.y += self.vy
        
        # Air resistance
        self.vx *= 0.98
        
        # Rotate
        self.rotation += self.rotation_speed * dt
        
        return self.lifetime > 0

    def draw(self, surface, camera):
        """Draw the particle."""
        screen_x, screen_y = camera.world_to_screen(self.x, self.y)
        scaled_size = max(1, int(self.size * camera.zoom))
        
        # Fade out as lifetime decreases
        alpha = int(255 * (self.lifetime / self.max_lifetime))
        
        # Draw a small rectangle
        rect = pygame.Rect(
            int(screen_x - scaled_size // 2),
            int(screen_y - scaled_size // 2),
            scaled_size,
            scaled_size
        )
        
        # Create a surface with alpha for fading
        color = (*self.color[:3], alpha) if len(self.color) == 3 else self.color
        pygame.draw.rect(surface, self.color, rect)


class ParticleManager:
    """Manages particle effects."""

    def __init__(self):
        self.particles = []

    def spawn_leaf_particles(self, x, y, count=5):
        """Spawn leaf particles at a position."""
        for _ in range(count):
            # Slight random offset
            px = x + random.uniform(-TILE_SIZE/2, TILE_SIZE/2)
            py = y + random.uniform(-TILE_SIZE/2, TILE_SIZE/2)
            
            # Slight color variation for leaves
            color_var = random.randint(-20, 20)
            color = (
                max(0, min(255, LEAVES_COLOR[0] + color_var)),
                max(0, min(255, LEAVES_COLOR[1] + color_var)),
                max(0, min(255, LEAVES_COLOR[2] + color_var))
            )
            
            particle = Particle(
                px, py, color,
                size=random.randint(3, 6),
                lifetime=random.uniform(0.5, 1.5)
            )
            self.particles.append(particle)

    def spawn_star_trail(self, x, y):
        """Spawn trail particles for falling stars."""
        # Spawn a few small yellow particles
        for _ in range(2):
            px = x + random.uniform(-5, 5)
            py = y + random.uniform(-5, 5)
            
            # Yellow/gold color variation
            color = (
                random.randint(240, 255),
                random.randint(220, 255),
                random.randint(50, 150)
            )
            
            particle = Particle(
                px, py, color,
                size=random.randint(2, 4),
                lifetime=random.uniform(0.3, 0.8)
            )
            # Override velocity for star trail effect
            particle.vx = random.uniform(-1, 1)
            particle.vy = random.uniform(-2, 0)
            self.particles.append(particle)

    def spawn_star_impact(self, x, y):
        """Spawn impact particles when a star hits the ground."""
        # Spawn burst of yellow particles
        for _ in range(15):
            px = x + random.uniform(-10, 10)
            py = y + random.uniform(-5, 5)
            
            # Bright yellow/gold colors
            color = (
                random.randint(240, 255),
                random.randint(200, 255),
                random.randint(50, 150)
            )
            
            particle = Particle(
                px, py, color,
                size=random.randint(3, 6),
                lifetime=random.uniform(0.5, 1.5)
            )
            # Explosive velocity outward
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(2, 6)
            particle.vx = math.cos(angle) * speed
            particle.vy = math.sin(angle) * speed - 3  # Initial upward burst
            self.particles.append(particle)

    def update(self, dt):
        """Update all particles and remove dead ones."""
        self.particles = [p for p in self.particles if p.update(dt)]

    def draw(self, surface, camera):
        """Draw all particles."""
        for particle in self.particles:
            particle.draw(surface, camera)


class DroppedItem:
    """A dropped item that can be collected by the player."""

    def __init__(self, x, y, block_type, falling=True, vx=0.0, vy=0.0):
        self.x = float(x)
        self.y = float(y)
        self.block_type = block_type
        self.size = DROP_SIZE
        self.collected = False
        self.time = 0.0  # For bobbing animation
        self.base_y = y
        self.hovered = False  # For hover effect
        
        # Physics for falling and throwing
        self.vx = float(vx)  # Horizontal velocity
        self.vy = float(vy)  # Vertical velocity
        self.falling = falling  # Whether the drop should fall
        self.on_ground = False  # Whether the drop has landed
        self.thrown = vx != 0 or vy != 0  # Was this item thrown?
        self.pickup_delay = 0.5 if self.thrown else 0.0  # Can't pick up thrown items immediately

    @property
    def rect(self):
        """Return the item's pygame.Rect for collision/collection."""
        return pygame.Rect(
            int(self.x - self.size // 2),
            int(self.y - self.size // 2),
            self.size,
            self.size
        )

    def update(self, dt, world=None):
        """Update the dropped item (falling and bobbing animation)."""
        # Decrease pickup delay
        if self.pickup_delay > 0:
            self.pickup_delay -= dt
        
        # Always check if ground below is still solid
        if world is not None and self.on_ground:
            tile_x = int(self.x // TILE_SIZE)
            tile_y = int((self.y + self.size // 2) // TILE_SIZE)
            if not world.is_solid(tile_x, tile_y):
                # Ground was removed, start falling again
                self.on_ground = False
                self.falling = True
                self.vy = 0.0
        
        # Apply gravity if falling and not on ground
        if self.falling and not self.on_ground:
            self.vy += GRAVITY * 2  # Slightly faster gravity for drops
            if self.vy > MAX_FALL_SPEED:
                self.vy = MAX_FALL_SPEED
            
            # Move down
            self.y += self.vy
            
            # Move horizontally if thrown
            if self.thrown and self.vx != 0:
                self.x += self.vx
                self.vx *= 0.98  # Air resistance
                if abs(self.vx) < 0.1:
                    self.vx = 0
            
            # Check for ground collision if world is provided
            if world is not None:
                self._check_ground_collision(world)
        else:
            # Bobbing animation when on ground
            self.time += dt * DROP_BOB_SPEED
            self.y = self.base_y + math.sin(self.time) * DROP_BOB_AMOUNT

    def _check_ground_collision(self, world):
        """Check if the drop has hit the ground."""
        # Check the tile below the drop
        tile_x = int(self.x // TILE_SIZE)
        tile_y = int((self.y + self.size // 2) // TILE_SIZE)
        
        if world.is_solid(tile_x, tile_y):
            # Land on the ground
            self.y = tile_y * TILE_SIZE - self.size // 2
            self.vy = 0
            self.vx = 0  # Stop horizontal movement
            self.on_ground = True
            self.base_y = self.y
            self.falling = False
            self.thrown = False

    def can_collect(self, player_rect):
        """Check if player is close enough to collect this item."""
        # Can't collect if pickup delay is active
        if self.pickup_delay > 0:
            return False
        
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

        # Get item rect for hover border
        rect = pygame.Rect(
            int(screen_x - scaled_size // 2),
            int(screen_y - scaled_size // 2),
            int(scaled_size),
            int(scaled_size)
        )
        
        # Skip generic rectangle for stars - they have custom rendering
        if self.block_type not in (BlockType.YELLOW_STAR, BlockType.BLUE_STAR):
            # Draw the item (smaller version of block or tool)
            color = get_item_color(self.block_type)
            pygame.draw.rect(surface, color, rect)
        
        # Draw tool-specific details if it's a tool
        if is_tool(self.block_type):
            # Draw a simple tool icon indicator
            center_x = int(screen_x)
            center_y = int(screen_y)
            handle_color = (80, 50, 20)
            if self.block_type == ToolType.SWORD:
                # Draw sword blade
                pygame.draw.line(surface, (200, 200, 220), 
                               (center_x, center_y - int(scaled_size//3)),
                               (center_x, center_y + int(scaled_size//3)), 
                               max(1, int(scaled_size//4)))
            elif self.block_type == ToolType.PICKAXE:
                # Draw pickaxe head
                pygame.draw.line(surface, (150, 150, 160),
                               (center_x - int(scaled_size//3), center_y - int(scaled_size//4)),
                               (center_x + int(scaled_size//3), center_y - int(scaled_size//4)),
                               max(1, int(scaled_size//5)))
            elif self.block_type == ToolType.AXE:
                # Draw axe head
                pygame.draw.polygon(surface, (100, 70, 40), [
                    (center_x + int(scaled_size//4), center_y - int(scaled_size//3)),
                    (center_x + int(scaled_size//3), center_y),
                    (center_x + int(scaled_size//4), center_y + int(scaled_size//4)),
                ])
            elif self.block_type == ToolType.SHOVEL:
                # Draw shovel head
                pygame.draw.ellipse(surface, (150, 150, 160),
                                  (center_x - int(scaled_size//5), center_y - int(scaled_size//3),
                                   int(scaled_size//2.5), int(scaled_size//2)))
            elif self.block_type == ToolType.BOW:
                # Draw bow shape
                pygame.draw.arc(surface, (139, 90, 43),
                              (center_x - int(scaled_size//3), center_y - int(scaled_size//2),
                               int(scaled_size*2//3), int(scaled_size)),
                              -1.5, 1.5, max(1, int(scaled_size//6)))
        
        # Draw platform-specific details
        elif self.block_type == BlockType.PLATFORM:
            # Draw as thin horizontal plank
            platform_color = (160, 120, 60)
            platform_height = max(2, int(scaled_size // 4))
            platform_rect = pygame.Rect(
                int(screen_x - scaled_size // 2),
                int(screen_y - scaled_size // 2),
                int(scaled_size),
                platform_height
            )
            pygame.draw.rect(surface, platform_color, platform_rect)
            # Wood grain
            grain_color = (130, 90, 40)
            pygame.draw.line(surface, grain_color,
                           (int(screen_x - scaled_size // 2), int(screen_y - scaled_size // 2 + platform_height // 2)),
                           (int(screen_x + scaled_size // 2), int(screen_y - scaled_size // 2 + platform_height // 2)), 1)

        # Draw star-specific visuals
        elif self.block_type == BlockType.YELLOW_STAR:
            # Draw 5-pointed yellow star shape
            center_x = int(screen_x)
            center_y = int(screen_y)
            star_size = max(6, int(8 * camera.zoom))
            
            # Glow effect (soft yellow circles behind)
            for radius in [14, 10, 6]:
                alpha = int(80 * (radius / 14))
                glow_surface = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
                pygame.draw.circle(glow_surface, (255, 255, 100, alpha), (radius, radius), radius)
                surface.blit(glow_surface, (center_x - radius, center_y - radius))
            
            # Draw 5-pointed star polygon
            def get_star_points(cx, cy, outer_r, inner_r, rotation=0):
                points = []
                for i in range(10):
                    angle = math.pi / 2 + i * math.pi / 5 + rotation  # Start at top
                    radius = outer_r if i % 2 == 0 else inner_r
                    px = cx + math.cos(angle) * radius
                    py = cy - math.sin(angle) * radius
                    points.append((px, py))
                return points
            
            # Main yellow star
            star_points = get_star_points(center_x, center_y, star_size, star_size // 2)
            pygame.draw.polygon(surface, (255, 220, 50), star_points)  # Bright yellow fill
            pygame.draw.polygon(surface, (255, 180, 0), star_points, max(1, int(camera.zoom)))  # Orange border
            
            # Sparkle effect
            sparkle_time = pygame.time.get_ticks() / 500
            for i in range(3):
                angle = sparkle_time + i * 2.094  # 120 degrees apart
                dist = star_size + 2
                sx = center_x + int(math.cos(angle) * dist)
                sy = center_y + int(math.sin(angle) * dist)
                pygame.draw.circle(surface, (255, 255, 200), (sx, sy), max(1, int(1.5 * camera.zoom)))

        elif self.block_type == BlockType.BLUE_STAR:
            # Draw 5-pointed blue star shape
            center_x = int(screen_x)
            center_y = int(screen_y)
            star_size = max(6, int(8 * camera.zoom))
            
            # Glow effect (soft blue circles behind)
            for radius in [14, 10, 6]:
                alpha = int(80 * (radius / 14))
                glow_surface = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
                pygame.draw.circle(glow_surface, (100, 150, 255, alpha), (radius, radius), radius)
                surface.blit(glow_surface, (center_x - radius, center_y - radius))
            
            # Draw 5-pointed star polygon
            def get_star_points(cx, cy, outer_r, inner_r, rotation=0):
                points = []
                for i in range(10):
                    angle = math.pi / 2 + i * math.pi / 5 + rotation  # Start at top
                    radius = outer_r if i % 2 == 0 else inner_r
                    px = cx + math.cos(angle) * radius
                    py = cy - math.sin(angle) * radius
                    points.append((px, py))
                return points
            
            # Main blue star
            star_points = get_star_points(center_x, center_y, star_size, star_size // 2, rotation=0.314)  # Slight rotation
            pygame.draw.polygon(surface, (100, 150, 255), star_points)  # Bright blue fill
            pygame.draw.polygon(surface, (60, 100, 200), star_points, max(1, int(camera.zoom)))  # Darker blue border
            
            # Sparkle effect
            sparkle_time = pygame.time.get_ticks() / 500
            for i in range(3):
                angle = sparkle_time + i * 2.094 + 1.047  # Offset from yellow star
                dist = star_size + 2
                sx = center_x + int(math.cos(angle) * dist)
                sy = center_y + int(math.sin(angle) * dist)
                pygame.draw.circle(surface, (180, 210, 255), (sx, sy), max(1, int(1.5 * camera.zoom)))

        # Draw yellow border if hovered
        if self.hovered:
            pygame.draw.rect(surface, YELLOW, rect, 2)
        else:
            pygame.draw.rect(surface, (0, 0, 0), rect, 1)


class DropManager:
    """Manages all dropped items in the world."""

    def __init__(self):
        self.drops = []

    def spawn_drop(self, x, y, block_type, falling=True):
        """Spawn a new dropped item at the given position."""
        # Center the drop in the tile
        drop = DroppedItem(
            x * TILE_SIZE + TILE_SIZE // 2,
            y * TILE_SIZE + TILE_SIZE // 2,
            block_type,
            falling=falling
        )
        self.drops.append(drop)
    
    def spawn_thrown_drop(self, x, y, block_type, vx, vy):
        """Spawn a thrown item with initial velocity."""
        drop = DroppedItem(
            x,
            y,
            block_type,
            falling=True,
            vx=vx,
            vy=vy
        )
        self.drops.append(drop)

    def update(self, dt, player_rect, world=None):
        """Update all drops and check for collection."""
        collected = []
        for drop in self.drops:
            drop.update(dt, world)
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


class Arrow:
    """A projectile arrow shot from a bow."""
    
    def __init__(self, x, y, vx, vy, damage=1):
        self.x = float(x)
        self.y = float(y)
        self.vx = float(vx)
        self.vy = float(vy)
        self.damage = damage
        self.active = True
        self.stuck = False
        self.lifetime = 10.0  # Seconds before disappearing
        self.gravity = 0.15  # Less gravity than normal
    
    @property
    def rect(self):
        """Return a small rect for collision detection."""
        return pygame.Rect(int(self.x - 4), int(self.y - 4), 8, 8)
    
    def update(self, dt, world, enemies):
        """Update arrow physics and check for hits."""
        if not self.active:
            return None
        
        if self.stuck:
            self.lifetime -= dt
            if self.lifetime <= 0:
                self.active = False
            return None
        
        # Apply gravity
        self.vy += self.gravity
        
        # Move
        self.x += self.vx
        self.y += self.vy
        
        # Check for enemy hits
        arrow_rect = self.rect
        for enemy in enemies:
            if arrow_rect.colliderect(enemy.rect):
                enemy.take_damage(self.damage)
                enemy.apply_knockback(self.x)
                self.active = False
                return enemy
        
        # Check for world collision
        tile_x = int(self.x // TILE_SIZE)
        tile_y = int(self.y // TILE_SIZE)
        if world.is_solid(tile_x, tile_y):
            self.stuck = True
            self.vx = 0
            self.vy = 0
        
        return None
    
    def draw(self, surface, camera):
        """Draw the arrow."""
        screen_x, screen_y = camera.world_to_screen(self.x, self.y)
        
        # Calculate angle from velocity
        if self.vx != 0 or self.vy != 0:
            angle = math.atan2(self.vy, self.vx)
        else:
            angle = 0
        
        # Draw arrow as a small line with tip
        length = 12 * camera.zoom
        tip_x = screen_x + math.cos(angle) * length
        tip_y = screen_y + math.sin(angle) * length
        
        # Arrow shaft
        shaft_color = (139, 90, 43)  # Brown wood
        pygame.draw.line(surface, shaft_color, 
                        (int(screen_x - math.cos(angle) * length * 0.5), 
                         int(screen_y - math.sin(angle) * length * 0.5)),
                        (int(tip_x), int(tip_y)), 
                        max(1, int(2 * camera.zoom)))
        
        # Arrow head
        head_color = (150, 150, 150)  # Gray metal
        pygame.draw.circle(surface, head_color, (int(tip_x), int(tip_y)), max(1, int(3 * camera.zoom)))


class ArrowManager:
    """Manages all arrows in flight."""
    
    def __init__(self):
        self.arrows = []
    
    def spawn_arrow(self, x, y, vx, vy, damage=1):
        """Spawn a new arrow."""
        arrow = Arrow(x, y, vx, vy, damage)
        self.arrows.append(arrow)
    
    def update(self, dt, world, enemies):
        """Update all arrows."""
        for arrow in self.arrows:
            arrow.update(dt, world, enemies)
        
        # Remove inactive arrows
        self.arrows = [a for a in self.arrows if a.active]
    
    def draw(self, surface, camera):
        """Draw all arrows."""
        for arrow in self.arrows:
            arrow.draw(surface, camera)


class FallingStar:
    """A falling yellow star that falls from the sky at night."""
    
    def __init__(self, x, y, target_x, target_y):
        self.x = float(x)
        self.y = float(y)
        self.target_x = float(target_x)
        self.target_y = float(target_y)
        self.active = True
        self.landed = False
        self.vanishing = False
        self.vanish_timer = 0.0
        self.vanish_duration = 1.0  # Seconds to vanish
        
        # Calculate velocity toward target
        dx = target_x - x
        dy = target_y - y
        dist = math.sqrt(dx * dx + dy * dy)
        speed = 8.0  # Falling speed
        if dist > 0:
            self.vx = (dx / dist) * speed
            self.vy = (dy / dist) * speed
        else:
            self.vx = 0
            self.vy = speed
        
        # Trail particles
        self.trail_timer = 0.0
        self.trail_interval = 0.05
        
        # Sparkle effect
        self.sparkle_timer = 0.0
        self.sparkle_offset = random.uniform(0, math.pi * 2)
    
    def update(self, dt, world, particle_manager):
        """Update falling star position and check for ground collision."""
        if not self.active:
            return None
        
        # Handle vanishing at day time
        if self.vanishing:
            self.vanish_timer -= dt
            if self.vanish_timer <= 0:
                self.active = False
            return None
        
        if self.landed:
            return None
        
        # Move
        self.x += self.vx
        self.y += self.vy
        
        # Spawn trail particles
        self.trail_timer += dt
        if self.trail_timer >= self.trail_interval:
            self.trail_timer = 0
            if particle_manager:
                particle_manager.spawn_star_trail(self.x, self.y)
        
        # Check for ground collision
        tile_x = int(self.x // TILE_SIZE)
        tile_y = int(self.y // TILE_SIZE)
        
        if world.is_solid(tile_x, tile_y) or self.y >= self.target_y:
            # Landed - convert to dropped item
            self.landed = True
            self.active = False
            # Spawn impact particles
            if particle_manager:
                particle_manager.spawn_star_impact(self.x, self.y)
            return (tile_x, tile_y)  # Return landing position
        
        return None
    
    def start_vanishing(self):
        """Start the vanishing effect when day comes."""
        if not self.vanishing and (self.active or self.landed):
            self.vanishing = True
            self.vanish_timer = self.vanish_duration
    
    def draw(self, surface, camera, is_day=False):
        """Draw the falling star with glow and sparkle effects."""
        if not self.active and not self.vanishing:
            return
        
        screen_x, screen_y = camera.world_to_screen(self.x, self.y)
        
        # Calculate alpha for vanishing effect
        alpha = 255
        if self.vanishing:
            alpha = int(255 * (self.vanish_timer / self.vanish_duration))
        
        # Draw glow (multiple circles for glow effect)
        glow_sizes = [20, 15, 10, 6]
        glow_alphas = [0.2, 0.4, 0.6, 0.8]
        for size, glow_alpha in zip(glow_sizes, glow_alphas):
            glow_surface = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
            final_alpha = int(255 * glow_alpha * (alpha / 255))
            pygame.draw.circle(glow_surface, (255, 255, 100, final_alpha), 
                             (size, size), size)
            surface.blit(glow_surface, 
                        (int(screen_x - size), int(screen_y - size)))
        
        # Draw main star (bright yellow)
        star_size = max(2, int(4 * camera.zoom))
        pygame.draw.circle(surface, (255, 255, 150), 
                          (int(screen_x), int(screen_y)), star_size)
        
        # Draw sparkle points
        self.sparkle_timer += 0.1
        for i in range(4):
            angle = self.sparkle_timer + self.sparkle_offset + (i * math.pi / 2)
            sparkle_dist = star_size + 3
            sparkle_x = screen_x + math.cos(angle) * sparkle_dist
            sparkle_y = screen_y + math.sin(angle) * sparkle_dist
            sparkle_size = max(1, int(2 * camera.zoom))
            pygame.draw.circle(surface, (255, 255, 200), 
                              (int(sparkle_x), int(sparkle_y)), sparkle_size)


class StarDropManager:
    """Manages falling stars at night time."""
    
    def __init__(self):
        self.falling_stars = []
        self.spawn_timer = 0.0
        self.spawn_interval = 3.0  # Spawn a star every 3 seconds at night
        self.max_stars = 5  # Maximum falling stars at once
    
    def update(self, dt, world, camera, is_night, particle_manager, drop_manager):
        """Update falling stars and spawn new ones at night."""
        # Spawn new stars at night
        if is_night:
            self.spawn_timer += dt
            if self.spawn_timer >= self.spawn_interval and len(self.falling_stars) < self.max_stars:
                self.spawn_timer = 0
                self._spawn_star(world, camera)
        else:
            # Day time - make all stars vanish
            for star in self.falling_stars:
                star.start_vanishing()
        
        # Update existing stars
        landed_stars = []
        for star in self.falling_stars:
            result = star.update(dt, world, particle_manager)
            if result:  # Star landed
                tile_x, tile_y = result
                landed_stars.append((tile_x, tile_y))
        
        # Remove inactive stars
        self.falling_stars = [s for s in self.falling_stars if s.active or s.vanishing]
        
        # Convert landed stars to dropped items
        # Spawn at tile_y - 1 so the star sits ON TOP of the ground, not inside it
        for tile_x, tile_y in landed_stars:
            drop_manager.spawn_drop(tile_x, tile_y - 1, BlockType.YELLOW_STAR, falling=False)
        
        return landed_stars
    
    def _spawn_star(self, world, camera):
        """Spawn a new falling star from the sky."""
        # Pick a random x position within visible area
        visible_left = int(camera.x // TILE_SIZE)
        visible_right = int((camera.x + SCREEN_WIDTH / camera.zoom) // TILE_SIZE)
        
        spawn_tile_x = random.randint(visible_left, visible_right)
        spawn_y = camera.y - 100  # Start above visible area
        
        # Target a spot on the ground
        target_tile_x = spawn_tile_x + random.randint(-5, 5)
        target_y = self._find_ground_y(world, target_tile_x, spawn_y)
        
        star = FallingStar(
            spawn_tile_x * TILE_SIZE + TILE_SIZE // 2,
            spawn_y,
            target_tile_x * TILE_SIZE + TILE_SIZE // 2,
            target_y
        )
        self.falling_stars.append(star)
    
    def _find_ground_y(self, world, tile_x, start_y):
        """Find the y coordinate of the ground at a given x position."""
        tile_y = int(start_y // TILE_SIZE)
        while tile_y < world.height:
            if world.is_solid(tile_x, tile_y):
                return tile_y * TILE_SIZE
            tile_y += 1
        return world.height * TILE_SIZE
    
    def draw(self, surface, camera, is_night):
        """Draw all falling stars."""
        for star in self.falling_stars:
            star.draw(surface, camera, is_night)
