import streamlit as st
import json
import os
import re
import random
from PIL import Image
import asyncio
import enka


def normalize_name(s):
    s = s.lower()
    s = re.sub(r"[ .&()-]", "", s)
    return s


class RelicScorerApp:
    MAX_ROLLS = 5

    MEDIAN_BASE_ATK = 1149
    MEDIAN_BASE_HP = 2271
    MEDIAN_BASE_DEF = 988

    COEFS = {
        "CritRate": 2.0,
        "SPD": 2.5,
        "ATK%": 1.5,
        "HP%": 1.5,
        "EHR%": 1.5,
        "EffectRES%": 1.5,
        "DEF%": 1.2,
        "Break%": 1.0,
        "CritDMG": 1.0,
    }

    def __init__(self):
        self.mainstat_weights_full = self.load_and_normalize_json("mainstat_weights.json")
        self.substat_weights_full = self.load_and_normalize_json("substat_weights.json")

        if not self.mainstat_weights_full or not self.substat_weights_full:
            st.error("Weight files missing or invalid. Please ensure the JSON files exist.")
            st.stop()

        self.piece_choices = ["Head", "Hands", "Chest", "Boots", "Sphere", "Rope"]
        self.substat_choices = [
            "None",
            "HP",
            "ATK",
            "DEF",
            "HP%",
            "DEF%",
            "ATK%",
            "CritRate",
            "CritDMG",
            "EHR%",
            "EffectRES%",
            "Break%",
            "SPD",
        ]

        self.scoring_options = [self.denormalize_name(k) for k in sorted(self.mainstat_weights_full.keys())]

        self.mainstat_for_piece = {
            "head": ["HP"],
            "hands": ["Flat ATK"],
            "chest": ["HP%", "ATK%", "DEF%", "CritRate", "CritDMG", "Heal%", "EHR%"],
            "boots": ["HP%", "ATK%", "DEF%", "SPD"],
            "sphere": ["Elemental%(Correct)", "Elemental%(Wrong)", "HP%", "ATK%", "DEF%"],
            "rope": ["HP%", "ATK%", "DEF%", "EnergyRegen%", "Break%"],
        }

        if "relic_data" not in st.session_state:
            st.session_state.relic_data = {}

        if "auto" not in st.session_state:
            st.session_state.auto = 0

        if "auto_char_selected" not in st.session_state:
            st.session_state.auto_char_selected = None

        if "gui_relic_data" not in st.session_state:
            st.session_state.gui_relic_data = {
                piece: {
                    "Mainstat": None,
                    "Substat 1": {"Substat": "None", "Value": 0.0, "Rolls": 0},
                    "Substat 2": {"Substat": "None", "Value": 0.0, "Rolls": 0},
                    "Substat 3": {"Substat": "None", "Value": 0.0, "Rolls": 0},
                    "Substat 4": {"Substat": "None", "Value": 0.0, "Rolls": 0},
                }
                for piece in self.piece_choices
            }

    def load_and_normalize_json(self, filename):
        if not os.path.isfile(filename):
            st.error(f"File '{filename}' not found.")
            return {}
        try:
            with open(filename, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            st.error(f"JSON decode error in {filename}:\n{e}")
            return {}

        normalized = {}
        for k, v in data.items():
            nk = normalize_name(k)
            normalized[nk] = v
        return normalized

    def denormalize_name(self, normalized_key):
        return " ".join(word.capitalize() for word in re.findall(r"[a-z, 0-9]+", normalized_key))

    def update_mainstat_choices(self, piece):
        piece_lower = piece.lower()
        return self.mainstat_for_piece.get(piece_lower, [])

    def calculate_points(self, character, piece, mainstat, substats):
        character_key = normalize_name(character)
        piece_lower = piece.lower()
        is_head_or_hands = piece_lower in ["head", "hands"]

        main_wt = self.mainstat_weights_full.get(character_key, {}).get(piece, {}).get(mainstat, 0)
        char_subweights = self.substat_weights_full.get(character_key, {})

        subscore = 0
        for stat_name, val in substats:
            if stat_name == "None":
                continue
            val_conv = val
            if stat_name == "HP":
                val_conv = val / self.MEDIAN_BASE_HP * 100
                val_conv *= self.COEFS.get("HP%", 1.5)
            elif stat_name == "Flat ATK":
                val_conv = val / self.MEDIAN_BASE_ATK * 100
                val_conv *= self.COEFS.get("ATK%", 1.5)
            elif stat_name == "Flat DEF":
                val_conv = val / self.MEDIAN_BASE_DEF * 100
                val_conv *= self.COEFS.get("DEF%", 1.2)
            else:
                coef = self.COEFS.get(stat_name, 1.0)
                val_conv = val * coef
            subscore += val_conv * char_subweights.get(stat_name, 0)

        if is_head_or_hands:
            return subscore
        return 5.832 * main_wt + subscore

    def sidebar_mode_selector(self):
        st.sidebar.title("Input Mode")
        self.automatic = st.sidebar.button("Automatic input")
        self.manual = st.sidebar.button("Manual input")

        if self.automatic:
            st.session_state.auto = 1
        if self.manual:
            st.session_state.auto = 0

        png_dir = "./png"
        if os.path.exists(png_dir):
            png_files = [f for f in os.listdir(png_dir) if f.endswith(".png")]
            if png_files:
                random_image_file = random.choice(png_files)
                image_path = os.path.join(png_dir, random_image_file)
                image = Image.open(image_path)
                width, height = image.size
                new_width = 200
                new_height = int(new_width * height / width)
                image = image.resize((new_width, new_height))
                st.sidebar.image(image)
            else:
                st.sidebar.write("No PNG images found in /png")
        else:
            st.sidebar.write("/png folder not found")

    async def auto_mode_info(self):
        st.write("### Automatic Mode: Fetching Player Data")
        uid = st.text_input("Enter HSR Player UID (numeric):")
        fetch_button = st.button("Fetch Data")

        if uid and fetch_button:
            try:
                uid_int = int(uid)
            except ValueError:
                st.error("Invalid UID, please enter an integer.")
                return

            async with enka.HSRClient() as client:
                user = await client.fetch_showcase(uid_int)
                st.write(f"Player: {user.player.nickname}, Level: {user.player.level}")

                st.session_state.characters_list = user.characters
                st.session_state.auto_char_selected = None

        if "characters_list" in st.session_state and st.session_state.characters_list:
            cols = st.columns(len(st.session_state.characters_list))
            for idx, char in enumerate(st.session_state.characters_list):
                if cols[idx].button(char.name):
                    st.session_state.auto_char_selected = idx

            if st.session_state.auto_char_selected is not None:
                char = st.session_state.characters_list[st.session_state.auto_char_selected]
                st.write(f"### Character: {char.name}, Level: {char.level}")
                st.write("Relics:")

                relics_data = {}
                for piece_name in self.piece_choices:
                    relic = next((r for r in char.relics if r.set_name and r.set_name.lower() == piece_name.lower()), None)
                    relic_info = {
                        "Mainstat": None,
                        "Substat 1": {"Substat": None, "Value": None, "Rolls": None},
                        "Substat 2": {"Substat": None, "Value": None, "Rolls": None},
                        "Substat 3": {"Substat": None, "Value": None, "Rolls": None},
                        "Substat 4": {"Substat": None, "Value": None, "Rolls": None},
                    }
                    if relic:
                        relic_info["Mainstat"] = f"{relic.main_stat.name} - {relic.main_stat.value}" if relic.main_stat else None
                        for i, sub_stat in enumerate(relic.sub_stats):
                            if i < 4:
                                relic_info[f"Substat {i + 1}"] = {
                                    "Substat": sub_stat.name,
                                    "Value": sub_stat.value,
                                    "Rolls": None,
                                }
                    relics_data[piece_name] = relic_info

                    st.write(f"**{piece_name}**")
                    st.write(f"Main Stat: {relic_info['Mainstat']}")
                    for i in range(1, 5):
                        sub = relic_info[f"Substat {i}"]
                        st.write(f"Substat {i}: {sub['Substat']}, Value: {sub['Value']}")

                st.session_state.relic_data[char.name] = relics_data

    def run(self):
        self.sidebar_mode_selector()

        if st.session_state.auto == 1:
            asyncio.run(self.auto_mode_info())
        else:
            st.title("HSR Relic Scorer")

            col1, col2 = st.columns([3, 1])

            with col1:
                scoring = st.selectbox(
                    "Scoring Criteria",
                    self.scoring_options,
                    format_func=lambda x: x[:10] + "…" if len(x) > 13 else x,
                )
                piece = st.selectbox(
                    "Piece",
                    self.piece_choices,
                    format_func=lambda x: x[:10] + "…" if len(x) > 13 else x,
                )

                mainstat_options = self.update_mainstat_choices(piece)
                if not mainstat_options:
                    st.warning(f"No valid mainstat options for piece {piece}.")
                    mainstat = None
                else:
                    saved_mainstat = st.session_state.gui_relic_data.get(piece, {}).get("Mainstat")
                    main_options_with_none = ["None"] + mainstat_options
                    default_mainstat_index = main_options_with_none.index(saved_mainstat) if saved_mainstat in main_options_with_none else 0
                    mainstat = st.selectbox(
                        "Mainstat",
                        main_options_with_none,
                        index=default_mainstat_index,
                        format_func=lambda x: x[:10] + "…" if len(x) > 13 else x,
                        key=f"mainstat_{piece}",
                    )

            with col2:
                img_path = os.path.join("png", f"{scoring}.png")
                if os.path.exists(img_path):
                    image = Image.open(img_path)
                    width, height = image.size
                    new_width = 200
                    new_height = int(new_width * height / width)
                    image = image.resize((new_width, new_height))
                    st.image(image, caption=scoring)
                else:
                    st.info(f"No image found for {scoring}")

            st.markdown("---")

            st.write("### Substats")

            disabled_substats = set()
            if mainstat not in (None, "None"):
                disabled_substats.add(mainstat)

            chosen_substats = []
            for i in range(4):
                substat_data = st.session_state.gui_relic_data.get(piece, {}).get(f"Substat {i + 1}", {})
                sub = substat_data.get("Substat", "None")
                if sub != "None":
                    chosen_substats.append(sub)

            chosen_substats_set = set(chosen_substats)

            substats = []
            total_rolls = 0
            rolls_inputs = []
            invalid_selection = False

            for i in range(4):
                col1_sub, col2_sub, col3_sub = st.columns([3, 2, 2])
                with col1_sub:
                    saved_substat = st.session_state.gui_relic_data.get(piece, {}).get(f"Substat {i + 1}", {}).get("Substat", "None")

                    cur_disabled_substats = set(disabled_substats)
                    if saved_substat != "None":
                        cur_disabled_substats.update(chosen_substats_set - {saved_substat})
                    else:
                        cur_disabled_substats.update(chosen_substats_set)

                    labeled_options = []
                    for option in self.substat_choices:
                        if option in cur_disabled_substats and option != "None":
                            labeled_options.append(f"{option} (disabled)")
                        else:
                            labeled_options.append(option)

                    default_index = 0
                    if saved_substat in self.substat_choices:
                        for idx, opt_label in enumerate(labeled_options):
                            if opt_label.startswith(saved_substat):
                                default_index = idx
                                break

                    selected_label = st.selectbox(f"Substat {i + 1}", labeled_options, index=default_index, key=f"substat_{piece}_{i}")

                    selected_substat = selected_label.replace(" (disabled)", "")

                    if selected_label.endswith("(disabled)"):
                        invalid_selection = True

                    stat = selected_substat

                with col2_sub:
                    default_val = st.session_state.gui_relic_data.get(piece, {}).get(f"Substat {i + 1}", {}).get("Value", 0.0)
                    val = st.number_input(
                        f"Value {i + 1}",
                        min_value=0.0,
                        max_value=9999.9,
                        value=default_val,
                        step=0.1,
                        format="%.1f",
                        key=f"value_{piece}_{i}",
                    )
                with col3_sub:
                    default_rolls = st.session_state.gui_relic_data.get(piece, {}).get(f"Rolls", 0)
                    rolls = st.number_input(
                        f"Rolls {i + 1}",
                        min_value=0,
                        max_value=self.MAX_ROLLS,
                        value=default_rolls,
                        step=1,
                        key=f"rolls_{piece}_{i}",
                    )

                substats.append((stat, val))
                rolls_inputs.append(rolls)
                total_rolls += rolls

                # Update only the manual gui dict
                st.session_state.gui_relic_data[piece][f"Substat {i + 1}"] = {
                    "Substat": stat,
                    "Value": val,
                    "Rolls": rolls,
                }

            st.session_state.gui_relic_data[piece]["Mainstat"] = mainstat

            if total_rolls > self.MAX_ROLLS:
                st.error(f"Total rolls {total_rolls} exceed maximum allowed {self.MAX_ROLLS}.")

            if mainstat in (None, "None"):
                points = 0
                st.warning("Cannot calculate score without a valid mainstat.")
            elif invalid_selection:
                points = 0
                st.error("Invalid substat selection detected (selected substat is disabled). Score cannot be calculated.")
            else:
                points = self.calculate_points(scoring, piece, mainstat, substats)

            st.markdown("---")

            st.write(f"**Scoring Criteria:** {scoring}")
            st.write(f"**Piece:** {piece}")
            st.write(f"**Mainstat:** {mainstat}")
            st.write(f"### Relic Score: {points:.3f}")

            st.write("### Substat Details:")
            for i, ((stat, val), rolls) in enumerate(zip(substats, rolls_inputs)):
                if stat != "None":
                    st.write(f"Substat {i + 1}: {stat} | Value: {val} | Rolls: {rolls}")

            # Show current manual relic dict for selected piece
            st.markdown("---")
            st.write(f"Manual relic dict for piece '{piece}':")
            current_dict = st.session_state.gui_relic_data.get(piece, {})
            st.code(json.dumps(current_dict, indent=2), language="json")

            manual_input = st.text_area(f"Paste manual dict JSON for piece '{piece}' here:", height=200)
            if st.button(f"Load manual dict for piece '{piece}'"):
                try:
                    loaded_dict = json.loads(manual_input)
                    st.session_state.gui_relic_data[piece] = loaded_dict
                    st.success("Manual dict loaded successfully")
                except Exception as e:
                    st.error(f"Failed to load JSON: {e}")


if __name__ == "__main__":
    app = RelicScorerApp()
    app.run()
