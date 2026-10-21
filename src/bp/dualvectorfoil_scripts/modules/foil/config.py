# -*- coding: utf-8 -*-
# =================================================
#  ⠀
#   Author: Nuoyan <https://github.com/charminglee>
#   Email : 1279735247@qq.com
#   Date  : 2026-10-21
#  ⠀
# =================================================


from ...common.config import FOIL_BLOCKS_PER_TICK, MAX_FOIL_BLOCKS, MAX_FOIL_ENTITIES


# 统一资源标识与持久化键。
ITEM = "nuoyan:foil"
PROJECTILE = "nuoyan:foil_projectile"
ATTR = "nuoyan:flat"
STATE_KEY = "nuoyan:world_v2"
PAGE_PREFIX = "nuoyan:plane_v2:"

# 系统名称、执行间隔和世界边界。
SERVER_NAME = "FoilServer"
CLIENT_NAME = "FoilClient"
ENTITY_INTERVAL = 10
SAVE_INTERVAL = 90
FUSE_TICKS = 60
LAUNCH_COOLDOWN = 30
LOAD_PADDING = 80
WORLD_LIMIT = 29999900

# 网易 3.10 默认维度的可放置范围；自定义维度必须在此明确配置。
HEIGHTS = {0: (-64, 319), 1: (0, 127), 2: (0, 255)}

# 空气方块的最小快照。
AIR = {'name': "minecraft:air", 'aux': 0}


