import sc2
from sc2 import run_game, maps, Race, Difficulty
from sc2.player import Bot, Computer
from sc2.constants import NEXUS, PROBE, PYLON, ASSIMILATOR, GATEWAY, CYBERNETICSCORE, STALKER, STARGATE, VOIDRAY
import random
import cv2
import numpy as np


class SentdeBot(sc2.BotAI):
    def __init__(self):
        self.ITERATIONS_PER_MINUTE = 165
        self.MAX_WORKERS = 80
        self.PROBES_PER_NEXUS = 40

    async def on_step(self, iteration):
        self.iteration = iteration
        await self.distribute_workers()
        await self.build_workers()
        await self.build_assimilators()
        await self.build_pylon()
        await self.offensive_force_buildings()
        await self.build_offensive_force()
        await self.expand()
        await self.attack()
        await self.intel()

    async def intel(self):
        game_data = np.zeros((self.game_info.map_size[1], self.game_info.map_size[0], 3), np.uint8)
        for nexus in self.units(NEXUS):
            nex_pos = nexus.position
            cv2.circle(game_data, (int(nex_pos[0]), int(nex_pos[1])), 10, (0, 255, 0), -1)

        flipped = cv2.flip(game_data, 0)
        resized = cv2.resize(flipped, dsize=None, fx=2, fy=2)
        cv2.imshow('Intel', resized)
        cv2.waitKey(1)

    async def build_workers(self):
        num_probes = len(self.units(PROBE)) + len(self.units(ASSIMILATOR))
        num_nexus = len(self.units(NEXUS))
        if num_probes < self.MAX_WORKERS and num_probes < num_nexus * self.PROBES_PER_NEXUS:
            for nexus in self.units(NEXUS).ready.idle:
                if self.can_afford(PROBE):
                    await self.do(nexus.train(PROBE))

    async def build_pylon(self):
        if self.supply_left < 5:
            for nexus in self.units(NEXUS).ready:
                if self.can_afford(PYLON) and not self.already_pending(PYLON):
                    await self.build(PYLON, near=nexus, placement_step=6, max_distance=20)

    async def build_assimilators(self):
        for nexus in self.units(NEXUS).ready:
            vaspenes = self.state.vespene_geyser.closer_than(20, nexus)
            for vaspene in vaspenes:
                worker = self.select_build_worker(vaspene.position)
                if worker is None:
                    break
                if not self.units(ASSIMILATOR).closer_than(1.0, vaspene).exists:
                    if self.can_afford(ASSIMILATOR):
                        await self.do(worker.build(ASSIMILATOR, vaspene))

    async def expand(self):
        if (self.can_afford(NEXUS)
                and len(self.units(NEXUS).ready) < 3):
            await self.expand_now(max_distance=25)

    async def offensive_force_buildings(self):
        for nexus in self.units(NEXUS).ready:
            if self.units(GATEWAY).ready.exists and not self.units(CYBERNETICSCORE):
                if self.can_afford(CYBERNETICSCORE) and not self.already_pending(CYBERNETICSCORE):
                    await self.build(CYBERNETICSCORE, near=nexus)
            elif len(self.units(GATEWAY)) < 1:
                if self.can_afford(GATEWAY) and not self.already_pending(GATEWAY):
                    await self.build(GATEWAY, near=nexus)

            if self.units(CYBERNETICSCORE).ready.exists:
                if len(self.units(STARGATE)) < (self.iteration / self.ITERATIONS_PER_MINUTE):
                    if self.can_afford(STARGATE) and not self.already_pending(STARGATE):
                        await self.build(STARGATE, near=nexus)

    async def build_offensive_force(self):
        for sg in self.units(STARGATE).ready.idle:
            if self.can_afford(VOIDRAY) and self.supply_left > 0:
                await self.do(sg.train(VOIDRAY))

    def find_target(self):
        if len(self.known_enemy_units) > 0:
            return random.choice(self.known_enemy_units)
        elif len(self.known_enemy_structures) > 0:
            return random.choice(self.known_enemy_structures)
        else:
            return self.enemy_start_locations[0]

    async def attack(self):
        # {UNIT: [n to fight, n to defend]}
        aggressive_units = {VOIDRAY: [15, 3]}

        for UNIT in aggressive_units:
            if self.units(UNIT).amount >= aggressive_units[UNIT][0]:
                for s in self.units(UNIT).idle:
                    await self.do(s.attack(self.find_target()))
            elif self.units(UNIT).amount >= aggressive_units[UNIT][1]:
                if len(self.known_enemy_units) > 0:
                    for s in self.units(UNIT).idle:
                        await self.do(s.attack(random.choice(self.known_enemy_units)))


run_game(maps.get("AbyssalReefLE"),
         [Bot(Race.Protoss, SentdeBot()),
          Computer(Race.Terran, Difficulty.Hard)],
         realtime=False)
