"""Block definitions and types for the game world."""

from game.constants import (
    GRASS_COLOR, DIRT_COLOR, WOOD_COLOR, LEAVES_COLOR, STONE_COLOR,
    BLACK, SWORD_COLOR, PICKAXE_COLOR, AXE_COLOR, SHOVEL_COLOR
)


class BlockType:
    """Represents a type of block in the game."""
    AIR = 0
    GRASS = 1
    DIRT = 2
    WOOD = 3
    LEAVES = 4
    STONE = 5
    PLANKS = 6
    DOOR = 7
    PLATFORM = 8
    TORCH = 9
    # Ores
    COAL_ORE = 10
    IRON_ORE = 11
    GOLD_ORE = 12
    # Furnace
    FURNACE = 13
    # Ingots (usable as items)
    IRON_INGOT = 14
    GOLD_INGOT = 15
    # Armor items (leather)
    HAT = 16
    BODY_ARMOR = 17
    LEGGINGS = 18
    # Iron armor
    IRON_HAT = 19
    IRON_BODY_ARMOR = 20
    IRON_LEGGINGS = 21
    # Gold armor
    GOLD_HAT = 22
    GOLD_BODY_ARMOR = 23
    GOLD_LEGGINGS = 24


class ToolType:
    """Represents a type of tool."""
    # Basic tools (wood/stone)
    SWORD = 100
    PICKAXE = 101
    AXE = 102
    SHOVEL = 103
    BOW = 104
    # Iron tools
    IRON_SWORD = 110
    IRON_PICKAXE = 111
    IRON_AXE = 112
    IRON_SHOVEL = 113
    # Gold tools
    GOLD_SWORD = 120
    GOLD_PICKAXE = 121
    GOLD_AXE = 122
    GOLD_SHOVEL = 123


class ItemType:
    """Represents non-block, non-tool items."""
    ARROW = 200


# Colors for new items
PLANKS_COLOR = (180, 140, 80)
DOOR_COLOR = (139, 90, 43)
BOW_COLOR = (139, 90, 43)
ARROW_COLOR = (150, 150, 150)
PLATFORM_COLOR = (160, 120, 60)
TORCH_COLOR = (255, 180, 50)  # Warm orange for torch
# Ore colors
COAL_COLOR = (50, 50, 50)  # Dark black/gray
IRON_ORE_COLOR = (140, 110, 90)  # Brownish
GOLD_ORE_COLOR = (200, 180, 60)  # Gold tint on stone
FURNACE_COLOR = (80, 80, 80)  # Dark gray stone
# Ingot colors
IRON_INGOT_COLOR = (180, 180, 200)  # Silver metal
GOLD_INGOT_COLOR = (255, 215, 0)  # Pure gold
# Armor colors
HAT_COLOR = (80, 60, 40)  # Leather brown
BODY_ARMOR_COLOR = (100, 80, 60)  # Leather
LEGGINGS_COLOR = (70, 55, 35)  # Darker leather
# Iron armor colors
IRON_HAT_COLOR = (180, 180, 200)  # Silver metal
IRON_BODY_ARMOR_COLOR = (170, 170, 190)
IRON_LEGGINGS_COLOR = (160, 160, 180)
# Gold armor colors
GOLD_HAT_COLOR = (255, 215, 0)  # Gold
GOLD_BODY_ARMOR_COLOR = (240, 200, 0)
GOLD_LEGGINGS_COLOR = (220, 180, 0)
# Iron tool colors
IRON_TOOL_COLOR = (180, 180, 200)  # Silver metal
# Gold tool colors
GOLD_TOOL_COLOR = (255, 215, 0)  # Gold


# Tool properties: (name, color, damage, speed_multiplier)
# Quality order: Iron > Gold > Wood/Stone
TOOL_DATA = {
    # Basic tools (wood/stone)
    ToolType.SWORD: ("Sword", SWORD_COLOR, 3, 1.0),
    ToolType.PICKAXE: ("Pickaxe", PICKAXE_COLOR, 2, 1.0),
    ToolType.AXE: ("Axe", AXE_COLOR, 3, 1.0),
    ToolType.SHOVEL: ("Shovel", SHOVEL_COLOR, 2, 1.0),
    ToolType.BOW: ("Bow", BOW_COLOR, 1, 1.0),
    # Iron tools (best quality)
    ToolType.IRON_SWORD: ("Iron Sword", IRON_TOOL_COLOR, 7, 1.5),
    ToolType.IRON_PICKAXE: ("Iron Pickaxe", IRON_TOOL_COLOR, 4, 1.5),
    ToolType.IRON_AXE: ("Iron Axe", IRON_TOOL_COLOR, 6, 1.5),
    ToolType.IRON_SHOVEL: ("Iron Shovel", IRON_TOOL_COLOR, 4, 1.5),
    # Gold tools (second best)
    ToolType.GOLD_SWORD: ("Gold Sword", GOLD_TOOL_COLOR, 5, 1.3),
    ToolType.GOLD_PICKAXE: ("Gold Pickaxe", GOLD_TOOL_COLOR, 3, 1.3),
    ToolType.GOLD_AXE: ("Gold Axe", GOLD_TOOL_COLOR, 4, 1.3),
    ToolType.GOLD_SHOVEL: ("Gold Shovel", GOLD_TOOL_COLOR, 3, 1.3),
}