# >>> GENERATED ENTITY CATALOG; tools/build_geometry.py replaces this block.
GEOMETRIES = {
    'geometry.agent': "geometry.nuoyan.flat.agent",
    'geometry.allay': "geometry.nuoyan.flat.allay",
    'geometry.armadillo': "geometry.nuoyan.flat.armadillo",
    'geometry.armor_stand': "geometry.nuoyan.flat.armor_stand",
    'geometry.arrow': "geometry.nuoyan.flat.arrow",
    'geometry.axolotl': "geometry.nuoyan.flat.axolotl",
    'geometry.bat': "geometry.nuoyan.flat.bat",
    'geometry.bat_v2': "geometry.nuoyan.flat.bat_v2",
    'geometry.bed': "geometry.nuoyan.flat.bed",
    'geometry.bee': "geometry.nuoyan.flat.bee",
    'geometry.blaze': "geometry.nuoyan.flat.blaze",
    'geometry.bogged.armor': "geometry.nuoyan.flat.bogged.armor",
    'geometry.breeze': "geometry.nuoyan.flat.breeze",
    'geometry.breeze_eyes': "geometry.nuoyan.flat.breeze_eyes",
    'geometry.breeze_wind_bottom': "geometry.nuoyan.flat.breeze_wind_bottom",
    'geometry.breeze_wind_mid': "geometry.nuoyan.flat.breeze_wind_mid",
    'geometry.breeze_wind_top': "geometry.nuoyan.flat.breeze_wind_top",
    'geometry.camel': "geometry.nuoyan.flat.camel",
    'geometry.camel_husk': "geometry.nuoyan.flat.camel_husk",
    'geometry.cape': "geometry.nuoyan.flat.cape",
    'geometry.cat': "geometry.nuoyan.flat.cat",
    'geometry.chalkboard_large': "geometry.nuoyan.flat.chalkboard_large",
    'geometry.chalkboard_medium': "geometry.nuoyan.flat.chalkboard_medium",
    'geometry.chalkboard_small': "geometry.nuoyan.flat.chalkboard_small",
    'geometry.chicken': "geometry.nuoyan.flat.chicken",
    'geometry.chicken.cold': "geometry.nuoyan.flat.chicken.cold",
    'geometry.chicken.v1.12': "geometry.nuoyan.flat.chicken.v1.12",
    'geometry.cod': "geometry.nuoyan.flat.cod",
    'geometry.copper_golem': "geometry.nuoyan.flat.copper_golem",
    'geometry.copper_golem.flower': "geometry.nuoyan.flat.copper_golem.flower",
    'geometry.copper_golem.running': "geometry.nuoyan.flat.copper_golem.running",
    'geometry.copper_golem.sitting': "geometry.nuoyan.flat.copper_golem.sitting",
    'geometry.copper_golem.star': "geometry.nuoyan.flat.copper_golem.star",
    'geometry.cow': "geometry.nuoyan.flat.cow",
    'geometry.cow.cold': "geometry.nuoyan.flat.cow.cold",
    'geometry.cow.v1.8': "geometry.nuoyan.flat.cow.v1.8",
    'geometry.cow.v2': "geometry.nuoyan.flat.cow.v2",
    'geometry.cow.warm': "geometry.nuoyan.flat.cow.warm",
    'geometry.creaking': "geometry.nuoyan.flat.creaking",
    'geometry.creeper': "geometry.nuoyan.flat.creeper",
    'geometry.creeper.charged': "geometry.nuoyan.flat.creeper.charged",
    'geometry.creeper.charged.v1.8': "geometry.nuoyan.flat.creeper.charged.v1.8",
    'geometry.creeper.v1.8': "geometry.nuoyan.flat.creeper.v1.8",
    'geometry.dolphin': "geometry.nuoyan.flat.dolphin",
    'geometry.dragon': "geometry.nuoyan.flat.dragon",
    'geometry.dragon_head': "geometry.nuoyan.flat.dragon_head",
    'geometry.elytra': "geometry.nuoyan.flat.elytra",
    'geometry.ender_crystal': "geometry.nuoyan.flat.ender_crystal",
    'geometry.enderman': "geometry.nuoyan.flat.enderman",
    'geometry.enderman.v1.8': "geometry.nuoyan.flat.enderman.v1.8",
    'geometry.endermite': "geometry.nuoyan.flat.endermite",
    'geometry.evocation_fang': "geometry.nuoyan.flat.evocation_fang",
    'geometry.evoker': "geometry.nuoyan.flat.evoker",
    'geometry.evoker.v1.8': "geometry.nuoyan.flat.evoker.v1.8",
    'geometry.experience_orb': "geometry.nuoyan.flat.experience_orb",
    'geometry.fireball': "geometry.nuoyan.flat.fireball",
    'geometry.fireworks_rocket': "geometry.nuoyan.flat.fireworks_rocket",
    'geometry.fishing_hook': "geometry.nuoyan.flat.fishing_hook",
    'geometry.fox': "geometry.nuoyan.flat.fox",
    'geometry.frog': "geometry.nuoyan.flat.frog",
    'geometry.ghast': "geometry.nuoyan.flat.ghast",
    'geometry.glow_squid': "geometry.nuoyan.flat.glow_squid",
    'geometry.goat': "geometry.nuoyan.flat.goat",
    'geometry.guardian': "geometry.nuoyan.flat.guardian",
    'geometry.guardian.v1.8': "geometry.nuoyan.flat.guardian.v1.8",
    'geometry.happy_ghast': "geometry.nuoyan.flat.happy_ghast",
    'geometry.happy_ghast_ropes': "geometry.nuoyan.flat.happy_ghast_ropes",
    'geometry.harness': "geometry.nuoyan.flat.harness",
    'geometry.hoglin': "geometry.nuoyan.flat.hoglin",
    'geometry.horse': "geometry.nuoyan.flat.horse",
    'geometry.horse.v2': "geometry.nuoyan.flat.horse.v2",
    'geometry.horse.v3': "geometry.nuoyan.flat.horse.v3",
    'geometry.humanoid': "geometry.nuoyan.flat.humanoid",
    'geometry.humanoid.armor.boots': "geometry.nuoyan.flat.humanoid.armor.boots",
    'geometry.humanoid.armor.chestplate': "geometry.nuoyan.flat.humanoid.armor.chestplate",
    'geometry.humanoid.armor.helmet': "geometry.nuoyan.flat.humanoid.armor.helmet",
    'geometry.humanoid.armor.leggings': "geometry.nuoyan.flat.humanoid.armor.leggings",
    'geometry.humanoid.armor1': "geometry.nuoyan.flat.humanoid.armor1",
    'geometry.humanoid.armor2': "geometry.nuoyan.flat.humanoid.armor2",
    'geometry.humanoid.custom': "geometry.nuoyan.flat.humanoid.custom",
    'geometry.humanoid.customSlim': "geometry.nuoyan.flat.humanoid.customSlim",
    'geometry.irongolem': "geometry.nuoyan.flat.irongolem",
    'geometry.item_sprite': "geometry.nuoyan.flat.item_sprite",
    'geometry.lavaslime': "geometry.nuoyan.flat.lavaslime",
    'geometry.leash_knot': "geometry.nuoyan.flat.leash_knot",
    'geometry.llama': "geometry.nuoyan.flat.llama",
    'geometry.llama.v1.8': "geometry.nuoyan.flat.llama.v1.8",
    'geometry.llamaspit': "geometry.nuoyan.flat.llamaspit",
    'geometry.magma_cube_v2': "geometry.nuoyan.flat.magma_cube_v2",
    'geometry.minecart': "geometry.nuoyan.flat.minecart",
    'geometry.minecart.v1.8': "geometry.nuoyan.flat.minecart.v1.8",
    'geometry.mob_head': "geometry.nuoyan.flat.mob_head",
    'geometry.mooshroom': "geometry.nuoyan.flat.mooshroom",
    'geometry.mooshroom.v1.8': "geometry.nuoyan.flat.mooshroom.v1.8",
    'geometry.mooshroom.v2': "geometry.nuoyan.flat.mooshroom.v2",
    'geometry.nautilus': "geometry.nuoyan.flat.nautilus",
    'geometry.nautilus.baby': "geometry.nuoyan.flat.nautilus.baby",
    'geometry.nautilus_armor': "geometry.nuoyan.flat.nautilus_armor",
    'geometry.nautilus_saddle': "geometry.nuoyan.flat.nautilus_saddle",
    'geometry.npc': "geometry.nuoyan.flat.npc",
    'geometry.ocelot': "geometry.nuoyan.flat.ocelot",
    'geometry.ocelot.v1.8': "geometry.nuoyan.flat.ocelot.v1.8",
    'geometry.panda': "geometry.nuoyan.flat.panda",
    'geometry.parched': "geometry.nuoyan.flat.parched",
    'geometry.parrot': "geometry.nuoyan.flat.parrot",
    'geometry.phantom': "geometry.nuoyan.flat.phantom",
    'geometry.pig': "geometry.nuoyan.flat.pig",
    'geometry.pig.v1.8': "geometry.nuoyan.flat.pig.v1.8",
    'geometry.pig.v3': "geometry.nuoyan.flat.pig.v3",
    'geometry.piglin': "geometry.nuoyan.flat.piglin",
    'geometry.pigzombie': "geometry.nuoyan.flat.pigzombie",
    'geometry.pigzombie.baby': "geometry.nuoyan.flat.pigzombie.baby",
    'geometry.pigzombie.baby.v1.8': "geometry.nuoyan.flat.pigzombie.baby.v1.8",
    'geometry.pigzombie.v1.8': "geometry.nuoyan.flat.pigzombie.v1.8",
    'geometry.pillager': "geometry.nuoyan.flat.pillager",
    'geometry.player.armor.base': "geometry.nuoyan.flat.player.armor.base",
    'geometry.player.armor.boots': "geometry.nuoyan.flat.player.armor.boots",
    'geometry.player.armor.chestplate': "geometry.nuoyan.flat.player.armor.chestplate",
    'geometry.player.armor.helmet': "geometry.nuoyan.flat.player.armor.helmet",
    'geometry.player.armor.leggings': "geometry.nuoyan.flat.player.armor.leggings",
    'geometry.player.armor1': "geometry.nuoyan.flat.player.armor1",
    'geometry.player.armor2': "geometry.nuoyan.flat.player.armor2",
    'geometry.player_head': "geometry.nuoyan.flat.player_head",
    'geometry.polarbear': "geometry.nuoyan.flat.polarbear",
    'geometry.pufferfish.large': "geometry.nuoyan.flat.pufferfish.large",
    'geometry.pufferfish.large.v1.8': "geometry.nuoyan.flat.pufferfish.large.v1.8",
    'geometry.pufferfish.mid': "geometry.nuoyan.flat.pufferfish.mid",
    'geometry.pufferfish.mid.v1.8': "geometry.nuoyan.flat.pufferfish.mid.v1.8",
    'geometry.pufferfish.small': "geometry.nuoyan.flat.pufferfish.small",
    'geometry.pufferfish.small.v1.8': "geometry.nuoyan.flat.pufferfish.small.v1.8",
    'geometry.quadruped': "geometry.nuoyan.flat.quadruped",
    'geometry.rabbit': "geometry.nuoyan.flat.rabbit",
    'geometry.rabbit.v1.8': "geometry.nuoyan.flat.rabbit.v1.8",
    'geometry.ravager': "geometry.nuoyan.flat.ravager",
    'geometry.salmon': "geometry.nuoyan.flat.salmon",
    'geometry.sheep': "geometry.nuoyan.flat.sheep",
    'geometry.sheep.sheared': "geometry.nuoyan.flat.sheep.sheared",
    'geometry.sheep.sheared.v1.8': "geometry.nuoyan.flat.sheep.sheared.v1.8",
    'geometry.sheep.v1.8': "geometry.nuoyan.flat.sheep.v1.8",
    'geometry.shield': "geometry.nuoyan.flat.shield",
    'geometry.shulker': "geometry.nuoyan.flat.shulker",
    'geometry.shulker.v1.8': "geometry.nuoyan.flat.shulker.v1.8",
    'geometry.shulker_bullet': "geometry.nuoyan.flat.shulker_bullet",
    'geometry.silverfish': "geometry.nuoyan.flat.silverfish",
    'geometry.skeleton': "geometry.nuoyan.flat.skeleton",
    'geometry.skeleton.bogged': "geometry.nuoyan.flat.skeleton.bogged",
    'geometry.skeleton.stray': "geometry.nuoyan.flat.skeleton.stray",
    'geometry.skeleton.stray.v1.8': "geometry.nuoyan.flat.skeleton.stray.v1.8",
    'geometry.skeleton.v1.8': "geometry.nuoyan.flat.skeleton.v1.8",
    'geometry.skeleton.wither': "geometry.nuoyan.flat.skeleton.wither",
    'geometry.skeleton.wither.v1.8': "geometry.nuoyan.flat.skeleton.wither.v1.8",
    'geometry.slime': "geometry.nuoyan.flat.slime",
    'geometry.slime.armor': "geometry.nuoyan.flat.slime.armor",
    'geometry.sniffer': "geometry.nuoyan.flat.sniffer",
    'geometry.snowgolem': "geometry.nuoyan.flat.snowgolem",
    'geometry.snowgolem.v1.8': "geometry.nuoyan.flat.snowgolem.v1.8",
    'geometry.spider': "geometry.nuoyan.flat.spider",
    'geometry.spider.v1.8': "geometry.nuoyan.flat.spider.v1.8",
    'geometry.spyglass': "geometry.nuoyan.flat.spyglass",
    'geometry.squid': "geometry.nuoyan.flat.squid",
    'geometry.stray.armor': "geometry.nuoyan.flat.stray.armor",
    'geometry.stray.armor.v1.8': "geometry.nuoyan.flat.stray.armor.v1.8",
    'geometry.strider': "geometry.nuoyan.flat.strider",
    'geometry.tadpole': "geometry.nuoyan.flat.tadpole",
    'geometry.trident': "geometry.nuoyan.flat.trident",
    'geometry.tripod_camera': "geometry.nuoyan.flat.tripod_camera",
    'geometry.tropicalfish_a': "geometry.nuoyan.flat.tropicalfish_a",
    'geometry.tropicalfish_b': "geometry.nuoyan.flat.tropicalfish_b",
    'geometry.turtle': "geometry.nuoyan.flat.turtle",
    'geometry.vex': "geometry.nuoyan.flat.vex",
    'geometry.vex.v1.8': "geometry.nuoyan.flat.vex.v1.8",
    'geometry.villager': "geometry.nuoyan.flat.villager",
    'geometry.villager.v1.8': "geometry.nuoyan.flat.villager.v1.8",
    'geometry.villager.witch': "geometry.nuoyan.flat.villager.witch",
    'geometry.villager.witch.v1.8': "geometry.nuoyan.flat.villager.witch.v1.8",
    'geometry.villager_v2': "geometry.nuoyan.flat.villager_v2",
    'geometry.vindicator': "geometry.nuoyan.flat.vindicator",
    'geometry.vindicator.v1.8': "geometry.nuoyan.flat.vindicator.v1.8",
    'geometry.warden': "geometry.nuoyan.flat.warden",
    'geometry.wind_charge': "geometry.nuoyan.flat.wind_charge",
    'geometry.witherBoss': "geometry.nuoyan.flat.witherBoss",
    'geometry.witherBoss.armor': "geometry.nuoyan.flat.witherBoss.armor",
    'geometry.witherBoss.armor.v1.8': "geometry.nuoyan.flat.witherBoss.armor.v1.8",
    'geometry.wither_skull': "geometry.nuoyan.flat.wither_skull",
    'geometry.wolf': "geometry.nuoyan.flat.wolf",
    'geometry.wolf.armor': "geometry.nuoyan.flat.wolf.armor",
    'geometry.zombie': "geometry.nuoyan.flat.zombie",
    'geometry.zombie.drowned': "geometry.nuoyan.flat.zombie.drowned",
    'geometry.zombie.drowned.v1.16': "geometry.nuoyan.flat.zombie.drowned.v1.16",
    'geometry.zombie.husk': "geometry.nuoyan.flat.zombie.husk",
    'geometry.zombie.husk.v1.8': "geometry.nuoyan.flat.zombie.husk.v1.8",
    'geometry.zombie.v1.8': "geometry.nuoyan.flat.zombie.v1.8",
    'geometry.zombie.villager': "geometry.nuoyan.flat.zombie.villager",
    'geometry.zombie.villager.v1.8': "geometry.nuoyan.flat.zombie.villager.v1.8",
    'geometry.zombie.villager_v2': "geometry.nuoyan.flat.zombie.villager_v2",
    'geometry.zombie_nautilus_coral': "geometry.nuoyan.flat.zombie_nautilus_coral",
}

