import streamlit as st
import json
import os
import re

def normalize_name(s):
    s = s.lower()
    s = re.sub(r'[ .&()-]', '', s)
    return s

class RelicScorerApp:
    MAX_ROLLS = 5

    # Median base stats for flat stat conversion
    MEDIAN_BASE_ATK = 1149
    MEDIAN_BASE_HP = 2271
    MEDIAN_BASE_DEF = 988

    # Coefficients for percentage stats to baseline unit
    COEFS = {
        'CritRate': 2.0,
        'SPD': 2.5,
        'ATK%': 1.5,
        'HP%': 1.5,
        'EHR%': 1.5,
        'EffectRES%': 1.5,
        'DEF%': 1.2,
        'Break%': 1.0,
        'CritDMG': 1.0,
    }

    def __init__(self):
        self.mainstat_weights_full = self.load_and_normalize_json("mainstat_weights.json")
        self.substat_weights_full = self.load_and_normalize_json("substat_weights.json")

        if not self.mainstat_weights_full or not self.substat_weights_full:
            st.error("Weight files missing or invalid. Please ensure the JSON files exist.")
            st.stop()

        self.piece_choices = ["Head", "Hands", "Chest", "Boots", "Sphere", "Rope"]
        self.substat_choices = ["None", "HP", "ATK", "DEF", "HP%", "DEF%", "ATK%", "CritRate",
                               "CritDMG", "EHR%", "EffectRES%", "Break%", "SPD"]

        self.scoring_options = [self.denormalize_name(k) for k in sorted(self.mainstat_weights_full.keys())]

        self.mainstat_for_piece = {
            "head": ["Flat HP"],
            "hands": ["Flat ATK"],
            "chest": ["HP%", "ATK%", "DEF%", "CritRate", "CritDMG", "Heal%", "EHR%"],
            "boots": ["HP%", "ATK%", "DEF%", "SPD"],
            "sphere": ["Elemental%(Correct)", "Elemental%(Wrong)", "HP%", "ATK%", "DEF%"],
            "rope": ["HP%", "ATK%", "DEF%", "EnergyRegen%", "Break%"]
        }

    def load_and_normalize_json(self, filename):
        if not os.path.isfile(filename):
            st.error(f"File '{filename}' not found.")
            return {}
        try:
            with open(filename, 'r', encoding='utf-8') as f:
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
        return ' '.join(word.capitalize() for word in re.findall(r'[a-z]+', normalized_key))

    def update_mainstat_choices(self, piece):
        piece_lower = piece.lower()
        allowed = self.mainstat_for_piece.get(piece_lower, [])
        return allowed

    def calculate_points(self, character, piece, mainstat, substats):
        character_key = normalize_name(character)
        piece_lower = piece.lower()
        is_head_or_hands = piece_lower in ['head', 'hands']

        main_wt = self.mainstat_weights_full.get(character_key, {}).get(piece, {}).get(mainstat, 0)
        char_subweights = self.substat_weights_full.get(character_key, {})

        subscore = 0
        for stat_name, val in substats:
            if stat_name == "None":
                continue
            val_conv = val
            if stat_name == "Flat HP":
                val_conv = val / self.MEDIAN_BASE_HP * 100
                val_conv *= self.COEFS.get('HP%', 1.5)
            elif stat_name == "Flat ATK":
                val_conv = val / self.MEDIAN_BASE_ATK * 100
                val_conv *= self.COEFS.get('ATK%', 1.5)
            elif stat_name == "Flat DEF":
                val_conv = val / self.MEDIAN_BASE_DEF * 100
                val_conv *= self.COEFS.get('DEF%', 1.2)
            else:
                coef = self.COEFS.get(stat_name, 1.0)
                val_conv = val * coef
            subscore += val_conv * char_subweights.get(stat_name, 0)

        if is_head_or_hands:
            return subscore
        return 5 * main_wt + 0.8 * subscore

    def run(self):
        st.title("HSR Relic Scorer")

        scoring = st.selectbox("Scoring Criteria", self.scoring_options)
        piece = st.selectbox("Piece", self.piece_choices)

        mainstat_options = self.update_mainstat_choices(piece)
        if not mainstat_options:
            st.warning(f"No valid mainstat options for piece {piece}.")
            mainstat = None
        else:
            mainstat = st.selectbox("Mainstat", mainstat_options)

        st.markdown("---")

        st.write("### Substats")
        substats = []
        total_rolls = 0
        rolls_inputs = []
        invalid_rolls = False

        # For each of the 4 substats, create three inputs (stat, value, rolls)
        for i in range(4):
            col1, col2, col3 = st.columns([3,2,2])
            with col1:
                stat = st.selectbox(f"Substat {i+1}", self.substat_choices, key=f"substat_{i}")
            with col2:
                val = st.number_input(f"Value {i+1}", min_value=0.0, max_value=9999.9, value=0.0, step=0.1, format="%.1f", key=f"value_{i}")
            with col3:
                rolls = st.number_input(f"Rolls {i+1}", min_value=0, max_value=self.MAX_ROLLS, value=0, step=1, key=f"rolls_{i}")

            substats.append((stat, val))
            rolls_inputs.append(rolls)
            total_rolls += rolls

        if total_rolls > self.MAX_ROLLS:
            st.error(f"Total rolls {total_rolls} exceed maximum allowed {self.MAX_ROLLS}.")

        if mainstat is None:
            points = 0
            st.warning("Cannot calculate score without a valid mainstat.")
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
                st.write(f"Substat {i+1}: {stat} | Value: {val} | Rolls: {rolls}")

if __name__ == "__main__":
    app = RelicScorerApp()
    app.run()