# Other item properties: (name, color)
ITEM_DATA = {
    ItemType.ARROW: ("Arrow", ARROW_COLOR),
}

# Tool efficiency multipliers for different block types
# Lower value = faster breaking
TOOL_EFFICIENCY = {
    ToolType.SWORD: {},  # No efficiency bonus
    ToolType.PICKAXE: {
        BlockType.STONE: 0.25,  # Stone breaks 4x faster
        BlockType.COAL_ORE: 0.25,  # Coal ore breaks 4x faster
        BlockType.IRON_ORE: 0.25,  # Iron ore breaks 4x faster
        BlockType.GOLD_ORE: 0.25,  # Gold ore breaks 4x faster
        BlockType.FURNACE: 0.25,  # Furnace breaks faster with pickaxe
    },
    ToolType.AXE: {BlockType.WOOD: 0.25, BlockType.LEAVES: 0.25, BlockType.PLANKS: 0.25, BlockType.DOOR: 0.25, BlockType.PLATFORM: 0.25},  # Wood items break 4x faster
    ToolType.SHOVEL: {BlockType.GRASS: 0.25, BlockType.DIRT: 0.25},  # Dirt/grass breaks 4x faster
    # Iron tools - even better efficiency
    ToolType.IRON_PICKAXE: {
        BlockType.STONE: 0.15,
        BlockType.COAL_ORE: 0.15,
        BlockType.IRON_ORE: 0.15,
        BlockType.GOLD_ORE: 0.15,
        BlockType.FURNACE: 0.15,
    },
    ToolType.IRON_AXE: {BlockType.WOOD: 0.15, BlockType.LEAVES: 0.15, BlockType.PLANKS: 0.15, BlockType.DOOR: 0.15, BlockType.PLATFORM: 0.15},
    ToolType.IRON_SHOVEL: {BlockType.GRASS: 0.15, BlockType.DIRT: 0.15},
    # Gold tools - good efficiency
    ToolType.GOLD_PICKAXE: {
        BlockType.STONE: 0.2,
        BlockType.COAL_ORE: 0.2,
        BlockType.IRON_ORE: 0.2,
        BlockType.GOLD_ORE: 0.2,
        BlockType.FURNACE: 0.2,
    },
    ToolType.GOLD_AXE: {BlockType.WOOD: 0.2, BlockType.LEAVES: 0.2, BlockType.PLANKS: 0.2, BlockType.DOOR: 0.2, BlockType.PLATFORM: 0.2},
    ToolType.GOLD_SHOVEL: {BlockType.GRASS: 0.2, BlockType.DIRT: 0.2},
}


def is_tool(item_type):
    """Check if an item type is a tool."""
    return item_type in TOOL_DATA


def get_tool_name(tool_type):
    """Get the name of a tool type."""
    return TOOL_DATA.get(tool_type, ("Unknown",))[0]


def get_tool_color(tool_type):
    """Get the color of a tool type."""
    return TOOL_DATA.get(tool_type, ("", BLACK))[1]


def get_tool_damage(tool_type):
    """Get the damage of a tool type."""
    return TOOL_DATA.get(tool_type, ("", BLACK, 1, 1.0))[2]


def get_tool_speed(tool_type):
    """Get the speed multiplier of a tool type."""
    return TOOL_DATA.get(tool_type, ("", BLACK, 1, 1.0))[3]