ENTITY_GEOMETRIES = {
    'minecraft:agent': {
        'default': "geometry.agent",
    },
    'minecraft:allay': {
        'default': "geometry.allay",
    },
    'minecraft:armadillo': {
        'default': "geometry.armadillo",
    },
    'minecraft:armor_stand': {
        'default': "geometry.armor_stand",
    },
    'minecraft:arrow': {
        'default': "geometry.arrow",
    },
    'minecraft:axolotl': {
        'default': "geometry.axolotl",
    },
    'minecraft:bat': {
        'default': "geometry.bat_v2",
    },
    'minecraft:bed': {
        'default': "geometry.bed",
    },
    'minecraft:bee': {
        'default': "geometry.bee",
    },
    'minecraft:blaze': {
        'default': "geometry.blaze",
    },
    'minecraft:bogged': {
        'default': "geometry.skeleton.bogged",
        'overlay': "geometry.bogged.armor",
    },
    'minecraft:breeze': {
        'breeze_eyes': "geometry.breeze_eyes",
        'breeze_wind_bottom': "geometry.breeze_wind_bottom",
        'breeze_wind_mid': "geometry.breeze_wind_mid",
        'breeze_wind_top': "geometry.breeze_wind_top",
        'default': "geometry.breeze",
    },
    'minecraft:breeze_wind_charge_projectile': {
        'default': "geometry.wind_charge",
    },
    'minecraft:camel': {
        'default': "geometry.camel",
    },
    'minecraft:camel_husk': {
        'default': "geometry.camel_husk",
    },
    'minecraft:cat': {
        'default': "geometry.cat",
    },
    'minecraft:cave_spider': {
        'default': "geometry.spider",
    },
    'minecraft:chest_minecart': {
        'default': "geometry.minecart",
    },
    'minecraft:chicken': {
        'default': "geometry.chicken",
    },
    'minecraft:cod': {
        'default': "geometry.cod",
    },
    'minecraft:command_block_minecart': {
        'default': "geometry.minecart",
    },
    'minecraft:copper_golem': {
        'default': "geometry.copper_golem",
        'flower': "geometry.copper_golem.flower",
        'running': "geometry.copper_golem.running",
        'sitting': "geometry.copper_golem.sitting",
        'standing': "geometry.copper_golem",
        'star': "geometry.copper_golem.star",
    },
    'minecraft:cow': {
        'default': "geometry.cow",
    },
    'minecraft:creaking': {
        'default': "geometry.creaking",
    },
    'minecraft:creeper': {
        'charged': "geometry.creeper.charged",
        'default': "geometry.creeper",
    },
    'minecraft:dolphin': {
        'default': "geometry.dolphin",
    },
    'minecraft:donkey': {
        'default': "geometry.horse.v3",
    },
    'minecraft:dragon_fireball': {
        'default': "geometry.fireball",
    },
    'minecraft:drowned': {
        'default': "geometry.zombie.drowned",
    },
    'minecraft:egg': {
        'default': "geometry.item_sprite",
    },
    'minecraft:elder_guardian': {
        'default': "geometry.guardian",
        'ghost': "geometry.guardian",
    },
    'minecraft:ender_crystal': {
        'default': "geometry.ender_crystal",
    },
    'minecraft:ender_dragon': {
        'default': "geometry.dragon",
    },
    'minecraft:ender_pearl': {
        'default': "geometry.item_sprite",
    },
    'minecraft:enderman': {
        'default': "geometry.enderman",
    },
    'minecraft:endermite': {
        'default': "geometry.endermite",
    },
    'minecraft:evocation_fang': {
        'default': "geometry.evocation_fang",
    },
    'minecraft:evocation_illager': {
        'default': "geometry.evoker",
    },
    'minecraft:eye_of_ender_signal': {
        'default': "geometry.item_sprite",
    },
    'minecraft:fireball': {
        'default': "geometry.fireball",
    },
    'minecraft:fireworks_rocket': {
        'default': "geometry.fireworks_rocket",
    },
    'minecraft:fishing_hook': {
        'default': "geometry.fishing_hook",
    },
    'minecraft:fox': {
        'default': "geometry.fox",
    },
    'minecraft:frog': {
        'default': "geometry.frog",
    },
    'minecraft:ghast': {
        'default': "geometry.ghast",
    },
    'minecraft:glow_squid': {
        'default': "geometry.squid",
    },
    'minecraft:goat': {
        'default': "geometry.goat",
    },
    'minecraft:guardian': {
        'default': "geometry.guardian",
        'ghost': "geometry.guardian",
    },
    'minecraft:happy_ghast': {
        'default': "geometry.happy_ghast",
        'ropes': "geometry.happy_ghast_ropes",
    },
    'minecraft:hoglin': {
        'default': "geometry.hoglin",
    },
    'minecraft:hopper_minecart': {
        'default': "geometry.minecart",
    },
    'minecraft:horse': {
        'default': "geometry.horse.v3",
    },
    'minecraft:husk': {
        'default': "geometry.zombie.husk",
    },
    'minecraft:iron_golem': {
        'default': "geometry.irongolem",
    },
    'minecraft:leash_knot': {
        'default': "geometry.leash_knot",
    },
    'minecraft:lingering_potion': {
        'default': "geometry.item_sprite",
    },
    'minecraft:llama': {
        'default': "geometry.llama",
    },
    'minecraft:llama_spit': {
        'default': "geometry.llamaspit",
    },
    'minecraft:magma_cube': {
        'default': "geometry.magma_cube_v2",
    },
    'minecraft:minecart': {
        'default': "geometry.minecart",
    },
    'minecraft:mooshroom': {
        'default': "geometry.mooshroom",
    },
    'minecraft:mule': {
        'default': "geometry.horse.v3",
    },
    'minecraft:nautilus': {
        'armor': "geometry.nautilus_armor",
        'baby': "geometry.nautilus.baby",
        'default': "geometry.nautilus",
        'saddle': "geometry.nautilus_saddle",
    },
    'minecraft:npc': {
        'default': "geometry.npc",
    },
    'minecraft:ocelot': {
        'default': "geometry.ocelot",
    },
    'minecraft:panda': {
        'default': "geometry.panda",
    },
    'minecraft:parched': {
        'default': "geometry.parched",
    },
    'minecraft:parrot': {
        'default': "geometry.parrot",
    },
    'minecraft:phantom': {
        'default': "geometry.phantom",
    },
    'minecraft:pig': {
        'default': "geometry.pig",
    },
    'minecraft:piglin': {
        'default': "geometry.piglin",
    },
    'minecraft:piglin_brute': {
        'default': "geometry.piglin",
    },
    'minecraft:pillager': {
        'default': "geometry.pillager",
    },
    'minecraft:player': {
        'cape': "geometry.cape",
        'default': "geometry.humanoid.custom",
    },
    'minecraft:polar_bear': {
        'default': "geometry.polarbear",
    },
    'minecraft:pufferfish': {
        'default': "geometry.pufferfish.small",
        'large': "geometry.pufferfish.large",
        'mid': "geometry.pufferfish.mid",
    },
    'minecraft:rabbit': {
        'default': "geometry.rabbit",
    },
    'minecraft:ravager': {
        'default': "geometry.ravager",
    },
    'minecraft:salmon': {
        'default': "geometry.salmon",
    },
    'minecraft:sheep': {
        'default': "geometry.sheep",
        'sheared': "geometry.sheep.sheared",
    },
    'minecraft:shulker': {
        'default': "geometry.shulker",
    },
    'minecraft:shulker_bullet': {
        'default': "geometry.shulker_bullet",
    },
    'minecraft:silverfish': {
        'default': "geometry.silverfish",
    },
    'minecraft:skeleton': {
        'default': "geometry.skeleton",
    },
    'minecraft:skeleton_horse': {
        'default': "geometry.horse.v3",
    },
    'minecraft:skull': {
        'creeper': "geometry.mob_head",
        'default': "geometry.player_head",
        'dragon': "geometry.dragon_head",
        'piglin': "geometry.piglin",
        'skeleton': "geometry.mob_head",
        'steve': "geometry.player_head",
        'wither': "geometry.mob_head",
        'zombie': "geometry.mob_head",
    },
    'minecraft:slime': {
        'armor': "geometry.slime.armor",
        'default': "geometry.slime",
    },
    'minecraft:small_fireball': {
        'default': "geometry.fireball",
    },
    'minecraft:sniffer': {
        'default': "geometry.sniffer",
    },
    'minecraft:snow_golem': {
        'default': "geometry.snowgolem",
    },
    'minecraft:snowball': {
        'default': "geometry.item_sprite",
    },
    'minecraft:spider': {
        'default': "geometry.spider",
    },
    'minecraft:splash_potion': {
        'default': "geometry.item_sprite",
    },
    'minecraft:squid': {
        'default': "geometry.squid",
    },
    'minecraft:stray': {
        'default': "geometry.skeleton.stray",
        'overlay': "geometry.stray.armor",
    },
    'minecraft:strider': {
        'default': "geometry.strider",
    },
    'minecraft:tadpole': {
        'default': "geometry.tadpole",
    },
    'minecraft:thrown_trident': {
        'default': "geometry.trident",
    },
    'minecraft:tnt_minecart': {
        'default': "geometry.minecart",
    },
    'minecraft:trader_llama': {
        'default': "geometry.llama.v1.8",
    },
    'minecraft:tripod_camera': {
        'default': "geometry.tripod_camera",
    },
    'minecraft:tropicalfish': {
        'typeA': "geometry.tropicalfish_a",
        'typeB': "geometry.tropicalfish_b",
    },
    'minecraft:turtle': {
        'default': "geometry.turtle",
    },
    'minecraft:vex': {
        'default': "geometry.vex",
    },
    'minecraft:villager': {
        'default': "geometry.villager",
    },
    'minecraft:villager_v2': {
        'default': "geometry.villager_v2",
    },
    'minecraft:vindicator': {
        'default': "geometry.vindicator",
    },
    'minecraft:wandering_trader': {
        'default': "geometry.villager_v2",
    },
    'minecraft:warden': {
        'default': "geometry.warden",
    },
    'minecraft:wind_charge_projectile': {
        'default': "geometry.wind_charge",
    },
    'minecraft:witch': {
        'default': "geometry.villager.witch",
    },
    'minecraft:wither': {
        'armor': "geometry.witherBoss.armor",
        'default': "geometry.witherBoss",
    },
    'minecraft:wither_skeleton': {
        'default': "geometry.skeleton.wither",
    },
    'minecraft:wither_skull': {
        'default': "geometry.wither_skull",
    },
    'minecraft:wither_skull_dangerous': {
        'default': "geometry.wither_skull",
    },
    'minecraft:wolf': {
        'default': "geometry.wolf",
    },
    'minecraft:xp_bottle': {
        'default': "geometry.item_sprite",
    },
    'minecraft:xp_orb': {
        'default': "geometry.experience_orb",
    },
    'minecraft:zoglin': {
        'default': "geometry.hoglin",
    },
    'minecraft:zombie': {
        'default': "geometry.zombie",
    },
    'minecraft:zombie_horse': {
        'default': "geometry.horse.v3",
    },
    'minecraft:zombie_nautilus': {
        'armor': "geometry.nautilus_armor",
        'coral': "geometry.zombie_nautilus_coral",
        'default': "geometry.nautilus",
        'saddle': "geometry.nautilus_saddle",
    },
    'minecraft:zombie_pigman': {
        'baby': "geometry.pigzombie.baby",
        'default': "geometry.pigzombie",
    },
    'minecraft:zombie_villager': {
        'default': "geometry.zombie.villager",
    },
    'minecraft:zombie_villager_v2': {
        'default': "geometry.zombie.villager_v2",
    },
}
# <<< END GENERATED ENTITY CATALOG
