from flask import Flask, render_template, request
from flask_wtf import FlaskForm
from wtforms import Form, FieldList, FormField, SelectField, DecimalField, SubmitField
from wtforms.validators import NumberRange, Optional
import json
import re

app = Flask(__name__)
app.secret_key = 'your-secret-key'  # Replace this with a secure secret in production

SUBSTAT_CHOICES = [
    ('None', 'None'), ('CritRate', 'CritRate'), ('CritDMG', 'CritDMG'), ('Break%', 'Break%'),
    ('SPD', 'SPD'), ('ATK%', 'ATK%'), ('HP%', 'HP%'), ('EHR%', 'EHR%'), ('EffectRES%', 'EffectRES%'),
    ('DEF%', 'DEF%'), ('Flat HP', 'Flat HP'), ('Flat ATK', 'Flat ATK'), ('Flat DEF', 'Flat DEF')
]

PIECE_CHOICES = [
    ('Head', 'Head'), ('Hands', 'Hands'), ('Chest', 'Chest'), ('Boots', 'Boots'),
    ('Sphere', 'Sphere'), ('Rope', 'Rope')
]

CHARACTER_CHOICES = [
    ('acheron', 'Acheron'), ('aglaea', 'Aglaea'), ('anaxa', 'Anaxa')  # Add more or generate dynamically from weights
]

MAINSTAT_CHOICES_BY_PIECE = {
    "head": [("Flat HP", "Flat HP")],
    "hands": [("Flat ATK", "Flat ATK")],
    "chest": [("HP%", "HP%"), ("ATK%", "ATK%"), ("DEF%", "DEF%"), ("CritRate", "CritRate"), ("CritDMG", "CritDMG"), ("Heal%", "Heal%"), ("EHR%", "EHR%")],
    "boots": [("HP%", "HP%"), ("ATK%", "ATK%"), ("DEF%", "DEF%"), ("SPD", "SPD")],
    "sphere": [("Elemental%(Correct)", "Elemental%(Correct)"), ("Elemental%(Wrong)", "Elemental%(Wrong)"), ("HP%", "HP%"), ("ATK%", "ATK%"), ("DEF%", "DEF%")],
    "rope": [("HP%", "HP%"), ("ATK%", "ATK%"), ("DEF%", "DEF%"), ("EnergyRegen%", "EnergyRegen%"), ("Break%", "Break%")]
}

class SubstatForm(Form):
    name = SelectField('Stat Name', choices=SUBSTAT_CHOICES)
    value = DecimalField('Value', validators=[Optional(), NumberRange(min=0)], default=0)


class RelicForm(FlaskForm):
    character = SelectField('Character', choices=CHARACTER_CHOICES)
    piece = SelectField('Piece', choices=PIECE_CHOICES)
    mainstat = SelectField('Mainstat', choices=[])
    substats = FieldList(FormField(SubstatForm), min_entries=4)
    submit = SubmitField('Calculate')


def normalize_name(s):
    return re.sub(r'[ .&()-]', '', s.lower())


def load_weights():
    with open("mainstat_weights.json", "r", encoding="utf-8") as f:
        mainstats = json.load(f)
    with open("substat_weights.json", "r", encoding="utf-8") as f:
        substats = json.load(f)

    mainstats_norm = {normalize_name(k): v for k, v in mainstats.items()}
    substats_norm = {normalize_name(k): v for k, v in substats.items()}
    return mainstats_norm, substats_norm

mainstat_weights_full, substat_weights_full = load_weights()

# Median base stats and coefficients same as before for relic scoring
MEDIAN_BASE_ATK = 1149
MEDIAN_BASE_HP = 2271
MEDIAN_BASE_DEF = 988
COEFS = {
    'CritRate': 2.0,
    'SPD': 2.5,
    'ATK%': 1.5,
    'HP%': 1.5,
    'EHR%': 1.5,
    'EffectRES%': 1.5,
    'DEF%': 1.2,
    'Break%': 1.0,
    'CritDMG': 1.0
}

@app.route('/', methods=['GET', 'POST'])
def index():
    form = RelicForm()

    # Update mainstat choices based on piece
    piece = form.piece.data or 'Chest'
    mainstat_choices = MAINSTAT_CHOICES_BY_PIECE.get(piece.lower(), [])
    form.mainstat.choices = mainstat_choices
    if not form.mainstat.data and mainstat_choices:
        form.mainstat.data = mainstat_choices[0][0]

    score = None
    if form.validate_on_submit():
        character_key = form.character.data
        piece = form.piece.data
        mainstat = form.mainstat.data
        substats = [(subform.name.data, float(subform.value.data or 0)) for subform in form.substats]

        score = calculate_relic_score(character_key, piece, mainstat, substats)

    return render_template('index.html', form=form, score=score)

def calculate_relic_score(character, piece, mainstat, substats):
    character_key = normalize_name(character)
    piece_lower = piece.lower()
    is_head_or_hands = piece_lower in ['head', 'hands']

    main_wt = mainstat_weights_full.get(character_key, {}).get(piece, {}).get(mainstat, 0)
    sub_weights = substat_weights_full.get(character_key, {})

    subscore = 0
    for stat_name, val in substats:
        if stat_name == 'None' or val == 0:
            continue

        val_conv = val
        if stat_name == "Flat HP":
            val_conv = val / MEDIAN_BASE_HP * 100 * COEFS.get('HP%', 1.5)
        elif stat_name == "Flat ATK":
            val_conv = val / MEDIAN_BASE_ATK * 100 * COEFS.get('ATK%', 1.5)
        elif stat_name == "Flat DEF":
            val_conv = val / MEDIAN_BASE_DEF * 100 * COEFS.get('DEF%', 1.2)
        else:
            coef = COEFS.get(stat_name, 1.0)
            val_conv = val * coef

        subscore += val_conv * sub_weights.get(stat_name, 0)

    if is_head_or_hands:
        return subscore
    else:
        return 5 * main_wt + 0.8 * subscore

if __name__ == '__main__':
    app.run(debug=True)