# Block properties: (name, color, breakable, solid, break_time_seconds)
BLOCK_DATA = {
    BlockType.AIR: ("Air", BLACK, False, False, 0.0),
    BlockType.GRASS: ("Grass", GRASS_COLOR, True, True, 2.0),
    BlockType.DIRT: ("Dirt", DIRT_COLOR, True, True, 2.0),
    BlockType.WOOD: ("Wood", WOOD_COLOR, True, True, 3.0),
    BlockType.LEAVES: ("Leaves", LEAVES_COLOR, True, True, 1.0),
    BlockType.STONE: ("Stone", STONE_COLOR, True, True, 4.0),
    BlockType.PLANKS: ("Planks", PLANKS_COLOR, True, True, 2.0),
    BlockType.DOOR: ("Door", DOOR_COLOR, True, True, 2.0),
    BlockType.PLATFORM: ("Wooden Platform", PLATFORM_COLOR, True, True, 1.0),
    BlockType.TORCH: ("Torch", TORCH_COLOR, True, False, 0.5),  # Torch is breakable, not solid
    # Ores
    BlockType.COAL_ORE: ("Coal Ore", COAL_COLOR, True, True, 3.0),
    BlockType.IRON_ORE: ("Iron Ore", IRON_ORE_COLOR, True, True, 3.5),
    BlockType.GOLD_ORE: ("Gold Ore", GOLD_ORE_COLOR, True, True, 3.5),
    # Furnace
    BlockType.FURNACE: ("Furnace", FURNACE_COLOR, True, True, 5.0),
    # Ingots (items, not world blocks but can be held)
    BlockType.IRON_INGOT: ("Iron Ingot", IRON_INGOT_COLOR, True, False, 0.5),
    BlockType.GOLD_INGOT: ("Gold Ingot", GOLD_INGOT_COLOR, True, False, 0.5),
    # Armor items (leather)
    BlockType.HAT: ("Leather Hat", HAT_COLOR, True, False, 0.5),
    BlockType.BODY_ARMOR: ("Leather Armor", BODY_ARMOR_COLOR, True, False, 0.5),
    BlockType.LEGGINGS: ("Leather Leggings", LEGGINGS_COLOR, True, False, 0.5),
    # Iron armor
    BlockType.IRON_HAT: ("Iron Helmet", IRON_HAT_COLOR, True, False, 0.5),
    BlockType.IRON_BODY_ARMOR: ("Iron Armor", IRON_BODY_ARMOR_COLOR, True, False, 0.5),
    BlockType.IRON_LEGGINGS: ("Iron Leggings", IRON_LEGGINGS_COLOR, True, False, 0.5),
    # Gold armor
    BlockType.GOLD_HAT: ("Gold Helmet", GOLD_HAT_COLOR, True, False, 0.5),
    BlockType.GOLD_BODY_ARMOR: ("Gold Armor", GOLD_BODY_ARMOR_COLOR, True, False, 0.5),
    BlockType.GOLD_LEGGINGS: ("Gold Leggings", GOLD_LEGGINGS_COLOR, True, False, 0.5),
}


def get_block_name(block_type):
    """Get the name of a block type."""
    return BLOCK_DATA.get(block_type, ("Unknown",))[0]


def get_block_color(block_type):
    """Get the color of a block type."""
    return BLOCK_DATA.get(block_type, ("", BLACK))[1]


def is_block_solid(block_type):
    """Check if a block is solid (can collide)."""
    return BLOCK_DATA.get(block_type, (None, None, None, True, 0))[3]


def is_block_breakable(block_type):
    """Check if a block can be broken."""
    return BLOCK_DATA.get(block_type, (None, None, True, None, 0))[2]


def is_block_air(block_type):
    """Check if block is air (empty)."""
    return block_type == BlockType.AIR


def is_block_platform(block_type):
    """Check if block is a platform (one-way collision)."""
    return block_type == BlockType.PLATFORM


def get_break_time(block_type):
    """Get the time in seconds required to break a block with bare hands."""
    return BLOCK_DATA.get(block_type, (None, None, None, None, 1.0))[4]


def get_break_time_with_tool(block_type, tool_type):
    """Get the break time with tool efficiency applied."""
    base_time = get_break_time(block_type)
    
    if tool_type is None or tool_type not in TOOL_EFFICIENCY:
        return base_time
    
    efficiency_map = TOOL_EFFICIENCY.get(tool_type, {})
    multiplier = efficiency_map.get(block_type, 1.0)
    
    return base_time * multiplier


def get_item_name(item_type):
    """Get the name of an item (block, tool, or other item)."""
    if is_tool(item_type):
        return get_tool_name(item_type)
    if item_type in ITEM_DATA:
        return ITEM_DATA[item_type][0]
    return get_block_name(item_type)


def get_item_color(item_type):
    """Get the color of an item (block, tool, or other item)."""
    if is_tool(item_type):
        return get_tool_color(item_type)
    if item_type in ITEM_DATA:
        return ITEM_DATA[item_type][1]
    return get_block_color(item_type)


def is_item(item_type):
    """Check if item_type is a valid item (block, tool, or other item)."""
    return item_type in BLOCK_DATA or item_type in TOOL_DATA or item_type in ITEM_DATA


