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


class ToolType:
    """Represents a type of tool."""
    SWORD = 100
    PICKAXE = 101
    AXE = 102
    SHOVEL = 103
    BOW = 104


class ItemType:
    """Represents non-block, non-tool items."""
    ARROW = 200


# Colors for new items
PLANKS_COLOR = (180, 140, 80)
DOOR_COLOR = (139, 90, 43)
BOW_COLOR = (139, 90, 43)
ARROW_COLOR = (150, 150, 150)


# Tool properties: (name, color)
TOOL_DATA = {
    ToolType.SWORD: ("Sword", SWORD_COLOR),
    ToolType.PICKAXE: ("Pickaxe", PICKAXE_COLOR),
    ToolType.AXE: ("Axe", AXE_COLOR),
    ToolType.SHOVEL: ("Shovel", SHOVEL_COLOR),
    ToolType.BOW: ("Bow", BOW_COLOR),
}

# Other item properties: (name, color)
ITEM_DATA = {
    ItemType.ARROW: ("Arrow", ARROW_COLOR),
}

# Tool efficiency multipliers for different block types
# Lower value = faster breaking
TOOL_EFFICIENCY = {
    ToolType.SWORD: {},  # No efficiency bonus
    ToolType.PICKAXE: {BlockType.STONE: 0.25},  # Stone breaks 4x faster
    ToolType.AXE: {BlockType.WOOD: 0.25, BlockType.LEAVES: 0.25, BlockType.PLANKS: 0.25, BlockType.DOOR: 0.25},  # Wood/leaves/planks/doors break 4x faster
    ToolType.SHOVEL: {BlockType.GRASS: 0.25, BlockType.DIRT: 0.25},  # Dirt/grass breaks 4x faster
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


# Crafting recipes: {result: (result_count, [(ingredient, count), ...])}
# Each recipe produces result_count of result item
CRAFTING_RECIPES = {
    BlockType.PLANKS: (4, [(BlockType.WOOD, 1)]),  # 1 wood -> 4 planks
    BlockType.DOOR: (1, [(BlockType.PLANKS, 6)]),  # 6 planks -> 1 door
}


def get_craftable_items(inventory_items):
    """Get list of items that can be crafted with given inventory.
    
    inventory_items: dict of {item_type: count}
    Returns: list of (result_item, result_count, ingredients_list)
    """
    craftable = []
    for result_item, (result_count, ingredients) in CRAFTING_RECIPES.items():
        can_craft = True
        for ingredient, needed_count in ingredients:
            have_count = inventory_items.get(ingredient, 0)
            if have_count < needed_count:
                can_craft = False
                break
        if can_craft:
            craftable.append((result_item, result_count, ingredients))
    return craftable
