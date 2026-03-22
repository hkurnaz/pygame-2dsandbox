"""Camera system for following the player."""

from game.constants import SCREEN_WIDTH, SCREEN_HEIGHT, TILE_SIZE, CAMERA_ZOOM


class Camera:
    """Camera that follows a target (usually the player) with zoom support."""

    def __init__(self):
        self.x = 0
        self.y = 0
        self.target_x = 0
        self.target_y = 0
        self.zoom = CAMERA_ZOOM

    def follow(self, target_rect):
        """Set camera to follow a target rect (centered)."""
        # Center camera on target, accounting for zoom
        self.target_x = target_rect.centerx - (SCREEN_WIDTH // 2) / self.zoom
        self.target_y = target_rect.centery - (SCREEN_HEIGHT // 2) / self.zoom

    def update(self, smooth=0.1):
        """Update camera position with optional smoothing."""
        # Smooth interpolation
        self.x += (self.target_x - self.x) * smooth
        self.y += (self.target_y - self.y) * smooth

        # Clamp camera to world bounds
        # Allow some freedom but not too far
        self.x = max(-SCREEN_WIDTH // 2, self.x)
        self.y = max(-SCREEN_HEIGHT // 2, self.y)

    def apply(self, rect):
        """Apply camera offset and zoom to a rect (for rendering)."""
        # Scale and offset
        scaled_x = (rect.x - self.x) * self.zoom
        scaled_y = (rect.y - self.y) * self.zoom
        scaled_width = rect.width * self.zoom
        scaled_height = rect.height * self.zoom
        return pygame.Rect(int(scaled_x), int(scaled_y), int(scaled_width), int(scaled_height))

    def apply_point(self, x, y):
        """Apply camera offset and zoom to a point."""
        return (x - self.x) * self.zoom, (y - self.y) * self.zoom

    def world_to_screen(self, wx, wy):
        """Convert world coordinates to screen coordinates."""
        return (wx - self.x) * self.zoom, (wy - self.y) * self.zoom

    def screen_to_world(self, sx, sy):
        """Convert screen coordinates to world coordinates."""
        return sx / self.zoom + self.x, sy / self.zoom + self.y

    def get_visible_tiles(self):
        """Get the range of tiles currently visible."""
        # Account for zoom in visible area
        left = int((self.x - 50) // TILE_SIZE)
        right = int((self.x + SCREEN_WIDTH / self.zoom + 50) // TILE_SIZE) + 1
        top = int((self.y - 50) // TILE_SIZE)
        bottom = int((self.y + SCREEN_HEIGHT / self.zoom + 50) // TILE_SIZE) + 1
        return left, right, top, bottom


import pygame  # Needed for Rect
