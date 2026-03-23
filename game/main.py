"""Main entry point for MyArea game.

Run with: python3 -m game.main
"""

import pygame
import sys
import math
import random
from game.constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT, FPS, SKY_BLUE, WHITE, YELLOW,
    TILE_SIZE, BREAK_RANGE, DAY_DURATION, DAY_SKY_COLOR, NIGHT_SKY_COLOR,
    SWORD_SWING_DURATION, SWORD_SWING_RANGE, SWORD_DAMAGE, THROW_FORCE, THROW_UPWARD_ANGLE
)

# Game states
GAME_STATE_MENU = "menu"
GAME_STATE_PLAYING = "playing"
GAME_STATE_PAUSED = "paused"
from game.player import Player
from game.world import World
from game.camera import Camera
from game.drops import DropManager, ParticleManager, ArrowManager
from game.inventory import Inventory
from game.enemy import EnemyManager
from game.blocks import get_break_time, get_break_time_with_tool, get_block_name, get_item_name, is_block_breakable, BlockType, ToolType, ItemType, is_tool


class Game:
    """Main game class."""

    def __init__(self):
        pygame.init()
        pygame.display.set_caption("MyArea")
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()
        self.running = True
        
        # Game state
        self.game_state = GAME_STATE_MENU

        # Game objects (created but not used until playing)
        self.world = None
        self.player = None
        self.camera = None

        # Systems
        self.drop_manager = None
        self.particle_manager = None
        self.inventory = None
        self.enemy_manager = None
        
        # Breaking state
        self.breaking_tile = None  # (tile_x, tile_y)
        self.break_progress = 0.0  # 0.0 to 1.0
        self.break_time_required = 0.0  # seconds
        self.mouse_held = False
        
        # Day/Night cycle
        self.time_of_day = 0.0  # 0 to DAY_DURATION
        self.is_night = False
        
        # Sword swing
        self.sword_swing_timer = 0.0
        self.sword_swing_active = False
        self.sword_swing_angle = 0.0
        
        # Player health
        self.player_health = 10
        self.player_max_health = 10
        self.player_damage_cooldown = 0.0
        
        # Bow charging
        self.bow_charge_start = 0.0  # Time when bow started charging
        self.bow_charging = False
        self.bow_max_charge = 2.0  # 2 seconds for full charge
        
        # UI font
        self.title_font = pygame.font.Font(None, 72)
        self.button_font = pygame.font.Font(None, 48)
        self.menu_font = pygame.font.Font(None, 36)
        
        # Button rects for menu/pause
        self.play_button_rect = None
        self.quit_button_rect = None
        self.resume_button_rect = None

    def _start_game(self):
        """Initialize and start a new game."""
        self.world = World()
        self.world.generate()
        self.player = Player(0, 0)
        spawn_x, spawn_y = self.world.get_player_spawn()
        self.player.x = float(spawn_x)
        self.player.y = float(spawn_y)
        self.camera = Camera()

        self.drop_manager = DropManager()
        self.particle_manager = ParticleManager()
        self.arrow_manager = ArrowManager()
        self.inventory = Inventory()
        self.enemy_manager = EnemyManager()
        
        # Initialize starting tools in slots 1-5
        self.inventory.hotbar[0] = (ToolType.SWORD, 1)
        self.inventory.hotbar[1] = (ToolType.PICKAXE, 1)
        self.inventory.hotbar[2] = (ToolType.AXE, 1)
        self.inventory.hotbar[3] = (ToolType.SHOVEL, 1)
        self.inventory.hotbar[4] = (ToolType.BOW, 1)
        
        # Give player starting arrows (in storage slot)
        self.inventory.storage[0][0] = (ItemType.ARROW, 10)

        self.game_state = GAME_STATE_PLAYING

    def handle_events(self):
        """Handle pygame events."""
        mouse_pos = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            
            # Handle MENU state
            elif self.game_state == GAME_STATE_MENU:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self.play_button_rect and self.play_button_rect.collidepoint(mouse_pos):
                        self._start_game()
                    elif self.quit_button_rect and self.quit_button_rect.collidepoint(mouse_pos):
                        self.running = False
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self.running = False
            
            # Handle PAUSED state
            elif self.game_state == GAME_STATE_PAUSED:
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self.game_state = GAME_STATE_PLAYING
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self.resume_button_rect and self.resume_button_rect.collidepoint(mouse_pos):
                        self.game_state = GAME_STATE_PLAYING
                    elif self.quit_button_rect and self.quit_button_rect.collidepoint(mouse_pos):
                        self.running = False
            
            # Handle PLAYING state
            elif self.game_state == GAME_STATE_PLAYING:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        # Close inventory if open, otherwise pause
                        if self.inventory.is_open:
                            self.inventory.is_open = False
                            self.inventory.cancel_drag()
                        else:
                            self.game_state = GAME_STATE_PAUSED
                    elif event.key == pygame.K_TAB:
                        # Toggle inventory
                        self.inventory.is_open = not self.inventory.is_open
                        self.inventory.cancel_drag()
                    # Number keys 1-9 for inventory selection
                    elif pygame.K_1 <= event.key <= pygame.K_9:
                        self.inventory.select_slot(event.key - pygame.K_1)
                    # N key to toggle day/night (hidden feature)
                    elif event.key == pygame.K_n:
                        self.is_night = not self.is_night
                    # Q key to drop item
                    elif event.key == pygame.K_q:
                        self._drop_selected_item()
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:  # Left click
                        self.mouse_held = True
                        # If inventory is open, handle inventory click
                        if self.inventory.is_open:
                            self.inventory.handle_click(*mouse_pos, 1)
                        else:
                            # Check hotbar click
                            hotbar_slot = self.inventory.check_hotbar_hover(*mouse_pos)
                            if hotbar_slot >= 0:
                                self.inventory.handle_click(*mouse_pos, 1)
                            else:
                                # Check if sword is selected
                                selected_item = self.inventory.get_selected_item()
                                if selected_item is not None and selected_item[0] == ToolType.SWORD:
                                    # Swing sword
                                    self._swing_sword()
                                else:
                                    # Try to break block
                                    self._start_breaking(mouse_pos)
                    elif event.button == 3:  # Right click - place block or charge bow
                        if not self.inventory.is_open:
                            selected_item = self.inventory.get_selected_item()
                            if selected_item is not None and selected_item[0] == ToolType.BOW:
                                # Start bow charging
                                self.bow_charging = True
                                self.bow_charge_start = pygame.time.get_ticks() / 1000.0
                            else:
                                self._try_place_block(mouse_pos)
                elif event.type == pygame.MOUSEBUTTONUP:
                    if event.button == 1:
                        self.mouse_held = False
                        # Only stop breaking if not in inventory
                        if not self.inventory.is_open:
                            self._stop_breaking()
                    elif event.button == 3:  # Release right click - shoot bow
                        if self.bow_charging:
                            self._shoot_bow()
                            self.bow_charging = False
                elif event.type == pygame.MOUSEWHEEL:
                    # Mouse wheel for inventory selection
                    # event.y is 1 for scroll up, -1 for scroll down
                    self.inventory.scroll_selection(-event.y)

        # Update hover states for drops (world coordinates) - only in playing
        if self.game_state == GAME_STATE_PLAYING and self.camera and self.drop_manager:
            world_x, world_y = self.camera.screen_to_world(*mouse_pos)
            self.drop_manager.check_hover(world_x, world_y)

    def _get_tile_at_mouse(self, mouse_pos):
        """Convert mouse position to tile coordinates (accounting for zoom)."""
        world_x, world_y = self.camera.screen_to_world(*mouse_pos)
        tile_x = int(world_x // TILE_SIZE)
        tile_y = int(world_y // TILE_SIZE)
        return tile_x, tile_y

    def _is_in_break_range(self, tile_x, tile_y):
        """Check if the tile is within break range of the player."""
        # Get player center in tile coordinates
        player_center_x = (self.player.x + self.player.width / 2) / TILE_SIZE
        player_center_y = (self.player.y + self.player.height / 2) / TILE_SIZE

        # Calculate distance
        dx = tile_x - player_center_x
        dy = tile_y - player_center_y
        distance = math.sqrt(dx * dx + dy * dy)

        return distance <= BREAK_RANGE

    def _start_breaking(self, mouse_pos):
        """Start breaking a block at mouse position."""
        tile_x, tile_y = self._get_tile_at_mouse(mouse_pos)

        # Check if in range and breakable
        if not self._is_in_break_range(tile_x, tile_y):
            return

        block_type = self.world.get_block(tile_x, tile_y)
        if not is_block_breakable(block_type):
            return

        # Get selected tool for efficiency calculation
        selected_item = self.inventory.get_selected_item()
        tool_type = None
        if selected_item is not None and is_tool(selected_item[0]):
            tool_type = selected_item[0]
        
        # Trees (WOOD, LEAVES) are only breakable with AXE
        if block_type in (BlockType.WOOD, BlockType.LEAVES):
            if tool_type != ToolType.AXE:
                return  # Cannot break trees without axe

        # Start breaking
        self.breaking_tile = (tile_x, tile_y)
        self.break_progress = 0.0
        self.break_time_required = get_break_time_with_tool(block_type, tool_type)

    def _stop_breaking(self):
        """Stop breaking (mouse released)."""
        self.breaking_tile = None
        self.break_progress = 0.0

    def _swing_sword(self):
        """Swing the sword to attack enemies."""
        if self.sword_swing_active:
            return  # Already swinging
        
        self.sword_swing_active = True
        self.sword_swing_timer = SWORD_SWING_DURATION
        self.sword_swing_angle = 0.0
        
        # Get player center
        player_center_x = self.player.x + self.player.width / 2
        player_center_y = self.player.y + self.player.height / 2
        
        # Offset swing origin to front of player (based on facing)
        swing_offset_x = 28 if self.player.facing_right else -28
        swing_origin_x = player_center_x + swing_offset_x
        swing_origin_y = player_center_y - 4  # Slightly above center
        
        # Get mouse position to determine swing direction
        mouse_pos = pygame.mouse.get_pos()
        world_x, world_y = self.camera.screen_to_world(*mouse_pos)
        
        # Calculate angle from offset position to mouse
        dx = world_x - swing_origin_x
        dy = world_y - swing_origin_y
        self.sword_swing_angle = math.atan2(dy, dx)
        
        # Check for enemy hits
        hit_enemies = self.enemy_manager.check_sword_hit(
            self.player.rect, self.sword_swing_angle, SWORD_SWING_RANGE
        )
        
        for enemy in hit_enemies:
            enemy.take_damage(SWORD_DAMAGE)
            enemy.apply_knockback(player_center_x)

    def _shoot_bow(self):
        """Shoot an arrow from the bow based on charge time."""
        # Check if we have arrows
        arrow_count = 0
        arrow_slot = None
        for i, slot in enumerate(self.inventory.hotbar):
            if slot is not None and slot[0] == ItemType.ARROW:
                arrow_count = slot[1]
                arrow_slot = ('hotbar', i)
                break
        if arrow_slot is None:
            for row in range(3):
                for col in range(9):
                    slot = self.inventory.storage[row][col]
                    if slot is not None and slot[0] == ItemType.ARROW:
                        arrow_count = slot[1]
                        arrow_slot = ('storage', row, col)
                        break
                if arrow_slot:
                    break
        
        if arrow_count <= 0:
            return  # No arrows
        
        # Calculate charge time
        current_time = pygame.time.get_ticks() / 1000.0
        charge_time = current_time - self.bow_charge_start
        charge_ratio = min(charge_time / self.bow_max_charge, 1.0)  # 0 to 1
        
        # Calculate arrow velocity based on charge
        # Min speed: 1 block distance, Max speed: 15 blocks distance
        # Speed in pixels per frame, but we'll use velocity
        min_speed = 3.0  # Low speed for quick tap
        max_speed = 15.0  # High speed for full charge
        speed = min_speed + (max_speed - min_speed) * charge_ratio
        
        # Get player position
        player_center_x = self.player.x + self.player.width / 2
        player_center_y = self.player.y + self.player.height / 2
        
        # Get mouse position for direction
        mouse_pos = pygame.mouse.get_pos()
        world_x, world_y = self.camera.screen_to_world(*mouse_pos)
        
        # Calculate angle to mouse
        dx = world_x - player_center_x
        dy = world_y - player_center_y
        angle = math.atan2(dy, dx)
        
        # Calculate velocity
        vx = math.cos(angle) * speed
        vy = math.sin(angle) * speed
        
        # Spawn arrow slightly in front of player
        spawn_x = player_center_x + math.cos(angle) * 30
        spawn_y = player_center_y + math.sin(angle) * 30
        
        # Calculate damage based on charge (1 for quick tap, 3 for full charge)
        damage = 1 + int(charge_ratio * 2)  # 1, 2, or 3 damage
        
        self.arrow_manager.spawn_arrow(spawn_x, spawn_y, vx, vy, damage=damage)
        
        # Consume arrow
        if arrow_slot[0] == 'hotbar':
            i = arrow_slot[1]
            if self.inventory.hotbar[i][1] <= 1:
                self.inventory.hotbar[i] = None
            else:
                self.inventory.hotbar[i] = (ItemType.ARROW, self.inventory.hotbar[i][1] - 1)
        else:
            row, col = arrow_slot[1], arrow_slot[2]
            if self.inventory.storage[row][col][1] <= 1:
                self.inventory.storage[row][col] = None
            else:
                self.inventory.storage[row][col] = (ItemType.ARROW, self.inventory.storage[row][col][1] - 1)

    def _drop_selected_item(self):
        """Drop the selected item from inventory in the direction player is facing."""
        selected_item = self.inventory.get_selected_item()
        if selected_item is None:
            return
        
        item_type, count = selected_item
        
        # Calculate throw direction based on player facing
        if self.player.facing_right:
            vx = THROW_FORCE
            offset_x = 20  # Spawn slightly in front
        else:
            vx = -THROW_FORCE
            offset_x = -20
        
        # Add upward arc
        vy = THROW_FORCE * THROW_UPWARD_ANGLE
        
        # Get player position for drop spawn (slightly in front of player)
        player_center_x = self.player.x + self.player.width / 2 + offset_x
        player_center_y = self.player.y + self.player.height / 3  # Chest level
        
        # Spawn the thrown drop
        self.drop_manager.spawn_thrown_drop(
            player_center_x,
            player_center_y,
            item_type,
            vx,
            vy
        )
        
        # Remove from inventory
        if is_tool(item_type):
            # Tools are dropped entirely
            self.inventory.hotbar[self.inventory.selected_slot] = None
        else:
            # Stackable items: drop only 1
            if count <= 1:
                self.inventory.hotbar[self.inventory.selected_slot] = None
            else:
                self.inventory.hotbar[self.inventory.selected_slot] = (item_type, count - 1)

    def _try_place_block(self, mouse_pos):
        """Try to place a block from inventory or toggle a door."""
        tile_x, tile_y = self._get_tile_at_mouse(mouse_pos)

        # Check if in range
        if not self._is_in_break_range(tile_x, tile_y):
            return

        # Check if clicking on a door - toggle it
        if self.world.get_block(tile_x, tile_y) == BlockType.DOOR:
            # Check if door is currently open (will be closing)
            is_open = self.world.is_door_open(tile_x, tile_y)
            
            if is_open:
                # Door is closing - check if player is inside door area
                door_left = tile_x * TILE_SIZE
                door_right = (tile_x + 1) * TILE_SIZE
                
                player_left = self.player.x
                player_right = self.player.x + self.player.width
                
                # Check horizontal overlap
                if player_right > door_left and player_left < door_right:
                    # Player is horizontally inside door - push them out
                    player_center_x = self.player.x + self.player.width / 2
                    door_center_x = tile_x * TILE_SIZE + TILE_SIZE / 2
                    
                    if player_center_x < door_center_x:
                        # Push player left
                        self.player.x = door_left - self.player.width - 1
                    else:
                        # Push player right
                        self.player.x = door_right + 1
            
            self.world.toggle_door(tile_x, tile_y)
            return

        # Check if tile is empty
        if self.world.get_block(tile_x, tile_y) != 0:  # Not air
            return

        # Check if we have an item selected
        selected = self.inventory.get_selected_item()
        if selected is None:
            return

        block_type, count = selected

        # Can't place tools or arrows as blocks
        if is_tool(block_type) or block_type == ItemType.ARROW:
            return

        # Special handling for doors (3 blocks tall)
        if block_type == BlockType.DOOR:
            # Check if we have space for 3 blocks vertically
            # Door is placed from bottom up
            can_place = True
            for dy in range(3):
                check_y = tile_y - dy
                if check_y < 0:
                    can_place = False
                    break
                if self.world.get_block(tile_x, check_y) != 0:
                    can_place = False
                    break
            
            if not can_place:
                return
            
            # Check if any of the 3 blocks would intersect player
            for dy in range(3):
                check_y = tile_y - dy
                block_rect = pygame.Rect(
                    tile_x * TILE_SIZE,
                    check_y * TILE_SIZE,
                    TILE_SIZE,
                    TILE_SIZE
                )
                if block_rect.colliderect(self.player.rect):
                    return
            
            # Place the 3 door blocks
            for dy in range(3):
                self.world.set_block(tile_x, tile_y - dy, BlockType.DOOR)
            
            self.inventory.remove_item(self.inventory.selected_slot, 1)
            return

        # Check if block would intersect player
        block_rect = pygame.Rect(
            tile_x * TILE_SIZE,
            tile_y * TILE_SIZE,
            TILE_SIZE,
            TILE_SIZE
        )
        if block_rect.colliderect(self.player.rect):
            return

        # Place the block
        self.world.set_block(tile_x, tile_y, block_type)
        self.inventory.remove_item(self.inventory.selected_slot, 1)

    def update(self):
        """Update game state."""
        dt = 1.0 / FPS  # Time delta in seconds
        
        # Only update game logic when playing
        if self.game_state != GAME_STATE_PLAYING:
            return

        # Update day/night cycle
        self.time_of_day += dt
        if self.time_of_day >= DAY_DURATION:
            self.time_of_day = 0.0
            self.is_night = not self.is_night
        
        # Update sword swing
        if self.sword_swing_active:
            self.sword_swing_timer -= dt
            if self.sword_swing_timer <= 0:
                self.sword_swing_active = False
        
        # Update player damage cooldown
        if self.player_damage_cooldown > 0:
            self.player_damage_cooldown -= dt

        # Don't update player if inventory is open
        if not self.inventory.is_open:
            # Player movement
            keys = pygame.key.get_pressed()
            self.player.handle_input(keys)
            self.player.update(self.world)
            self.camera.follow(self.player.rect)
            self.camera.update()

            # Handle breaking progress
            if self.mouse_held and self.breaking_tile is not None:
                tile_x, tile_y = self.breaking_tile

                # Check if still in range and still valid
                if self._is_in_break_range(tile_x, tile_y):
                    block_type = self.world.get_block(tile_x, tile_y)
                    if is_block_breakable(block_type):
                        # Get current tool for efficiency calculation
                        selected_item = self.inventory.get_selected_item()
                        tool_type = None
                        if selected_item is not None and is_tool(selected_item[0]):
                            tool_type = selected_item[0]
                        
                        # Trees (WOOD, LEAVES) require AXE to break
                        can_break = True
                        if block_type in (BlockType.WOOD, BlockType.LEAVES):
                            if tool_type != ToolType.AXE:
                                can_break = False
                                self._stop_breaking()
                        
                        if can_break:
                            # Recalculate break time if tool changed
                            current_break_time = get_break_time_with_tool(block_type, tool_type)
                            if current_break_time != self.break_time_required:
                                self.break_time_required = current_break_time
                            
                            # Progress breaking
                            self.break_progress += dt / self.break_time_required

                        if self.break_progress >= 1.0:
                            # Block broken!
                            self._break_block(tile_x, tile_y, block_type)
                            self.breaking_tile = None
                            self.break_progress = 0.0
                    else:
                        self._stop_breaking()
                else:
                    self._stop_breaking()

        # Update drops and check for collection
        collected_drops = self.drop_manager.update(dt, self.player.rect, self.world)
        for drop in collected_drops:
            if self.inventory.add_item(drop.block_type):
                self.drop_manager.remove_drop(drop)
        
        # Update particles
        self.particle_manager.update(dt)
        
        # Update arrows
        self.arrow_manager.update(dt, self.world, self.enemy_manager.enemies)
        
        # Update enemies
        damage_to_player = self.enemy_manager.update(dt, self.world, self.player.rect, self.is_night)
        
        # Apply damage to player
        if damage_to_player > 0 and self.player_damage_cooldown <= 0:
            self.player_health -= damage_to_player
            self.player_damage_cooldown = 1.0  # 1 second cooldown
            if self.player_health <= 0:
                # Player dies - respawn
                self._respawn_player()

    def _break_block(self, tile_x, tile_y, block_type):
        """Break a block and spawn a drop. Handle tree collapse for wood blocks."""
        # Special handling for doors (3 blocks tall)
        if block_type == BlockType.DOOR:
            # Break all door blocks
            broken_positions = self.world.break_door(tile_x, tile_y)
            if broken_positions:
                # Only drop 1 door item from the bottom-most position
                bottom_y = max(y for x, y in broken_positions)
                bottom_x = tile_x
                self.drop_manager.spawn_drop(bottom_x, bottom_y, BlockType.DOOR)
            return
        
        # Check if this is a wood block - if so, check for tree collapse
        if block_type == BlockType.WOOD:
            self._handle_tree_collapse(tile_x, tile_y)
        
        # Remove the block
        self.world.break_block(tile_x, tile_y)

        # Leaves spawn particles instead of drops
        if block_type == BlockType.LEAVES:
            self.particle_manager.spawn_leaf_particles(
                tile_x * TILE_SIZE + TILE_SIZE // 2,
                tile_y * TILE_SIZE + TILE_SIZE // 2,
                count=5
            )
            return

        # Grass drops dirt instead of grass
        drop_type = block_type
        if block_type == BlockType.GRASS:
            drop_type = BlockType.DIRT

        # Spawn a drop
        self.drop_manager.spawn_drop(tile_x, tile_y, drop_type)
    
    def _respawn_player(self):
        """Respawn the player at the spawn point."""
        spawn_x, spawn_y = self.world.get_player_spawn()
        self.player.x = float(spawn_x)
        self.player.y = float(spawn_y)
        self.player.vx = 0
        self.player.vy = 0
        self.player_health = self.player_max_health
        self.enemy_manager.enemies.clear()  # Clear all enemies on death
    
    def _handle_tree_collapse(self, tile_x, tile_y):
        """Check if breaking a wood block should collapse the tree above."""
        # Use flood-fill to find all connected tree parts (wood and leaves)
        # that are connected to blocks above the broken block
        blocks_to_drop = []
        visited = set()
        
        # Start from blocks directly above the broken block
        # Check if there are wood blocks above
        start_y = tile_y - 1
        if self.world.get_block(tile_x, start_y) not in (BlockType.WOOD, BlockType.LEAVES):
            return  # No tree above to collapse
        
        # Flood fill to find all connected tree parts
        stack = [(tile_x, start_y)]
        
        while stack:
            cx, cy = stack.pop()
            
            if (cx, cy) in visited:
                continue
            
            block = self.world.get_block(cx, cy)
            if block not in (BlockType.WOOD, BlockType.LEAVES):
                continue
            
            # Only process blocks above or at the same level as the broken block
            if cy > tile_y:
                continue
            
            visited.add((cx, cy))
            blocks_to_drop.append((cx, cy))
            
            # Check all 4 adjacent blocks (up, down, left, right)
            for dx, dy in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
                nx, ny = cx + dx, cy + dy
                if (nx, ny) not in visited and 0 <= nx < self.world.width and 0 <= ny < self.world.height:
                    neighbor_block = self.world.get_block(nx, ny)
                    if neighbor_block in (BlockType.WOOD, BlockType.LEAVES):
                        stack.append((nx, ny))
        
        # Drop all the blocks
        for bx, by in blocks_to_drop:
            block = self.world.get_block(bx, by)
            if block != BlockType.AIR:
                self.world.break_block(bx, by)
                # Leaves spawn particles, wood spawns drops
                if block == BlockType.LEAVES:
                    self.particle_manager.spawn_leaf_particles(
                        bx * TILE_SIZE + TILE_SIZE // 2,
                        by * TILE_SIZE + TILE_SIZE // 2,
                        count=5
                    )
                else:
                    self.drop_manager.spawn_drop(bx, by, block, falling=True)

    def draw(self):
        """Draw everything."""
        # Handle MENU state
        if self.game_state == GAME_STATE_MENU:
            self.screen.fill((40, 40, 60))  # Dark blue background
            self._draw_main_menu()
            pygame.display.flip()
            return
        
        # Clear screen with dynamic sky color
        sky_color = self._get_sky_color()
        self.screen.fill(sky_color)
        
        # Draw sun or moon
        self._draw_celestial_body()

        # Draw world
        self.world.draw(self.screen, self.camera)

        # Draw dropped items
        self.drop_manager.draw(self.screen, self.camera)
        
        # Draw particles
        self.particle_manager.draw(self.screen, self.camera)
        
        # Draw arrows
        self.arrow_manager.draw(self.screen, self.camera)
        
        # Draw enemies
        self.enemy_manager.draw(self.screen, self.camera)

        # Draw player
        self.player.draw(self.screen, self.camera)
        
        # Draw sword swing
        if self.sword_swing_active:
            self._draw_sword_swing()

        # Draw breaking progress
        self._draw_breaking_progress()

        # Draw range indicator (only if inventory not open)
        if not self.inventory.is_open:
            self._draw_range_indicator()

        # Draw inventory
        mouse_pos = pygame.mouse.get_pos()
        self.inventory.draw(self.screen, *mouse_pos)

        # Draw inventory tooltip
        self.inventory.draw_tooltip(self.screen, *mouse_pos)

        # Draw dragged item
        self.inventory.draw_drag_item(self.screen, *mouse_pos)
        
        # Draw player health bar
        self._draw_health_bar()

        # Draw HUD / instructions
        self._draw_hud()
        
        # Draw pause menu overlay
        if self.game_state == GAME_STATE_PAUSED:
            self._draw_pause_menu()

        pygame.display.flip()
    
    def _draw_celestial_body(self):
        """Draw sun during day or moon during night. Position indicates time remaining."""
        # Progress through current day/night cycle (0.0 to 1.0)
        progress = self.time_of_day / DAY_DURATION
        
        # Calculate position - moves from top-left to top-right in a straight line
        # Sun/Moon travels horizontally across the top of the screen
        x_pos = int(SCREEN_WIDTH * progress)
        
        # Y position stays near the top, slight arc for visual interest
        # Arc peaks in the middle of the journey
        arc_progress = progress * 2 - 1  # -1 to 1
        arc_height = 1 - (arc_progress * arc_progress)  # 1 at center, 0 at edges
        y_pos = int(SCREEN_HEIGHT * 0.15 + SCREEN_HEIGHT * 0.1 * (1 - arc_height))
        
        if self.is_night:
            # Draw moon (white/gray circle with craters)
            moon_radius = 25
            pygame.draw.circle(self.screen, (240, 240, 230), (x_pos, y_pos), moon_radius)
            # Draw some craters
            pygame.draw.circle(self.screen, (200, 200, 190), (x_pos - 8, y_pos - 5), 6)
            pygame.draw.circle(self.screen, (200, 200, 190), (x_pos + 10, y_pos + 8), 4)
            pygame.draw.circle(self.screen, (200, 200, 190), (x_pos + 5, y_pos - 10), 3)
        else:
            # Draw sun (yellow circle with rays)
            sun_radius = 30
            pygame.draw.circle(self.screen, (255, 220, 50), (x_pos, y_pos), sun_radius)
            # Draw rays
            for i in range(8):
                angle = i * math.pi / 4
                ray_start_x = x_pos + int(math.cos(angle) * (sun_radius + 5))
                ray_start_y = y_pos + int(math.sin(angle) * (sun_radius + 5))
                ray_end_x = x_pos + int(math.cos(angle) * (sun_radius + 15))
                ray_end_y = y_pos + int(math.sin(angle) * (sun_radius + 15))
                pygame.draw.line(self.screen, (255, 220, 50), 
                               (ray_start_x, ray_start_y), 
                               (ray_end_x, ray_end_y), 3)
    
    def _get_sky_color(self):
        """Get the current sky color based on time of day."""
        progress = self.time_of_day / DAY_DURATION
        
        # Define color transitions
        if self.is_night:
            # Night: dark blue throughout
            # Transition to dawn near the end
            if progress < 0.8:
                return NIGHT_SKY_COLOR
            else:
                # Transition from night to dawn (pinkish)
                t = (progress - 0.8) / 0.2  # 0 to 1 in last 20%
                dawn_color = (80, 80, 120)
                r = int(NIGHT_SKY_COLOR[0] + (dawn_color[0] - NIGHT_SKY_COLOR[0]) * t)
                g = int(NIGHT_SKY_COLOR[1] + (dawn_color[1] - NIGHT_SKY_COLOR[1]) * t)
                b = int(NIGHT_SKY_COLOR[2] + (dawn_color[2] - NIGHT_SKY_COLOR[2]) * t)
                return (r, g, b)
        else:
            # Day: sky blue with sunset near the end
            if progress < 0.7:
                return DAY_SKY_COLOR
            elif progress < 0.85:
                # Transition to sunset (orange-ish)
                t = (progress - 0.7) / 0.15
                sunset_color = (255, 150, 100)
                r = int(DAY_SKY_COLOR[0] + (sunset_color[0] - DAY_SKY_COLOR[0]) * t)
                g = int(DAY_SKY_COLOR[1] + (sunset_color[1] - DAY_SKY_COLOR[1]) * t)
                b = int(DAY_SKY_COLOR[2] + (sunset_color[2] - DAY_SKY_COLOR[2]) * t)
                return (r, g, b)
            else:
                # Transition to dusk (purple-ish)
                t = (progress - 0.85) / 0.15
                dusk_color = (60, 40, 80)
                sunset_color = (255, 150, 100)
                r = int(sunset_color[0] + (dusk_color[0] - sunset_color[0]) * t)
                g = int(sunset_color[1] + (dusk_color[1] - sunset_color[1]) * t)
                b = int(sunset_color[2] + (dusk_color[2] - sunset_color[2]) * t)
                return (r, g, b)
    
    def _draw_sword_swing(self):
        """Draw the sword swing animation."""
        # Calculate sword position based on swing progress
        progress = 1.0 - (self.sword_swing_timer / SWORD_SWING_DURATION)
        
        # Swing arc from -60 to +60 degrees around the swing angle
        swing_offset = (progress - 0.5) * math.pi  # -90 to +90 degrees
        current_angle = self.sword_swing_angle + swing_offset
        
        # Player center
        player_center_x = self.player.x + self.player.width / 2
        player_center_y = self.player.y + self.player.height / 2
        
        # Offset swing origin to front of player (based on facing)
        swing_offset_x = 28 if self.player.facing_right else -28
        swing_origin_x = player_center_x + swing_offset_x
        swing_origin_y = player_center_y - 4  # Slightly above center
        
        # Sword tip position
        sword_length = SWORD_SWING_RANGE
        tip_x = swing_origin_x + math.cos(current_angle) * sword_length
        tip_y = swing_origin_y + math.sin(current_angle) * sword_length
        
        # Convert to screen coordinates
        screen_center_x, screen_center_y = self.camera.world_to_screen(swing_origin_x, swing_origin_y)
        screen_tip_x, screen_tip_y = self.camera.world_to_screen(tip_x, tip_y)
        
        # Draw sword slash trail
        trail_width = max(2, int(8 * self.camera.zoom))
        
        # Draw multiple lines for a trail effect
        for i in range(3):
            alpha = 255 - i * 60
            offset = i * 0.1
            angle1 = current_angle - offset
            angle2 = current_angle + offset
            
            x1 = screen_center_x + math.cos(angle1) * sword_length * self.camera.zoom
            y1 = screen_center_y + math.sin(angle1) * sword_length * self.camera.zoom
            x2 = screen_center_x + math.cos(angle2) * sword_length * self.camera.zoom
            y2 = screen_center_y + math.sin(angle2) * sword_length * self.camera.zoom
            
            # Draw arc
            pygame.draw.line(self.screen, (200, 200, 220), 
                           (int(screen_center_x), int(screen_center_y)),
                           (int(x1), int(y1)), trail_width - i)
            pygame.draw.line(self.screen, (200, 200, 220), 
                           (int(screen_center_x), int(screen_center_y)),
                           (int(x2), int(y2)), trail_width - i)
        
        # Draw sword blade
        pygame.draw.line(self.screen, (220, 220, 230),
                        (int(screen_center_x), int(screen_center_y)),
                        (int(screen_tip_x), int(screen_tip_y)), trail_width)
    
    def _draw_health_bar(self):
        """Draw player health bar."""
        bar_width = 200
        bar_height = 20
        bar_x = 10
        bar_y = SCREEN_HEIGHT - 60
        
        # Background
        pygame.draw.rect(self.screen, (50, 50, 50),
                        (bar_x, bar_y, bar_width, bar_height))
        
        # Health fill
        health_width = int(bar_width * (self.player_health / self.player_max_health))
        health_color = (50, 200, 50) if self.player_health > 3 else (200, 50, 50)
        pygame.draw.rect(self.screen, health_color,
                        (bar_x, bar_y, health_width, bar_height))
        
        # Border
        pygame.draw.rect(self.screen, WHITE,
                        (bar_x, bar_y, bar_width, bar_height), 2)
        
        # Health text
        font = pygame.font.SysFont(None, 18)
        health_text = font.render(f"HP: {self.player_health}/{self.player_max_health}", True, WHITE)
        self.screen.blit(health_text, (bar_x + 5, bar_y + 3))

    def _draw_breaking_progress(self):
        """Draw breaking progress bar and cracking animation on the block being broken."""
        if self.breaking_tile is None or self.break_progress <= 0:
            return

        tile_x, tile_y = self.breaking_tile

        # Calculate screen position with zoom
        world_x = tile_x * TILE_SIZE
        world_y = tile_y * TILE_SIZE
        screen_x, screen_y = self.camera.world_to_screen(world_x, world_y)
        scaled_tile = TILE_SIZE * self.camera.zoom

        # Draw progress bar background
        bar_width = scaled_tile
        bar_height = 6
        bar_y = screen_y - bar_height - 2

        pygame.draw.rect(
            self.screen,
            (50, 50, 50),
            (int(screen_x), int(bar_y), int(bar_width), bar_height)
        )

        # Draw progress bar fill
        progress_width = int(bar_width * self.break_progress)
        pygame.draw.rect(
            self.screen,
            (0, 200, 0),
            (int(screen_x), int(bar_y), progress_width, bar_height)
        )

        # Draw border
        pygame.draw.rect(
            self.screen,
            WHITE,
            (int(screen_x), int(bar_y), int(bar_width), bar_height),
            1
        )

        # Draw cracking animation on the block
        self._draw_crack_effect(int(screen_x), int(screen_y), int(scaled_tile))
    
    def _draw_crack_effect(self, x, y, size):
        """Draw a cracking effect on a block based on break progress."""
        # Create crack patterns for different progress stages
        progress = self.break_progress
        
        # Define crack lines based on progress (0.0 to 1.0)
        # More cracks appear as progress increases
        crack_color = (30, 30, 30)  # Dark gray for cracks
        
        center_x = x + size // 2
        center_y = y + size // 2
        
        # Stage 1: Small cracks (0-33%)
        if progress > 0.1:
            alpha = min(255, int(progress * 300))
            # First small crack from center to top-left
            self._draw_crack_line(
                self.screen, center_x, center_y,
                x + int(size * 0.2), y + int(size * 0.15),
                crack_color, max(1, size // 16)
            )
        
        if progress > 0.2:
            # Second small crack from center to bottom-right
            self._draw_crack_line(
                self.screen, center_x, center_y,
                x + int(size * 0.85), y + int(size * 0.8),
                crack_color, max(1, size // 16)
            )
        
        # Stage 2: Medium cracks (33-66%)
        if progress > 0.33:
            # Crack from center to top-right
            self._draw_crack_line(
                self.screen, center_x, center_y,
                x + int(size * 0.8), y + int(size * 0.2),
                crack_color, max(1, size // 14)
            )
            # Branch from first crack
            self._draw_crack_line(
                self.screen, x + int(size * 0.35), y + int(size * 0.25),
                x + int(size * 0.15), y + int(size * 0.4),
                crack_color, max(1, size // 18)
            )
        
        if progress > 0.45:
            # Crack from center to bottom-left
            self._draw_crack_line(
                self.screen, center_x, center_y,
                x + int(size * 0.15), y + int(size * 0.85),
                crack_color, max(1, size // 14)
            )
            # Branch from second crack
            self._draw_crack_line(
                self.screen, x + int(size * 0.7), y + int(size * 0.65),
                x + int(size * 0.85), y + int(size * 0.55),
                crack_color, max(1, size // 18)
            )
        
        # Stage 3: Heavy cracks (66-100%)
        if progress > 0.66:
            # Horizontal crack across middle
            self._draw_crack_line(
                self.screen, x + int(size * 0.1), center_y,
                x + int(size * 0.9), center_y,
                crack_color, max(1, size // 12)
            )
            # Branches
            self._draw_crack_line(
                self.screen, x + int(size * 0.3), center_y,
                x + int(size * 0.2), y + int(size * 0.6),
                crack_color, max(1, size // 16)
            )
            self._draw_crack_line(
                self.screen, x + int(size * 0.7), center_y,
                x + int(size * 0.8), y + int(size * 0.4),
                crack_color, max(1, size // 16)
            )
        
        if progress > 0.8:
            # Vertical crack
            self._draw_crack_line(
                self.screen, center_x, y + int(size * 0.1),
                center_x, y + int(size * 0.9),
                crack_color, max(1, size // 12)
            )
            # More branches
            self._draw_crack_line(
                self.screen, center_x, y + int(size * 0.3),
                x + int(size * 0.55), y + int(size * 0.25),
                crack_color, max(1, size // 18)
            )
            self._draw_crack_line(
                self.screen, center_x, y + int(size * 0.7),
                x + int(size * 0.45), y + int(size * 0.75),
                crack_color, max(1, size // 18)
            )
        
        # Draw small debris particles at high progress
        if progress > 0.5:
            import random
            # Use deterministic "random" based on tile position for consistent animation
            seed = hash((self.breaking_tile[0], self.breaking_tile[1]))
            random.seed(seed)
            
            num_particles = int(progress * 8)
            for i in range(num_particles):
                px = x + random.randint(0, size)
                py = y + random.randint(0, size)
                particle_size = max(1, size // 20)
                pygame.draw.rect(
                    self.screen,
                    crack_color,
                    (px, py, particle_size, particle_size)
                )
    
    def _draw_crack_line(self, surface, x1, y1, x2, y2, color, width):
        """Draw a jagged crack line between two points."""
        import math
        
        # Calculate distance and direction
        dx = x2 - x1
        dy = y2 - y1
        distance = math.sqrt(dx * dx + dy * dy)
        
        if distance < 2:
            return
        
        # Draw the main line
        pygame.draw.line(surface, color, (x1, y1), (x2, y2), width)
        
        # Add some jaggedness with small perpendicular lines
        mid_x = (x1 + x2) // 2
        mid_y = (y1 + y2) // 2
        
        # Perpendicular offset
        if distance > 10:
            perp_x = -dy // max(1, int(distance))
            perp_y = dx // max(1, int(distance))
            
            # Small jag
            pygame.draw.line(
                surface, color,
                (mid_x, mid_y),
                (mid_x + perp_x // 2, mid_y + perp_y // 2),
                max(1, width - 1)
            )

    def _draw_range_indicator(self):
        """Draw a subtle indicator showing break range."""
        mouse_pos = pygame.mouse.get_pos()
        tile_x, tile_y = self._get_tile_at_mouse(mouse_pos)

        # Draw highlight on hovered block if in range
        if self._is_in_break_range(tile_x, tile_y):
            block_type = self.world.get_block(tile_x, tile_y)
            if is_block_breakable(block_type):
                # Calculate screen position with zoom
                world_x = tile_x * TILE_SIZE
                world_y = tile_y * TILE_SIZE
                screen_x, screen_y = self.camera.world_to_screen(world_x, world_y)
                scaled_tile = TILE_SIZE * self.camera.zoom

                # Draw yellow border to indicate breakable
                rect = pygame.Rect(int(screen_x), int(screen_y), int(scaled_tile), int(scaled_tile))
                pygame.draw.rect(self.screen, YELLOW, rect, 2)

    def _draw_hud(self):
        """Draw HUD elements (text, instructions)."""
        font = pygame.font.SysFont(None, 20)

        # Show title
        title = pygame.font.SysFont(None, 32).render("MyArea", True, WHITE)
        self.screen.blit(title, (SCREEN_WIDTH - 100, 10))
        
        # Show time of day
        time_text = "Night" if self.is_night else "Day"
        time_color = (150, 150, 255) if self.is_night else (255, 200, 100)
        time_display = font.render(f"Time: {time_text}", True, time_color)
        self.screen.blit(time_display, (SCREEN_WIDTH - 100, 45))
        
        # Show enemy count at night
        if self.is_night:
            enemy_count = font.render(f"Enemies: {len(self.enemy_manager.enemies)}", True, (255, 100, 100))
            self.screen.blit(enemy_count, (SCREEN_WIDTH - 100, 65))

        # Instructions at bottom
        if self.inventory.is_open:
            text = font.render("Tab: Close Inventory | Drag items to rearrange", True, WHITE)
        else:
            text = font.render(
                "WASD: Move | Space: Jump | L-Click: Attack/Break | R-Click: Place | Tab: Inventory",
                True, WHITE
            )
        self.screen.blit(text, (10, SCREEN_HEIGHT - 25))

        # Show current breaking info if breaking
        if self.breaking_tile is not None:
            tile_x, tile_y = self.breaking_tile
            block_type = self.world.get_block(tile_x, tile_y)
            name = get_block_name(block_type)
            info = font.render(f"Breaking: {name} ({self.break_progress * 100:.0f}%)", True, WHITE)
            self.screen.blit(info, (10, 60))
        
        # Show bow charge indicator if charging
        if self.bow_charging:
            current_time = pygame.time.get_ticks() / 1000.0
            charge_time = current_time - self.bow_charge_start
            charge_ratio = min(charge_time / self.bow_max_charge, 1.0)
            
            # Draw charge bar
            bar_x = SCREEN_WIDTH // 2 - 50
            bar_y = SCREEN_HEIGHT // 2 + 50
            bar_width = 100
            bar_height = 10
            
            # Background
            pygame.draw.rect(self.screen, (50, 50, 50), (bar_x, bar_y, bar_width, bar_height))
            
            # Fill based on charge
            fill_width = int(bar_width * charge_ratio)
            fill_color = (100 + int(155 * charge_ratio), 200 - int(150 * charge_ratio), 50)  # Green to red
            pygame.draw.rect(self.screen, fill_color, (bar_x, bar_y, fill_width, bar_height))
            
            # Border
            pygame.draw.rect(self.screen, WHITE, (bar_x, bar_y, bar_width, bar_height), 1)
            
            # Charge percentage text
            charge_text = font.render(f"Charge: {int(charge_ratio * 100)}%", True, WHITE)
            self.screen.blit(charge_text, (bar_x, bar_y - 20))

    def _draw_main_menu(self):
        """Draw the main menu with Play and Quit buttons."""
        # Title
        title_text = self.title_font.render("MyArea", True, WHITE)
        title_rect = title_text.get_rect(center=(SCREEN_WIDTH // 2, 150))
        self.screen.blit(title_text, title_rect)
        
        # Subtitle
        subtitle_text = self.menu_font.render("A 2D Sandbox Adventure", True, (180, 180, 200))
        subtitle_rect = subtitle_text.get_rect(center=(SCREEN_WIDTH // 2, 200))
        self.screen.blit(subtitle_text, subtitle_rect)
        
        # Button positions
        button_width = 200
        button_height = 60
        button_y_start = 280
        button_spacing = 80
        
        # Play button
        self.play_button_rect = pygame.Rect(
            (SCREEN_WIDTH - button_width) // 2,
            button_y_start,
            button_width,
            button_height
        )
        pygame.draw.rect(self.screen, (60, 120, 60), self.play_button_rect, border_radius=10)
        pygame.draw.rect(self.screen, WHITE, self.play_button_rect, 3, border_radius=10)
        play_text = self.button_font.render("Play", True, WHITE)
        play_rect = play_text.get_rect(center=self.play_button_rect.center)
        self.screen.blit(play_text, play_rect)
        
        # Quit button
        self.quit_button_rect = pygame.Rect(
            (SCREEN_WIDTH - button_width) // 2,
            button_y_start + button_spacing,
            button_width,
            button_height
        )
        pygame.draw.rect(self.screen, (120, 60, 60), self.quit_button_rect, border_radius=10)
        pygame.draw.rect(self.screen, WHITE, self.quit_button_rect, 3, border_radius=10)
        quit_text = self.button_font.render("Quit", True, WHITE)
        quit_rect = quit_text.get_rect(center=self.quit_button_rect.center)
        self.screen.blit(quit_text, quit_rect)
        
        # Instructions
        hint_text = self.menu_font.render("Press ESC or click Quit to exit", True, (150, 150, 150))
        hint_rect = hint_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 60))
        self.screen.blit(hint_text, hint_rect)

    def _draw_pause_menu(self):
        """Draw the pause menu overlay with Resume and Quit buttons."""
        # Semi-transparent overlay
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        self.screen.blit(overlay, (0, 0))
        
        # Pause title
        pause_text = self.title_font.render("PAUSED", True, WHITE)
        pause_rect = pause_text.get_rect(center=(SCREEN_WIDTH // 2, 150))
        self.screen.blit(pause_text, pause_rect)
        
        # Button positions
        button_width = 200
        button_height = 60
        button_y_start = 250
        button_spacing = 80
        
        # Resume button
        self.resume_button_rect = pygame.Rect(
            (SCREEN_WIDTH - button_width) // 2,
            button_y_start,
            button_width,
            button_height
        )
        pygame.draw.rect(self.screen, (60, 120, 60), self.resume_button_rect, border_radius=10)
        pygame.draw.rect(self.screen, WHITE, self.resume_button_rect, 3, border_radius=10)
        resume_text = self.button_font.render("Resume", True, WHITE)
        resume_rect = resume_text.get_rect(center=self.resume_button_rect.center)
        self.screen.blit(resume_text, resume_rect)
        
        # Quit button
        self.quit_button_rect = pygame.Rect(
            (SCREEN_WIDTH - button_width) // 2,
            button_y_start + button_spacing,
            button_width,
            button_height
        )
        pygame.draw.rect(self.screen, (120, 60, 60), self.quit_button_rect, border_radius=10)
        pygame.draw.rect(self.screen, WHITE, self.quit_button_rect, 3, border_radius=10)
        quit_text = self.button_font.render("Quit", True, WHITE)
        quit_rect = quit_text.get_rect(center=self.quit_button_rect.center)
        self.screen.blit(quit_text, quit_rect)
        
        # Hint
        hint_text = self.menu_font.render("Press ESC to resume", True, (180, 180, 180))
        hint_rect = hint_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 60))
        self.screen.blit(hint_text, hint_rect)

    def run(self):
        """Main game loop."""
        while self.running:
            self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(FPS)

        pygame.quit()
        sys.exit()


def main():
    """Entry point for python3 -m game.main."""
    game = Game()
    game.run()


if __name__ == "__main__":
    main()
