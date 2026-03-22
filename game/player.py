"""Player class - a simple box that can move and jump."""

import pygame
from game.constants import (
    PLAYER_WIDTH, PLAYER_HEIGHT, PLAYER_COLOR,
    PLAYER_SPEED, PLAYER_JUMP_VELOCITY, GRAVITY, MAX_FALL_SPEED,
    TILE_SIZE
)
from game.blocks import is_block_solid


class Player:
    """Player represented as a box with movement and jumping (2 blocks wide, 3 blocks tall)."""

    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)
        self.vx = 0.0
        self.vy = 0.0
        self.width = PLAYER_WIDTH
        self.height = PLAYER_HEIGHT
        self.on_ground = False
        self.color = PLAYER_COLOR

    @property
    def rect(self):
        """Return the player's pygame.Rect for collisions."""
        return pygame.Rect(int(self.x), int(self.y), self.width, self.height)

    @property
    def center(self):
        """Return the player's center point."""
        return (
            int(self.x + self.width / 2),
            int(self.y + self.height / 2)
        )

    def handle_input(self, keys):
        """Handle keyboard input for movement."""
        self.vx = 0

        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.vx = -PLAYER_SPEED
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.vx = PLAYER_SPEED

        # Jump
        if (keys[pygame.K_SPACE] or keys[pygame.K_UP] or keys[pygame.K_w]) and self.on_ground:
            self.vy = PLAYER_JUMP_VELOCITY
            self.on_ground = False

    def update(self, world):
        """Update player physics and collisions with world."""
        # Apply gravity
        self.vy += GRAVITY
        if self.vy > MAX_FALL_SPEED:
            self.vy = MAX_FALL_SPEED

        # Horizontal movement with collision
        self.x += self.vx
        self._resolve_horizontal_collisions(world)

        # Vertical movement with collision
        self.y += self.vy
        self._resolve_vertical_collisions(world)

    def _resolve_horizontal_collisions(self, world):
        """Resolve collisions on the horizontal axis."""
        rect = self.rect
        # Check tiles overlapping the player's rect
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
                            # Moving right, push left
                            self.x = block_rect.left - self.width
                            self.vx = 0
                        elif self.vx < 0:
                            # Moving left, push right
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
                            # Falling, land on top
                            self.y = block_rect.top - self.height
                            self.vy = 0
                            self.on_ground = True
                        elif self.vy < 0:
                            # Jumping, hit head
                            self.y = block_rect.bottom
                            self.vy = 0
                        rect = self.rect

    def draw(self, surface, camera):
        """Draw the player as a box."""
        screen_rect = camera.apply(self.rect)
        pygame.draw.rect(surface, self.color, screen_rect)
        # Draw a small highlight on top for detail (scaled with zoom)
        highlight_height = max(4, int(10 * camera.zoom))
        highlight = pygame.Rect(screen_rect.x, screen_rect.y, screen_rect.width, highlight_height)
        pygame.draw.rect(surface, (100, 150, 255), highlight)
        # Draw face area (scaled with zoom)
        face_margin = max(4, int(8 * camera.zoom))
        face_top = max(6, int(12 * camera.zoom))
        face_height = max(8, int(20 * camera.zoom))
        face = pygame.Rect(
            screen_rect.x + face_margin,
            screen_rect.y + face_top,
            screen_rect.width - face_margin * 2,
            face_height
        )
        pygame.draw.rect(surface, (200, 180, 160), face)
        # Draw eyes (scaled with zoom)
        eye_size = max(2, int(6 * camera.zoom))
        eye_offset_x = max(7, int(14 * camera.zoom))
        eye_offset_y = max(9, int(18 * camera.zoom))
        pygame.draw.rect(surface, (0, 0, 0),
                         (screen_rect.x + eye_offset_x, screen_rect.y + eye_offset_y, eye_size, eye_size))
        pygame.draw.rect(surface, (0, 0, 0),
                         (screen_rect.x + screen_rect.width - eye_offset_x - eye_size,
                          screen_rect.y + eye_offset_y, eye_size, eye_size))
