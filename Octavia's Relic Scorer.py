import wx
import json
import os
import re

def normalize_name(s):
    s = s.lower()
    s = re.sub(r'[ .&()-]', '', s)
    return s

class MyFrame(wx.Frame):
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
        super().__init__(parent=None, title="HSR Relic Scorer", size=(750, 630))

        self.mainstat_weights_full = self.load_and_normalize_json("mainstat_weights.json")
        self.substat_weights_full = self.load_and_normalize_json("substat_weights.json")

        if not self.mainstat_weights_full or not self.substat_weights_full:
            wx.MessageBox("Weight files missing or invalid. The app will close.", "Error")
            self.Close()

        panel = wx.Panel(self)
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

        main_sizer = wx.BoxSizer(wx.VERTICAL)
        top_row_sizer = wx.BoxSizer(wx.HORIZONTAL)

        piece_sizer = wx.BoxSizer(wx.VERTICAL)
        label1 = wx.StaticText(panel, label="Piece")
        self.combo_piece = wx.ComboBox(panel, choices=self.piece_choices, style=wx.CB_READONLY)
        piece_sizer.Add(label1, 0, wx.ALL, 5)
        piece_sizer.Add(self.combo_piece, 0, wx.ALL | wx.EXPAND, 5)

        scoring_sizer = wx.BoxSizer(wx.VERTICAL)
        label_scoring = wx.StaticText(panel, label="Scoring Criteria")
        self.combo_scoring = wx.ComboBox(panel, choices=self.scoring_options, style=wx.CB_READONLY)
        scoring_sizer.Add(label_scoring, 0, wx.ALL, 5)
        scoring_sizer.Add(self.combo_scoring, 0, wx.ALL | wx.EXPAND, 5)

        top_row_sizer.Add(piece_sizer, 1, wx.EXPAND | wx.ALL, 5)
        top_row_sizer.Add(scoring_sizer, 1, wx.EXPAND | wx.ALL, 5)
        main_sizer.Add(top_row_sizer, 0, wx.EXPAND)

        label2 = wx.StaticText(panel, label="Mainstat")
        self.combo_mainstat = wx.ComboBox(panel, choices=[], style=wx.CB_READONLY)
        main_sizer.Add(label2, 0, wx.ALL, 5)
        main_sizer.Add(self.combo_mainstat, 0, wx.ALL | wx.EXPAND, 5)

        self.substat_combos = []
        self.value_inputs = []
        self.rolls_inputs = []

        for i in range(4):
            row_sizer = wx.BoxSizer(wx.HORIZONTAL)
            label = wx.StaticText(panel, label=f"Substat {i + 1}")
            row_sizer.Add(label, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)

            combo = wx.ComboBox(panel, choices=self.substat_choices, style=wx.CB_READONLY)
            row_sizer.Add(combo, 1, wx.ALL | wx.EXPAND, 5)

            val_sizer = wx.BoxSizer(wx.VERTICAL)
            val_label = wx.StaticText(panel, label="Value")
            val_spin = wx.SpinCtrlDouble(panel, min=0.0, max=9999.9, initial=0.0, inc=0.1, size=(80, -1))
            val_spin.SetDigits(1)
            val_sizer.Add(val_label, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 0)
            val_sizer.Add(val_spin, 0, wx.ALL, 0)
            row_sizer.Add(val_sizer, 0, wx.ALL, 5)

            rolls_sizer = wx.BoxSizer(wx.VERTICAL)
            rolls_label = wx.StaticText(panel, label="Rolls")
            rolls_spin = wx.SpinCtrl(panel, min=0, max=self.MAX_ROLLS, initial=0, size=(60, -1))
            rolls_sizer.Add(rolls_label, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 0)
            rolls_sizer.Add(rolls_spin, 0, wx.ALL, 0)
            row_sizer.Add(rolls_sizer, 0, wx.ALL, 5)

            main_sizer.Add(row_sizer, 0, wx.EXPAND)

            self.substat_combos.append(combo)
            self.value_inputs.append(val_spin)
            self.rolls_inputs.append(rolls_spin)

        self.label7 = wx.StaticText(panel, label="")
        main_sizer.Add(self.label7, 0, wx.ALL, 5)

        panel.SetSizer(main_sizer)
        self.Centre()
        self.Show()

        self.combo_piece.SetSelection(0)
        self.combo_scoring.SetSelection(0)
        self.UpdateMainstatChoices()
        for i in range(4):
            self.substat_combos[i].SetSelection(0)
            self.value_inputs[i].SetValue(0.0)
            self.rolls_inputs[i].SetValue(0)

        self.combo_piece.Bind(wx.EVT_COMBOBOX, self.OnPieceChanged)
        self.combo_scoring.Bind(wx.EVT_COMBOBOX, self.OnSelectionChanged)
        self.combo_mainstat.Bind(wx.EVT_COMBOBOX, self.OnMainOrSubstatChanged)
        for combo in self.substat_combos:
            combo.Bind(wx.EVT_COMBOBOX, self.OnMainOrSubstatChanged)
        for val_spin in self.value_inputs:
            val_spin.Bind(wx.EVT_SPINCTRLDOUBLE, self.OnValueChanged)
            val_spin.Bind(wx.EVT_TEXT, self.OnValueChanged)
            val_spin.Bind(wx.EVT_KILL_FOCUS, self.OnValueChanged)
        for rolls_spin in self.rolls_inputs:
            rolls_spin.Bind(wx.EVT_SPINCTRL, self.OnRollsSpinChanged)
            rolls_spin.Bind(wx.EVT_TEXT, self.OnRollsSpinChanged)

        self.updating = False
        self.UpdateLabel()

    def load_and_normalize_json(self, filename):
        if not os.path.isfile(filename):
            wx.MessageBox(f"File '{filename}' not found.", "Error")
            return {}
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            wx.MessageBox(f"JSON decode error in {filename}:\n{e}", "Error")
            return {}

        normalized = {}
        for k, v in data.items():
            nk = normalize_name(k)
            normalized[nk] = v
        return normalized

    def denormalize_name(self, normalized_key):
        return ' '.join(word.capitalize() for word in re.findall(r'[a-z]+', normalized_key))

    def UpdateMainstatChoices(self):
        piece = self.combo_piece.GetStringSelection().lower()
        allowed = self.mainstat_for_piece.get(piece, [])

        current = self.combo_mainstat.GetStringSelection()
        if current not in allowed:
            new_sel = allowed[0] if allowed else ""
            self.combo_mainstat.SetItems(allowed)
            if new_sel:
                self.combo_mainstat.SetStringSelection(new_sel)
            else:
                wx.MessageBox(f"No valid mainstat options for piece {self.combo_piece.GetStringSelection()}.", "Warning")
                self.combo_mainstat.SetSelection(wx.NOT_FOUND)
        else:
            self.combo_mainstat.SetItems(allowed)
            self.combo_mainstat.SetStringSelection(current)

    def OnPieceChanged(self, event):
        self.UpdateMainstatChoices()
        self.OnMainOrSubstatChanged(None)
        self.UpdateLabel()

    def OnSelectionChanged(self, event):
        self.UpdateLabel()

    def OnMainOrSubstatChanged(self, event):
        if self.updating:
            return
        self.updating = True
        self.updating = False
        self.UpdateLabel()

    def OnValueChanged(self, event):
        self.UpdateLabel()

    def OnRollsSpinChanged(self, event):
        total_rolls = sum(spin.GetValue() for spin in self.rolls_inputs)
        spin = event.GetEventObject()
        if total_rolls > self.MAX_ROLLS:
            wx.Bell()
            if not hasattr(spin, "_last_valid_value"):
                spin._last_valid_value = 0
            spin.SetValue(spin._last_valid_value)
            return
        spin._last_valid_value = spin.GetValue()
        self.UpdateLabel()

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
            # Check if flat stat to convert
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
                # Multiply percentage stats by their coeff or 1 if unknown
                coef = self.COEFS.get(stat_name, 1.0)
                val_conv = val * coef
            subscore += val_conv * char_subweights.get(stat_name, 0)

        if is_head_or_hands:
            return subscore
        return 5 * main_wt + 0.8 * subscore

    def UpdateLabel(self):
        scoring = self.combo_scoring.GetStringSelection()
        piece = self.combo_piece.GetStringSelection()
        mainstat = self.combo_mainstat.GetStringSelection()

        substats = []
        for i in range(4):
            stat = self.substat_combos[i].GetStringSelection()
            val = self.value_inputs[i].GetValue()
            try:
                val = float(val)
            except Exception:
                val = 0.0
            substats.append((stat, val))

        if normalize_name(scoring) not in self.mainstat_weights_full:
            score_text = f"Character '{scoring}' not in data."
            points = 0
        else:
            points = self.calculate_points(scoring, piece, mainstat, substats)
            score_text = f"Relic Score: {points:.3f}"

        label = (f"Scoring Criteria: {scoring}\n"
                 f"Piece: {piece}\n"
                 f"Mainstat: {mainstat}\n"
                 f"{score_text}")

        for i, (combo, val_input, rolls_input) in enumerate(zip(self.substat_combos, self.value_inputs, self.rolls_inputs)):
            stat = combo.GetStringSelection()
            val = val_input.GetValue()
            rolls = rolls_input.GetValue()
            if stat == "None":
                continue
            label += f"\nSubstat {i+1}: {stat} | Value: {val} | Rolls: {rolls}"

        self.label7.SetLabel(label)


if __name__ == "__main__":
    app = wx.App()
    frame = MyFrame()
    app.MainLoop()
