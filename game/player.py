"""Player class - a simple box that can move and jump."""

import pygame
from game.constants import (
    PLAYER_WIDTH, PLAYER_HEIGHT, PLAYER_COLOR,
    PLAYER_SPEED, PLAYER_JUMP_VELOCITY, GRAVITY, MAX_FALL_SPEED,
    TILE_SIZE, PLATFORM_THICKNESS
)
from game.blocks import is_block_solid, is_block_platform, BlockType


class Player:
    """Player represented as a box with movement and jumping (1.5 blocks wide, 3 blocks tall)."""

    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)
        self.vx = 0.0
        self.vy = 0.0
        self.width = PLAYER_WIDTH
        self.height = PLAYER_HEIGHT
        self.on_ground = False
        self.color = PLAYER_COLOR
        self.facing_right = True  # Player facing direction
        self.dropping_through_platform = False  # Track if player is dropping through a platform
        self.drop_platform_y = 0  # Y position of platform we're dropping through
        self.current_platform_tiles = set()  # Track which platform tiles we're on
        
        # UFO mode (debug/creative mode)
        self.ufo_mode = False
        self.ufo_speed = PLAYER_SPEED * 2  # Faster in UFO mode

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
        if self.ufo_mode:
            # UFO mode: free flight in all directions
            self.vx = 0
            self.vy = 0
            
            if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                self.vx = -self.ufo_speed
                self.facing_right = False
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                self.vx = self.ufo_speed
                self.facing_right = True
            if keys[pygame.K_UP] or keys[pygame.K_w]:
                self.vy = -self.ufo_speed
            if keys[pygame.K_DOWN] or keys[pygame.K_s]:
                self.vy = self.ufo_speed
        else:
            # Normal mode
            self.vx = 0

            if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                self.vx = -PLAYER_SPEED
                self.facing_right = False
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                self.vx = PLAYER_SPEED
                self.facing_right = True

            # Jump
            if (keys[pygame.K_SPACE] or keys[pygame.K_UP] or keys[pygame.K_w]) and self.on_ground:
                self.vy = PLAYER_JUMP_VELOCITY
                self.on_ground = False
                # When jumping, clear platform tracking
                self.current_platform_tiles.clear()

            # Drop through platform (S key or Down arrow)
            if keys[pygame.K_DOWN] or keys[pygame.K_s]:
                if self.on_ground and self.current_platform_tiles:
                    self.dropping_through_platform = True
                    self.on_ground = False
                    self.vy = 3  # Small downward velocity to start dropping
                    # Store the Y position of the platform we're dropping through
                    # Get the platform tile Y from current_platform_tiles
                    if self.current_platform_tiles:
                        tile_pos = next(iter(self.current_platform_tiles))
                        self.drop_platform_y = tile_pos[1] * TILE_SIZE
                    self.current_platform_tiles.clear()

    def update(self, world):
        """Update player physics and collisions with world."""
        if self.ufo_mode:
            # UFO mode: no gravity, free movement, no collisions
            self.x += self.vx
            self.y += self.vy
            # Clamp to world bounds
            self.x = max(0, min(self.x, world.width * TILE_SIZE - self.width))
            self.y = max(0, min(self.y, world.height * TILE_SIZE - self.height))
        else:
            # Normal mode: apply gravity
            self.vy += GRAVITY
            if self.vy > MAX_FALL_SPEED:
                self.vy = MAX_FALL_SPEED

            # Horizontal movement with collision
            self.x += self.vx
            self._resolve_horizontal_collisions(world)

            # Vertical movement with collision
            self.y += self.vy
            self._resolve_vertical_collisions(world)

            # Reset dropping state when player has passed through the platform
            # (player's feet are below the platform's bottom)
            if self.dropping_through_platform:
                player_bottom = self.y + self.height
                if player_bottom > self.drop_platform_y + PLATFORM_THICKNESS + 5:
                    self.dropping_through_platform = False
    
    def toggle_ufo_mode(self):
        """Toggle UFO mode on/off."""
        self.ufo_mode = not self.ufo_mode
        if self.ufo_mode:
            self.vy = 0  # Reset vertical velocity when entering UFO mode
        return self.ufo_mode

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
                bt = world.get_block(tx, ty)
                # Skip tree blocks (WOOD, LEAVES) - player can walk through
                if bt in (BlockType.WOOD, BlockType.LEAVES):
                    continue
                # Skip platforms - they only affect vertical collision from above
                if bt == BlockType.PLATFORM:
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
        self.current_platform_tiles.clear()

        for ty in range(top_tile, bottom_tile + 1):
            for tx in range(left_tile, right_tile + 1):
                bt = world.get_block(tx, ty)
                # Skip tree blocks (WOOD, LEAVES) - player can walk through
                if bt in (BlockType.WOOD, BlockType.LEAVES):
                    continue
                
                # Handle platforms specially
                if bt == BlockType.PLATFORM:
                    # Platform is thin at top of tile
                    platform_top = ty * TILE_SIZE
                    platform_bottom = platform_top + PLATFORM_THICKNESS
                    platform_rect = pygame.Rect(
                        tx * TILE_SIZE,
                        platform_top,
                        TILE_SIZE,
                        PLATFORM_THICKNESS
                    )
                    
                    # Only collide when falling and not dropping through
                    if self.vy > 0 and not self.dropping_through_platform:
                        # Check if player's feet are at or just above the platform
                        player_bottom = self.y + self.height
                        # Player must be above the platform bottom to land
                        if player_bottom >= platform_top and player_bottom <= platform_bottom + self.vy:
                            # Land on platform
                            self.y = platform_top - self.height
                            self.vy = 0
                            self.on_ground = True
                            self.current_platform_tiles.add((tx, ty))
                            rect = self.rect
                    # Allow jumping through from below (vy < 0) - no collision
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
        """Draw the player as a thinner, more human-like character."""
        screen_rect = camera.apply(self.rect)
        zoom = camera.zoom
        
        # Helper function to scale dimensions
        def scale(val):
            return max(1, int(val * zoom))
        
        # The visual character is slightly thinner than collision box
        # Collision box is 48x96, visual will be ~32x96 (centered)
        visual_width = scale(32)
        visual_offset = (screen_rect.width - visual_width) // 2
        visual_x = screen_rect.x + visual_offset
        
        # Flip offset for facing left
        flip_offset = 0 if self.facing_right else visual_width
        
        # Proportions for a more human-like character
        # Head: ~24 pixels
        # Body: ~32 pixels
        # Legs: ~40 pixels
        head_height = scale(24)
        body_height = scale(32)
        leg_height = scale(40)
        
        # Colors
        skin_color = (255, 220, 185)  # Skin tone
        shirt_color = (70, 130, 180)  # Steel blue shirt
        shirt_dark = (50, 100, 150)   # Darker blue for shading
        pants_color = (60, 60, 90)    # Dark blue-gray pants
        pants_dark = (40, 40, 60)     # Darker pants
        hair_color = (60, 40, 25)     # Dark brown hair
        shoe_color = (50, 35, 20)     # Dark brown shoes
        
        # Helper to flip x coordinate if facing left
        def flip_x(x):
            if self.facing_right:
                return x
            return visual_x + visual_width - (x - visual_x)
        
        # === DRAW LEGS ===
        leg_y = screen_rect.y + head_height + body_height
        leg_gap = scale(2)
        leg_width = (visual_width - leg_gap) // 2
        
        # Left leg (or right leg if flipped)
        left_leg_x = visual_x if self.facing_right else visual_x + leg_width + leg_gap
        left_leg = pygame.Rect(
            left_leg_x,
            leg_y,
            leg_width,
            leg_height - scale(6)
        )
        pygame.draw.rect(surface, pants_color, left_leg)
        # Shading
        shade_x = left_leg.right - scale(4) if self.facing_right else left_leg.x
        pygame.draw.rect(surface, pants_dark, 
                        (shade_x, left_leg.y, scale(4), left_leg.height))
        
        # Right leg (or left leg if flipped)
        right_leg_x = visual_x + leg_width + leg_gap if self.facing_right else visual_x
        right_leg = pygame.Rect(
            right_leg_x,
            leg_y,
            leg_width,
            leg_height - scale(6)
        )
        pygame.draw.rect(surface, pants_color, right_leg)
        # Shading
        shade_x = right_leg.right - scale(4) if self.facing_right else right_leg.x
        pygame.draw.rect(surface, pants_dark,
                        (shade_x, right_leg.y, scale(4), right_leg.height))
        
        # Shoes
        shoe_height = scale(6)
        shoe_extend = scale(2)
        left_shoe_x = visual_x - shoe_extend if self.facing_right else visual_x + leg_width + leg_gap - shoe_extend
        left_shoe = pygame.Rect(
            left_shoe_x,
            screen_rect.bottom - shoe_height,
            leg_width + shoe_extend * 2,
            shoe_height
        )
        pygame.draw.rect(surface, shoe_color, left_shoe)
        
        right_shoe_x = visual_x + leg_width + leg_gap - shoe_extend if self.facing_right else visual_x - shoe_extend
        right_shoe = pygame.Rect(
            right_shoe_x,
            screen_rect.bottom - shoe_height,
            leg_width + shoe_extend * 2,
            shoe_height
        )
        pygame.draw.rect(surface, shoe_color, right_shoe)
        
        # === DRAW BODY/TORSO ===
        body_rect = pygame.Rect(
            visual_x,
            screen_rect.y + head_height,
            visual_width,
            body_height
        )
        pygame.draw.rect(surface, shirt_color, body_rect)
        
        # Body shading (sides) - flip based on direction
        left_shade_x = body_rect.x if not self.facing_right else body_rect.right - scale(4)
        right_shade_x = body_rect.right - scale(4) if not self.facing_right else body_rect.x
        pygame.draw.rect(surface, shirt_dark,
                        (left_shade_x, body_rect.y, scale(4), body_rect.height))
        
        # Collar/neckline
        collar_points = [
            (body_rect.centerx, body_rect.y),
            (body_rect.centerx - scale(8), body_rect.y + scale(6)),
            (body_rect.centerx + scale(8), body_rect.y + scale(6)),
        ]
        pygame.draw.polygon(surface, shirt_dark, collar_points)
        
        # === DRAW ARMS ===
        arm_width = scale(8)
        arm_height = body_height - scale(2)
        arm_extend = scale(4)  # How far arms extend from body
        
        # Front arm (the one facing the camera)
        front_arm_x = visual_x + visual_width - arm_extend if self.facing_right else visual_x - arm_width + arm_extend
        front_arm = pygame.Rect(
            front_arm_x,
            screen_rect.y + head_height + scale(2),
            arm_width,
            arm_height
        )
        pygame.draw.rect(surface, shirt_color, front_arm)
        shade_x = front_arm.x if not self.facing_right else front_arm.right - scale(3)
        pygame.draw.rect(surface, shirt_dark, (shade_x, front_arm.y, scale(3), front_arm.height))
        
        # Front hand
        hand_width = scale(6)
        hand_height = scale(6)
        front_hand = pygame.Rect(
            front_arm.x + (arm_width - hand_width) // 2,
            front_arm.bottom - hand_height // 2,
            hand_width,
            hand_height
        )
        pygame.draw.ellipse(surface, skin_color, front_hand)
        
        # Back arm (behind body)
        back_arm_x = visual_x - arm_width + arm_extend if self.facing_right else visual_x + visual_width - arm_extend
        back_arm = pygame.Rect(
            back_arm_x,
            screen_rect.y + head_height + scale(2),
            arm_width,
            arm_height
        )
        pygame.draw.rect(surface, shirt_color, back_arm)
        shade_x = back_arm.x if self.facing_right else back_arm.right - scale(3)
        pygame.draw.rect(surface, shirt_dark, (shade_x, back_arm.y, scale(3), back_arm.height))
        
        # Back hand
        back_hand = pygame.Rect(
            back_arm.x + (arm_width - hand_width) // 2,
            back_arm.bottom - hand_height // 2,
            hand_width,
            hand_height
        )
        pygame.draw.ellipse(surface, skin_color, back_hand)
        
        # === DRAW HEAD ===
        head_width = scale(24)
        head_offset = (visual_width - head_width) // 2
        head_rect = pygame.Rect(
            visual_x + head_offset,
            screen_rect.y,
            head_width,
            head_height
        )
        pygame.draw.ellipse(surface, skin_color, head_rect)
        
        # Hair (top and sides)
        hair_height = scale(10)
        hair_rect = pygame.Rect(
            head_rect.x + scale(2),
            head_rect.y,
            head_rect.width - scale(4),
            hair_height
        )
        pygame.draw.ellipse(surface, hair_color, hair_rect)
        
        # Side hair / bangs - flip based on direction
        bang_width = scale(4)
        bang_height = scale(8)
        # Bang on the side facing away from camera
        bang_x = head_rect.x + scale(1) if self.facing_right else head_rect.right - bang_width - scale(1)
        side_bang = pygame.Rect(
            bang_x,
            head_rect.y + scale(6),
            bang_width,
            bang_height
        )
        pygame.draw.rect(surface, hair_color, side_bang)
        
        # === DRAW FACE ===
        # Offset face slightly based on direction
        face_offset = scale(2) if self.facing_right else -scale(2)
        
        # Eyes
        eye_width = scale(4)
        eye_height = scale(3)
        eye_y = head_rect.y + scale(10)
        eye_spacing = scale(4)
        
        # Left eye (from character's perspective, so right when flipped)
        left_eye_x = head_rect.centerx - eye_spacing - eye_width // 2 + face_offset
        left_eye = pygame.Rect(
            left_eye_x,
            eye_y,
            eye_width,
            eye_height
        )
        pygame.draw.ellipse(surface, (255, 255, 255), left_eye)
        
        # Left pupil
        pupil_size = scale(2)
        pupil_offset = scale(1) if self.facing_right else -scale(1)
        left_pupil = pygame.Rect(
            left_eye.centerx - pupil_size // 2 + pupil_offset,
            left_eye.centery - pupil_size // 2,
            pupil_size,
            pupil_size
        )
        pygame.draw.ellipse(surface, (0, 0, 0), left_pupil)
        
        # Right eye
        right_eye_x = head_rect.centerx + eye_spacing - eye_width // 2 + face_offset
        right_eye = pygame.Rect(
            right_eye_x,
            eye_y,
            eye_width,
            eye_height
        )
        pygame.draw.ellipse(surface, (255, 255, 255), right_eye)
        
        # Right pupil
        right_pupil = pygame.Rect(
            right_eye.centerx - pupil_size // 2 + pupil_offset,
            right_eye.centery - pupil_size // 2,
            pupil_size,
            pupil_size
        )
        pygame.draw.ellipse(surface, (0, 0, 0), right_pupil)
        
        # Nose (small line) - offset based on direction
        nose_x = head_rect.centerx + (scale(3) if self.facing_right else -scale(3))
        nose_y = eye_y + eye_height + scale(2)
        pygame.draw.line(surface, (220, 180, 150),
                        (nose_x, nose_y),
                        (nose_x, nose_y + scale(3)), scale(2))
        
        # Mouth
        mouth_width = scale(4)
        mouth_height = scale(2)
        mouth_rect = pygame.Rect(
            head_rect.centerx - mouth_width // 2 + face_offset,
            head_rect.y + head_height - scale(6),
            mouth_width,
            mouth_height
        )
        pygame.draw.ellipse(surface, (180, 100, 100), mouth_rect)
