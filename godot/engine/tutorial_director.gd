class_name TutorialDirector
extends RefCounted
## 6-Step Guided Onboarding Director for the Pokémon Emerald Enclave Overworld.
## Tracks step progression, provides the 1-line top-center HUD objective pill text,
## and supplies the exact target zone + world coordinates for the bouncing golden arrow.

signal step_changed(step_index: int, step_data: Dictionary)
signal tutorial_completed()

const STEPS: Array[Dictionary] = [
	{
		"step": 1,
		"id": "step_1_talk_mentor",
		"zone_id": "zone_01_homestead_grove",
		"target_pos": Vector2(416, 336),
		"pill_text": "🎯 Step 1/6: Walk to Mentor Silas & Terra by your porch and press [Z / Space]",
		"completion_msg": "Step 1/6 Complete! Terra & Silas welcomed you to Homestead Grove. Next: equip your Copper Trowel [1] and dig the glowing Bismuth Geode crack!"
	},
	{
		"step": 2,
		"id": "step_2_dig_geode",
		"zone_id": "zone_01_homestead_grove",
		"target_pos": Vector2(320, 416),
		"pill_text": "🎯 Step 2/6: Walk to the glowing Bismuth Geode crack and press [F / Z] with Trowel [1]",
		"completion_msg": "Step 2/6 Complete! You unearthed a Hopper-Crystal Bismuth Geode + Cave-Truffle (+5 RUP)! Next: water the Golden Iron-Wheat plots!"
	},
	{
		"step": 3,
		"id": "step_3_water_wheat",
		"zone_id": "zone_01_homestead_grove",
		"target_pos": Vector2(640, 384),
		"pill_text": "🎯 Step 3/6: Equip Watering Can [4] and press [F / Z] on the Golden Iron-Wheat plots",
		"completion_msg": "Step 3/6 Complete! You irrigated the Crystalline Iron-Wheat plots (+5 RUP)! Next: catch an Aurora Prism-Moth in the tall spore-grass!"
	},
	{
		"step": 4,
		"id": "step_4_catch_moth",
		"zone_id": "zone_01_homestead_grove",
		"target_pos": Vector2(224, 480),
		"pill_text": "🎯 Step 4/6: Equip Bug Net [2] and press [F / Z] by the fluttering Aurora Prism-Moth",
		"completion_msg": "Step 4/6 Complete! You cataloged an Aurora Prism-Moth (+5 RUP)! Next: step into Willow's Homestead doorway and craft a tonic at your Alembic Workbench!"
	},
	{
		"step": 5,
		"id": "step_5_craft_alembic",
		"zone_id": "room_willow_home",
		"outdoor_door_zone": "zone_01_homestead_grove",
		"outdoor_door_pos": Vector2(480, 272),
		"target_pos": Vector2(160, 160),
		"pill_text": "🎯 Step 5/6: Enter Willow's Homestead door and press [Z / F] at the Copper Alembic Workbench",
		"completion_msg": "Step 5/6 Complete! You synthesized a warming Herbal Joint-Liniment Vial (+10 RUP)! Final step: gift your tonic to a citizen or donate a specimen to the Museum!"
	},
	{
		"step": 6,
		"id": "step_6_gift_or_donate",
		"zone_id": "zone_01_homestead_grove",
		"target_pos": Vector2(512, 336),
		"pill_text": "🎯 Step 6/6: Deliver a Gift/Favor to Silas [Z] or Donate a Specimen at the Living Atlas Museum!",
		"completion_msg": "🎉 Onboarding Complete! You've mastered all 6 Enclave Alchemist tools! Walk the N/S/E/W paths or open [START / Enter] to explore all 5 zones & 3 indoor rooms!"
	}
]

var current_step: int = 1 # 1..6, or 7 when completed
var is_completed: bool = false


func get_current_step_data() -> Dictionary:
	if is_completed or current_step > STEPS.size():
		return {
			"step": 7,
			"id": "completed",
			"zone_id": "",
			"target_pos": Vector2.ZERO,
			"pill_text": "✨ Free Exploration: Walk N/S/E/W between all 5 Hoenn Zones or press [Enter] for START Menu"
		}
	return STEPS[current_step - 1]


func get_objective_pill_text() -> String:
	return str(get_current_step_data().get("pill_text", ""))


func get_arrow_world_position(active_zone_id: String) -> Vector2:
	if is_completed or current_step > STEPS.size():
		return Vector2(-1000, -1000)
	var data := get_current_step_data()
	var step_zone := str(data.get("zone_id", ""))
	if step_zone == active_zone_id:
		return data.get("target_pos", Vector2(-1000, -1000))
	if data.has("outdoor_door_zone") and str(data.get("outdoor_door_zone")) == active_zone_id:
		return data.get("outdoor_door_pos", Vector2(-1000, -1000))
	return Vector2(-1000, -1000)


func notify_event(event_tag: String) -> String:
	if is_completed:
		return ""
	var matched := false
	match current_step:
		1:
			if event_tag in ["talk_npc", "talk_terra", "talk_silas"]:
				matched = true
		2:
			if event_tag == "forage_dig":
				matched = true
		3:
			if event_tag == "water_crop":
				matched = true
		4:
			if event_tag == "catch_critter":
				matched = true
		5:
			if event_tag == "craft_diy":
				matched = true
		6:
			if event_tag in ["gift_citizen", "donate_museum", "trigger_feast"]:
				matched = true

	if not matched:
		return ""

	var msg := str(get_current_step_data().get("completion_msg", ""))
	current_step += 1
	if current_step > STEPS.size():
		is_completed = true
		tutorial_completed.emit()
	else:
		step_changed.emit(current_step, get_current_step_data())
	return msg


func complete_step(step_num: int) -> String:
	if step_num < 1 or step_num > STEPS.size():
		return ""
	current_step = step_num
	var msg := str(get_current_step_data().get("completion_msg", ""))
	current_step = step_num + 1
	if current_step > STEPS.size():
		is_completed = true
		tutorial_completed.emit()
	else:
		step_changed.emit(current_step, get_current_step_data())
	return msg


func skip_tutorial() -> void:
	current_step = STEPS.size() + 1
	is_completed = true
	tutorial_completed.emit()


func restart_tutorial() -> void:
	current_step = 1
	is_completed = false
	step_changed.emit(current_step, get_current_step_data())
