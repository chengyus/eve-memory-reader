from lib2to3.pgen2.token import OP
from libeve import KEYMAP
from libeve.bots import Bot
from libeve.interface import UITreeNode


import string
import random
import time
import traceback
import ipdb

class MiningBot(Bot):
    def __init__(
        self,
        log_fn=print,
        pause_interrupt=None,
        pause_callback=None,
        stop_interrupt=None,
        stop_callback=None,
        stop_safely_interrupt=None,
        stop_safely_callback=None,
        deploy_drones_while_mining=False,
        station=None,
        number_of_miners=1,
        shields=None,
        afterburner=None,
        asteroids_of_interest=[],
        asteroids_ratios=[],
        fleet_commander=None,
    ):
        super().__init__(
            log_fn=log_fn,
            pause_interrupt=pause_interrupt,
            pause_callback=pause_callback,
            stop_interrupt=stop_interrupt,
            stop_callback=stop_callback,
            stop_safely_interrupt=stop_safely_interrupt,
            stop_safely_callback=stop_safely_callback,
        )
        self.visited_asteroid_belts = list()
        self.deploy_drones_while_mining = deploy_drones_while_mining
        self.station = station
        self.number_of_miners = number_of_miners
        self.shields = shields
        self.afterburner= afterburner
        self.asteroids_of_interest = asteroids_of_interest
        self.asteroids_ratios = asteroids_ratios
        self.matched_asteroids = list()
        self.fleet_commander = fleet_commander
        self.trip_id = ""
        self.current_asteroid = None
        self.asteroids_mined = 0
        self.shields_enabled = False
        self.afterburner_enabled = False
        self.need_repairs = False

    def new_trip(self):
        self.trip_id = "".join(random.choice(string.ascii_letters) for i in range(32))

    def undock(self):
        super().undock()
        self.visited_asteroid_belts = list()
        self.shields_enabled = False
        self.new_trip()

    def ensure_fleet_hangar_open(self):

        fleet_hangar = self.wait_for(
            {"_setText": " (Fleet Hangar)"},
            type="Label",
            contains=True,
            until=5,
        )

        if fleet_hangar:
            self.say("fleet hangar open")
            self.click_node(fleet_hangar, times=2)
            return

        while True:

            self.say("opening fleet hangar")

            self.wait_for_overview()
            time.sleep(5)

            fleet_tab = self.wait_for({"_setText": "Fleet"}, type="LabelThemeColored")

            self.click_node(
                fleet_tab,
                times=2,
                expect=[{"_text": self.fleet_commander}],
                expect_args={"type": "OverviewLabel"},
            )

            self.click_node(
                self.wait_for({"_text": self.fleet_commander}, type="OverviewLabel"),
                right_click=True,
            )

            open_fleet_hangar_btn = self.wait_for(
                {"_setText": "Open Fleet Hangar"},
                type="EveLabelMedium",
            )

            self.click_node(open_fleet_hangar_btn)

            if not (
                fleet_hangar := self.wait_for(
                    {"_setText": " (Fleet Hangar)"},
                    type="Label",
                    contains=True,
                    until=5,
                )
            ):
                continue

            self.click_node(fleet_hangar, times=2)
            break

    def compress(self):
        while True:
            self.ensure_fleet_hangar_open()

            fleet_info = self.wait_for(
                {"_setText": "<br>Distance:"}, type="EveLabelSmall", contains=True
            )

            name, distance_str, _ = fleet_info.attrs["_setText"].split("<br>")

            _, dist_str, unit = distance_str.strip().split(" ")

            dist = int(dist_str.replace(",", ""))

            if unit == "m":
                dist /= 1000

            if dist > 2.5:

                # find the approach button
                approach_btn = self.wait_for(
                    {"_name": "selectedItemApproach"}, type="SelectedItemButton"
                )

                # click it
                self.click_node(approach_btn)

                # wait a bit
                time.sleep(5)
                continue

            self.ensure_mining_hold_is_open()

            items = self.wait_for(
                {"_name": "itemNameLabel"}, type="Label", select_many=True
            )

            if not items:
                return  # this is not a failure, you're just poor

            self.count_earnings()

            fleet_hangar = self.wait_for(
                {"_setText": " (Fleet Hangar)"},
                type="Label",
                contains=True,
                until=5,
            )

            self.say("compressing ore")

            for item in items:

                self.click_node(
                    item,
                    right_click=True,
                    expect=[{"_setText": "Stack All"}],
                    expect_args={"type": "EveLabelMedium"},
                )

                stack_all_btn = self.wait_for(
                    {"_setText": "Stack All"},
                    type="EveLabelMedium",
                )

                self.click_node(stack_all_btn)

                self.click_node(
                    item,
                    right_click=True,
                    expect=[{"_setText": "Select All"}],
                    expect_args={"type": "EveLabelMedium"},
                )

                select_all_btn = self.wait_for(
                    {"_setText": "Select All"},
                    type="EveLabelMedium",
                )

                self.click_node(select_all_btn)

                self.click_node(
                    item,
                    right_click=True,
                    expect=[{"_setText": "Compress"}],
                    expect_args={"type": "EveLabelMedium", "contains": True},
                )

                compress_btn = self.wait_for(
                    {"_setText": "Compress"},
                    type="EveLabelMedium",
                    contains=True,
                )

                self.click_node(compress_btn)

                confirm_btn = self.wait_for(
                    {"_setText": "Compress"},
                    type="LabelThemeColored",
                )

                self.click_node(confirm_btn, times=2)

                close_btn = self.wait_for(
                    {"_setText": "Cancel"},
                    type="LabelThemeColored",
                )

                self.click_node(close_btn, times=2)

                self.click_node(
                    item,
                    right_click=True,
                    expect=[{"_setText": "Select All"}],
                    expect_args={"type": "EveLabelMedium"},
                )

                select_all_btn = self.wait_for(
                    {"_setText": "Select All"},
                    type="EveLabelMedium",
                )

                self.click_node(select_all_btn)
                self.drag_node_to_node(item, fleet_hangar)
                break

            break

    def repair(self):
        self.say("repairing ship")
        repair_facilities = self.wait_for({"_setText": "Repair Facilities"}, until=5)
        if not repair_facilities:
            repair_btn = self.wait_for({"_name": "repairshop"})
            self.click_node(
                repair_btn,
                expect=[
                    {"_setText": "Repair Facilities"},
                ],
            )
        items_to_repair = self.wait_for(
            {"_name": "entryLabel"}, select_many=True, until=5
        )
        if not items_to_repair:
            return
        for item in items_to_repair:
            self.click_node(item)
        repair_item_btn = self.wait_for({"_setText": "Repair Item"})
        self.click_node(repair_item_btn)

    def warp_to_asteroid_belt(self):
        while True:
            self.wait_for_overview()

            self.say("Finding asteroid belt for warp target")

            asteroid_belts = self.wait_for(
                {"_text": " - Asteroid Belt "},
                select_many=True,
                contains=True,
                type="OverviewLabel",
            )
            self.current_asteroid = asteroid_belts[0]
            #self.click_node(
            #    self.current_asteroid,
            #    times=2,
            #    expect=[{"_text": " - Asteroid Belt "}],
            #    expect_args={"contains": True, "type": "OverviewLabel"},
            #)

            asteroid_belt = None
            for belt in asteroid_belts:
                if "_text" not in belt.attrs:
                    continue
                if belt.attrs["_text"] not in self.visited_asteroid_belts:
                    self.visited_asteroid_belts.append(belt.attrs["_text"])
                    asteroid_belt = belt
                    break

            if not asteroid_belt:
                return -1

            self.click_node(asteroid_belt)

            warpto_btn = self.wait_for(
                {"_name": "selectedItemWarpTo"}, type="SelectedItemButton"
            )

            self.click_node(warpto_btn)

            if self.wait_for({"_setText": "Establishing Warp Vector"}, until=5):
                break
        self.wait_until_warp_finished()

    def ensure_inventory_is_open(self):

        inv_label = self.wait_for(
            {"_setText": "Inventory"}, type="Label", until=1
        )

        if not inv_label:

            inv_btn = self.wait_for({"_name": "inventory"}, type="ButtonInventory")

            if not inv_btn:
                raise Exception("failed to find inventory button")

            self.click_node(
                inv_btn,
                expect=[{"_setText": "Inventory"}],
                expect_args={"type": "Label"},
            )

    def ensure_mining_hold_is_open(self):
        self.ensure_inventory_is_open()
        mining_hold = self.wait_for({"_setText": "Mining Hold"}, type="Label", until=1)

        if not mining_hold:
            raise Exception("failed to find mining hold")

        #time.sleep(3)
        self.click_node(mining_hold, times=2)

    def ensure_cargo_is_open(self):
        self.ensure_inventory_is_open()

        cargo_btn = self.wait_for({"_name": "topCont_ShipHangar"}, type="Container")

        self.click_node(cargo_btn, times=2)

    def count_earnings(self):
        est_price_node = self.wait_for(
            {"_setText": "Est. price"}, type="EveLabelMedium", contains=True
        )
        est_price_str = est_price_node.attrs.get("_setText", "")
        est_price, _ = est_price_str.split("ISK")
        est_price = int(est_price.replace(",", "").strip())

    def unload_loot(self):
        self.wait_for({"_setText": "Hangars"}, type="EveLabelMedium")
        self.say("unloading loot")

        self.ensure_mining_hold_is_open()

        items = self.wait_for(
            {"_name": "itemNameLabel"}, type="Label", select_many=True
        )

        if not items:
            return  # this is not a failure, you're just poor

        self.count_earnings()

        item_hangar = self.wait_for(
            {"_setText": "Item hangar", "_name": None}, type="Label", until=5
        )

        if not item_hangar:
            raise Exception("failed to find item hangar")

        for item in items:
            this_ore_icon_node = self.tree.nodes[self.tree.nodes[item.parent].children[0]]
            self.drag_node_to_node(this_ore_icon_node, item_hangar)

    def deploy_drones(self):

        if not self.deploy_drones_while_mining:
            return

        self.say("deploying drones")

        drones_node_text = self.wait_for( {"_setText": "Drones in Bay ("}, type="EveLabelMedium", contains=True, until=1)
        _, drones_number_with_trailing_parent = drones_node_text.attrs["_setText"].split('(')
        drones_number = int(drones_number_with_trailing_parent.split(')')[0])
        if not drones_node_text or drones_number == 0:
            return
        if drones_number > 0:
            self.click_node(drones_node_text, right_click=True)

            launch_btn = self.wait_for( {"_setText": "Launch Drone"}, type="EveLabelMedium", contains=True, until=2)

            self.click_node(launch_btn)
            mining_drone = self.wait_for( {"_setText": "Mining Drone"}, contains=True, until=3 )
            if mining_drone:
                drones_in_space = self.wait_for( {"_setText": "Drones in Space ("}, type="EveLabelMedium", contains=True, until=5)
                self.click_node(drones_in_space, right_click=True)
                mine_btn = self.wait_for( {"_setText": "Mine ("}, type="EveLabelMedium", contains=True )
                self.say("setting mining drones to mine")
                self.click_node(mine_btn)


    def warp_to_asteroid_belt_if_no_asteroid_of_interest(self):
        asteroids = self.wait_for( {"_text": "Asteroid ("}, type="OverviewLabel", select_many=False, contains=True, until=1 )
        if not asteroids:
            self.warp_to_asteroid_belt()

    def find_asteroids_of_interest(self):
        for asteroid_type in self.asteroids_of_interest:
            this_list = self.wait_for( {"_text": asteroid_type}, type="OverviewLabel", select_many=True, contains=False, until=3)
            for this_asteroid in this_list:
                self.matched_asteroids.append(this_asteroid)
        return

    def find_closest_asteroid(self):
        while True:
            try:
                # while there are no asteroids in the current belt
                asteroids = self.wait_for( {"_text": "Asteroid ("}, type="OverviewLabel", select_many=True, contains=True, until=1 )
                if asteroids_len := len(asteroids):
                    print(f"asteroids len: {asteroids_len}")
                while not asteroids:
                    if self.deploy_drones_while_mining:
                        self.recall_drones()
                    # warp to another belt
                    # -1 means we've gone through all belts with no asteroids
                    if self.warp_to_asteroid_belt() == -1:
                        return -1
                    self.wait_for_overview()
                    mining_tab = self.wait_for(
                        {"_setText": "Mining"}, type="EveLabelMedium"
                    )
                    self.click_node(mining_tab, times=1)
                    self.say("finding asteroid")
                # find the closest asteroid
                closest_asteroid = None
                for asteroid in asteroids:
                    _, asteroid_name = asteroid.attrs["_text"].split("(")
                    asteroid.data["full_name"] = asteroid_name.replace(")", "")
                    if " " in asteroid.data["full_name"]:
                        _, asteroid.data["name"] = asteroid.data["full_name"].split(" ")
                    else:
                        asteroid.data["name"] = asteroid.data["full_name"]
                    print("asteroid.data name: ", asteroid.data["name"]  )
                    if asteroid.data["name"] not in self.asteroids_of_interest:
                        continue
                    pnode = asteroid.parent
                    dnode = pnode.children[5]
                    distance_str = dnode.attrs.get("_text", "0 m")
                    if not (distance_str.endswith("m") or distance_str.endswith("km")):
                        continue
                    print(f"'{distance_str}'")
                    distance, unit = distance_str.strip().split(" ")
                    asteroid.data["distance"] = int(distance.replace(",", ""))
                    if unit == "m":
                        asteroid.data["distance"] /= 1000
                    if (
                        not closest_asteroid
                        or (
                            "Massive" not in closest_asteroid.attrs.get("_text")
                            and asteroid.data["distance"]
                            < closest_asteroid.data["distance"]
                        )
                    ) or (
                        "Massive" in asteroid.attrs.get("_text", "")
                        and asteroid.data["distance"] < 15
                    ):
                        closest_asteroid = asteroid
                # we've found a belt and at least 1 asteroid
                self.current_asteroid = closest_asteroid
                return closest_asteroid
            except Exception as e:
                traceback.print_exc()
                self.say("trying to recover from error")
                continue

    def check_for_locked_asteroid(self):
        return self.wait_for(
            {"_name": "assigned"}, type="Container", until=1
        )


    def find_asteroid(self):

        self.wait_for_overview()

        mining_tab = self.wait_for({"_setText": "Mining"}, type="EveLabelMedium")

        self.click_node(mining_tab, times=1)

        self.warp_to_asteroid_belt_if_no_asteroid_of_interest()
        self.current_asteroid = None
        self.say("finding asteroid")

        # acquire target
        # track the target
        # approach the target + afterburner
        # lock when within range
        while not (target_locked := self.check_for_locked_asteroid()):
            # find the asteroid of interest and use the first one, self.current_asteroid holds it
            self.find_asteroids_of_interest()
            if not self.current_asteroid:
                self.current_asteroid = self.matched_asteroids[0]
                # if it is, click it
                self.click_node(self.current_asteroid)
            name = self.current_asteroid.attrs['_text']
            selected_item_info = self.wait_for( { "_setText": f"Asteroid ({name})<br>" }, type="EveLabelMedium", contains=True )
            _, dist_with_unit = selected_item_info.attrs['_setText'].split("<br>")
            distance_str, unit = dist_with_unit.split(' ')
            distance = int(distance_str.replace( ',', ''))
            track_btn = self.wait_for(
                {"_name": "selectedItemSetInterest"}, type="SelectedItemButton"
            )
            if not track_btn:
                target_locked = False
            self.click_node(track_btn)
            #ipdb.set_trace()

            lock_target_btn = self.wait_for( {"_name": "selectedItemLockTarget"}, type="SelectedItemButton", until=1 )
            stop_button = self.wait_for(type="StopButton")
            if distance <= 9999 and unit == 'm':
                self.click_node(stop_button)
                if(lock_target_btn):
                    self.click_node(lock_target_btn)
                    self.say("Target locked")
                    self.click_node(stop_button)
                    if self.afterburner_enabled:
                        self.toggle_afterburner()
                    break

            elif distance >= 10 and distance < 12 and unit == "km":
                self.toggle_afterburner()
                self.click_node(stop_button)
                if(lock_target_btn):
                    self.click_node(lock_target_btn)
                    self.say("Target locked")
                    self.click_node(stop_button)
                    if self.afterburner_enabled:
                        self.toggle_afterburner()
                    break
            elif distance >= 12 and distance <= 16 and unit == "km":
                if(lock_target_btn):
                    self.click_node(lock_target_btn)
                    self.say("Target locked")
                    self.click_node(stop_button)
                    if self.afterburner_enabled:
                        self.toggle_afterburner()
                # find the approach button
                approach_btn = self.wait_for(
                    {"_name": "selectedItemApproach"}, type="SelectedItemButton"
                )
                self.click_node(approach_btn)
            elif distance > 16 and unit == "km":
                # find the approach button
                approach_btn = self.wait_for(
                    {"_name": "selectedItemApproach"}, type="SelectedItemButton"
                )
                self.click_node(approach_btn)
                self.enable_afterburner()

    def change_miner(self, slot: UITreeNode):
        # returns -1 if no more miners

        self.ensure_cargo_is_open()

        items = self.wait_for(
            {"_name": "itemNameLabel"}, type="Label", until=5, select_many=True
        )

        if not items:
            return -1

        miner_stash = None
        for item in items:
            item_parent = self.tree.nodes[item.parent]
            item_grandparent = self.tree.nodes[item_parent.parent]
            item_quantity_parent = self.tree.nodes[item_grandparent.children[2]]

            if item_quantity_parent.type != "ContainerAutoSize":
                continue

            item_quantity = self.tree.nodes[item_quantity_parent.children[0]]

            if item_quantity.type != "EveLabelSmall":
                continue

            quantity = int(item_quantity.attrs.get("_setText", "0"))

            if quantity > 1:
                miner_stash = item
                break

        if not miner_stash:
            return -1

        self.drag_node_to_node(miner_stash, slot)

    def check_if_high_sec(self):
        sec_text_node = self.wait_for({"_setText": "Security status"}, contains=True, type="EveCaptionSmall")
        sec_num_part = sec_text_node.attrs["_setText"].split('>')[2].split('<')[0]
        sec_num = float(sec_num_part)
        return sec_num > 0.8

    def check_if_miner_is_badly_damaged(self, slot: UITreeNode):
        self.move_cursor_to_node(slot)
        high_sec_bool = self.check_if_high_sec()
        if high_sec_bool:
            # Assume in High Sec, it's unlikely to be damaged.
            return False

        if damaged_str := self.wait_for(
            {"_setText": "Damaged"}, type="EveLabelMedium", contains=True, until=1
        ):
            if "<color=red>" in damaged_str.attrs["_setText"]:
                _, damaged_percentage_str = damaged_str.attrs["_setText"].split(
                    "<color=red>"
                )
                percentage_str, _ = damaged_percentage_str.split(" ")
                percentage = int(percentage_str.replace("%", ""))
                if percentage >= 60:
                    return false
                else:
                    self.need_repairs = True
                    return true

    def ensure_miner_is_running(self, slot_key, number_of_miners_enabled):
        slot = self.wait_for({"_name": KEYMAP[slot_key]}, type="ShipSlot", until=1)
        if slot:
            status = self.check_if_miner_is_badly_damaged(slot)
            glow_nodes = self.tree.find_node( {"_name": "glow"}, type="Sprite", select_many=True)
            if not glow_nodes:
                self.click_node(slot)
                return
            for glow in glow_nodes:
                if not self.tree.nodes[glow.parent].attrs.get("_name") == KEYMAP[slot_key]:
                    self.click_node(slot)

    def ensure_drones_are_mining(self):

        if not self.deploy_drones_while_mining:
            return
        drones_node_text = self.wait_for( {"_setText": "Drones in Bay ("}, type="EveLabelMedium", contains=True, until=1)
        _, drones_number_with_trailing_parent = drones_node_text.attrs["_setText"].split('(')
        drones_number = int(drones_number_with_trailing_parent.split(')')[0])
        mining_drones = self.wait_for({"_setText": "Mining Drone"}, type="EveLabelMedium", contains=True, until=1)
        if mining_drones:
            idle = mining_drones.attrs["_setText"].split('>')[1].split('<')[0]
        if drones_number == 0 and not mining_drones and not idle:
            return

        if drones_number > 0:
            self.click_node(drones_node_text, right_click=True)
            submenuitem = self.wait_for({"_setText": "Launch Drone ("}, contains=True)
            self.click_node(submenuitem)
        if mining_drones and idle == "Idle":
            self.say("setting drones to mine")
            drones_in_space = self.wait_for( {"_setText": "Drones in Space ("}, type="EveLabelMedium", contains=True, until=3)
            self.click_node(drones_in_space, right_click=True)
            mine_btn = self.wait_for( {"_setText": "Mine ("}, type="EveLabelMedium", contains=True, until=3)
            self.click_node(mine_btn)

    def mine_asteroid(self):
        self.ensure_inventory_is_open()
        self.ensure_drones_are_mining()

        number_of_miners_enabled = 0

        for slot_key in ["F1", "F2"][: self.number_of_miners]:
            self.say(f"toggling {slot_key}")
            if not self.wait_for({"_name": "target"}, type="TargetInBar", until=10):
                break
            self.ensure_miner_is_running(slot_key, number_of_miners_enabled)
            number_of_miners_enabled += 1

        self.say("mining asteroid")

        while len(
            self.tree.find_node({"_name": "glow"}, type="Sprite", select_many=True)
        ) == self.number_of_miners + (1 if self.shields else 0) and self.tree.find_node(
            {"_name": "target"}, type="TargetInBar"
        ):
            self.check_interrupts()
            time.sleep(5)

        self.asteroids_mined += 1

        time.sleep(5)
        for glow in self.tree.find_node(
            {"_name": "glow"}, type="Sprite", select_many=True
        ):
            if "inFlightHighSlot" not in self.tree.nodes[glow.parent].attrs.get(
                "_name"
            ):
                continue
            self.click_node(self.tree.nodes[glow.parent])
            time.sleep(2)

        self.current_asteroid = None

    def toggle_afterburner(self):
        self.say("toggling afterburner")
        slot = self.wait_for({"_name": KEYMAP[self.afterburner]}, type="ShipSlot")
        self.click_node(slot)
        self.afterburner_enabled = not self.afterburner_enabled

    def enable_afterburner(self):
        if not self.afterburner or self.afterburner_enabled:
            return
        self.toggle_afterburner()
        self.afterburner_enabled = True
        retries = 0
        while retries < 3:
            for glow in self.tree.find_node(
                {"_name": "glow"}, type="Sprite", select_many=True
            ):
                if (
                    self.tree.nodes[glow.parent].attrs.get("_name")
                    == "inFlightMediumSlot1"
                ):
                    return True
            retries += 1
            time.sleep(2)

    def enable_shields(self):
        if not self.shields or self.shields_enabled:
            return
        self.say("enabling shields")
        slot = self.wait_for({"_name": KEYMAP[self.shields]}, type="ShipSlot")
        self.click_node(slot)
        self.shields_enabled = True
        retries = 0
        while retries < 3:
            for glow in self.tree.find_node(
                {"_name": "glow"}, type="Sprite", select_many=True
            ):
                if (
                    self.tree.nodes[glow.parent].attrs.get("_name")
                    == "inFlightMediumSlot2"
                ):
                    return True
            retries += 1
            time.sleep(2)

    def handle_ratios(self, ratio, match_asteroid=None):
        ast1_inv_label_node = self.wait_for({"_setText": "<center>"+ match_asteroid}, type="Label")
        ast1_icon_node = self.tree.nodes[self.tree.nodes[ast1_inv_label_node.parent].children[0]]
        self.click_node(ast1_icon_node)
        cap_gauge = self.wait_for(type="InvContCapacityGauge")
        cap_node_id = cap_gauge.children[0]
        cap_node = self.tree.nodes[cap_node_id]
        cap_str = cap_node.attrs.get("_setText", "0/0 m").strip()
        selected_inv_vol_str, ratio_str, _ = cap_str.split(" ")
        load, capacity_str = ratio_str.split('/')
        capacity = float(capacity_str.replace(',',''))
        if float(selected_inv_vol_str.strip("()").replace(',',''))/capacity >= self.asteroids_ratios[0]:
            self.asteroids_of_interest.remove(self.asteroids_of_interest[0])

    def cargo_is_full(self):
        self.say("checking cargo")
        self.ensure_mining_hold_is_open()
        cap_gauge = self.wait_for(type="InvContCapacityGauge")
        cap_node_id = cap_gauge.children[0]
        cap_node = self.tree.nodes[cap_node_id]
        cap_str = cap_node.attrs.get("_setText", "0/0 m").strip()
        self.say(f"capacity at: {cap_str}", narrate=False)
        if not cap_str.__contains__('('):
            ratio_str, _ = cap_str.split(" ")
        else:
            selected_inv_vol_str, ratio_str, _ = cap_str.split(" ")
        try:
            ratio = eval(ratio_str.replace(",", ""))
            print(ratio)
            volume, max_volume = ratio_str.split('/')
            inv_asteroid_node = self.wait_for({"_name": "itemNameLabel"}, type="Label", until=1)
            if self.asteroids_ratios and inv_asteroid_node:
                _, match_asteroid = inv_asteroid_node.attrs["_setText"].split('>')
                self.handle_ratios(ratio, match_asteroid)
            return ratio > 0.95
        except ZeroDivisionError:
            return False

    def mine_asteroids(self):
        if self.trip_id == "":
            self.new_trip()
        #if self.shields:
        #    self.enable_shields()
        while not self.cargo_is_full():
            if self.find_asteroid() == -1:
                break
            if self.deploy_drones_while_mining:
                self.deploy_drones()
            self.mine_asteroid()

    def warp_to_station(self):
        self.ensure_within_station()
    def warp_to_site(self):
        warp_to_site = self.for_for({"_setText": "Warp To Site"}, contains=True, type="EveLabelMedium", until=3)
        self.click_node = warp_to_site