# Crafting recipes: {result: (result_count, [(ingredient, count), ...], requires_furnace)}
# requires_furnace is optional, defaults to False
# Each recipe produces result_count of result item
CRAFTING_RECIPES = {
    BlockType.PLANKS: (4, [(BlockType.WOOD, 1)]),  # 1 wood -> 4 planks
    BlockType.DOOR: (1, [(BlockType.PLANKS, 6)]),  # 6 planks -> 1 door
    BlockType.PLATFORM: (4, [(BlockType.PLANKS, 2)]),  # 2 planks -> 4 platforms
    BlockType.TORCH: (1, [(BlockType.PLANKS, 1), (BlockType.COAL_ORE, 1)]),  # 1 plank + 1 coal -> 1 torch
    BlockType.FURNACE: (1, [(BlockType.STONE, 8)]),  # 8 stone -> 1 furnace
    # Leather armor crafting
    BlockType.HAT: (1, [(BlockType.PLANKS, 3)]),  # 3 planks -> 1 hat
    BlockType.BODY_ARMOR: (1, [(BlockType.PLANKS, 5)]),  # 5 planks -> 1 body armor
    BlockType.LEGGINGS: (1, [(BlockType.PLANKS, 4)]),  # 4 planks -> 1 leggings
    # Smelting recipes (require furnace nearby)
    BlockType.IRON_INGOT: (1, [(BlockType.IRON_ORE, 1)], True),  # 1 iron ore -> 1 iron ingot (needs furnace)
    BlockType.GOLD_INGOT: (1, [(BlockType.GOLD_ORE, 1)], True),  # 1 gold ore -> 1 gold ingot (needs furnace)
    # Iron tools
    ToolType.IRON_SWORD: (1, [(BlockType.IRON_INGOT, 2)]),  # 2 iron ingots -> 1 iron sword
    ToolType.IRON_PICKAXE: (1, [(BlockType.IRON_INGOT, 3)]),  # 3 iron ingots -> 1 iron pickaxe
    ToolType.IRON_AXE: (1, [(BlockType.IRON_INGOT, 3)]),  # 3 iron ingots -> 1 iron axe
    ToolType.IRON_SHOVEL: (1, [(BlockType.IRON_INGOT, 1)]),  # 1 iron ingot -> 1 iron shovel
    # Gold tools
    ToolType.GOLD_SWORD: (1, [(BlockType.GOLD_INGOT, 2)]),  # 2 gold ingots -> 1 gold sword
    ToolType.GOLD_PICKAXE: (1, [(BlockType.GOLD_INGOT, 3)]),  # 3 gold ingots -> 1 gold pickaxe
    ToolType.GOLD_AXE: (1, [(BlockType.GOLD_INGOT, 3)]),  # 3 gold ingots -> 1 gold axe
    ToolType.GOLD_SHOVEL: (1, [(BlockType.GOLD_INGOT, 1)]),  # 1 gold ingot -> 1 gold shovel
    # Iron armor
    BlockType.IRON_HAT: (1, [(BlockType.IRON_INGOT, 5)]),  # 5 iron ingots -> 1 iron helmet
    BlockType.IRON_BODY_ARMOR: (1, [(BlockType.IRON_INGOT, 8)]),  # 8 iron ingots -> 1 iron armor
    BlockType.IRON_LEGGINGS: (1, [(BlockType.IRON_INGOT, 7)]),  # 7 iron ingots -> 1 iron leggings
    # Gold armor
    BlockType.GOLD_HAT: (1, [(BlockType.GOLD_INGOT, 5)]),  # 5 gold ingots -> 1 gold helmet
    BlockType.GOLD_BODY_ARMOR: (1, [(BlockType.GOLD_INGOT, 8)]),  # 8 gold ingots -> 1 gold armor
    BlockType.GOLD_LEGGINGS: (1, [(BlockType.GOLD_INGOT, 7)]),  # 7 gold ingots -> 1 gold leggings
}


def get_craftable_items(inventory_items, near_furnace=False):
    """Get list of items that can be crafted with given inventory.
    
    inventory_items: dict of {item_type: count}
    near_furnace: bool, whether player is near a furnace (for smelting recipes)
    Returns: list of (result_item, result_count, ingredients_list)
    """
    craftable = []
    for result_item, recipe_data in CRAFTING_RECIPES.items():
        # Handle both old format (2 elements) and new format (3 elements)
        if len(recipe_data) == 3:
            result_count, ingredients, requires_furnace = recipe_data
        else:
            result_count, ingredients = recipe_data
            requires_furnace = False
        
        # Skip furnace recipes if not near furnace
        if requires_furnace and not near_furnace:
            continue
            
        can_craft = True
        for ingredient, needed_count in ingredients:
            have_count = inventory_items.get(ingredient, 0)
            if have_count < needed_count:
                can_craft = False
                break
        if can_craft:
            craftable.append((result_item, result_count, ingredients))
    return craftable
