###app.py
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash, make_response, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timezone
import pytz
import json
from io import BytesIO
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4

app = Flask(__name__)
app.config['SECRET_KEY'] = 'votre_cle_secrete_ici'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///calculations.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Modèles de données
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    calculations = db.relationship('Calculation', backref='user', lazy=True)

class Calculation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(50), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    parameters = db.Column(db.Text, nullable=False)
    date = db.Column(db.DateTime, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def get_paris_time():
    paris_tz = pytz.timezone('Europe/Paris')
    return datetime.now(paris_tz)

# Routes d'authentification
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Identifiants incorrects')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if User.query.filter_by(username=username).first():
            flash('Nom d\'utilisateur déjà pris')
            return redirect(url_for('register'))

        user = User(
            username=username,
            password_hash=generate_password_hash(password)
        )
        db.session.add(user)
        db.session.commit()
        login_user(user)
        return redirect(url_for('index'))
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# Routes principales
@app.route('/')
@login_required
def index():
    return render_template('index.html')

@app.route('/calculate', methods=['POST'])
@login_required
def calculate():
    try:
        data = request.get_json()
        calculation_type = data.get('type')
        parameters = data.get('parameters', {})

        print(f"🔍 Calcul demandé - Type: {calculation_type}")
        print(f"🔍 Paramètres reçus: {parameters}")

        # Calcul selon le type
        if calculation_type == 'Assurance Vie':
            prime = calculate_life_insurance(parameters)
        elif calculation_type == 'Assurance Non-Vie':
            prime = calculate_non_life_insurance(parameters)
        elif calculation_type == 'Assurance Obligatoire':
            prime = calculate_mandatory_insurance(parameters)
        else:
            return jsonify({'error': 'Type non valide'}), 400

        print(f"💰 Prime calculée: {prime} UM")

        # Sauvegarde du calcul
        calculation = Calculation(
            type=calculation_type,
            amount=prime,
            parameters=json.dumps(parameters),
            date=get_paris_time(),
            user_id=current_user.id
        )
        db.session.add(calculation)
        db.session.commit()

        return jsonify({
            'success': True,
            'prime': prime,
            'calculation_id': calculation.id
        })

    except Exception as e:
        print(f"❌ Erreur calcul: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Fonctions de calcul actuariel
def get_safe_float(value, default=0.0):
    """Convertit safely en float"""
    if value is None or value == '':
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default

def get_safe_bool(value):
    """Convertit safely en booléen"""
    return value in [True, 'true', '1', 1]

# Table de mortalité THP-00/02 (identique au JavaScript)
def get_taux_mortalite(age):
    table_mortalite = {
        18: 0.0005, 19: 0.0005, 20: 0.0006, 21: 0.0006, 22: 0.0007, 23: 0.0007, 24: 0.0008,
        25: 0.0008, 26: 0.0009, 27: 0.0009, 28: 0.0010, 29: 0.0010, 30: 0.0011,
        31: 0.0012, 32: 0.0013, 33: 0.0014, 34: 0.0015, 35: 0.0016,
        36: 0.0017, 37: 0.0019, 38: 0.0020, 39: 0.0022, 40: 0.0024,
        41: 0.0026, 42: 0.0029, 43: 0.0032, 44: 0.0035, 45: 0.0039,
        46: 0.0043, 47: 0.0048, 48: 0.0053, 49: 0.0059, 50: 0.0066,
        51: 0.0074, 52: 0.0083, 53: 0.0093, 54: 0.0104, 55: 0.0117,
        56: 0.0132, 57: 0.0148, 58: 0.0166, 59: 0.0187, 60: 0.0211,
        61: 0.0238, 62: 0.0268, 63: 0.0302, 64: 0.0340, 65: 0.0383,
        66: 0.0431, 67: 0.0485, 68: 0.0546, 69: 0.0614, 70: 0.0690,
        71: 0.0775, 72: 0.0869, 73: 0.0973, 74: 0.1088, 75: 0.1214,
        76: 0.1352, 77: 0.1502, 78: 0.1664, 79: 0.1838, 80: 0.2024
    }
    age_arrondi = max(18, min(80, int(age)))
    return table_mortalite.get(age_arrondi, 0.05)

def get_taux_mortalite_etendu(age):
    """Table de mortalité étendue au-delà de 80 ans"""
    if age <= 80:
        return get_taux_mortalite(age)
    else:
        # Taux de mortalité progressif au-delà de 80 ans
        return min(0.25, 0.05 + (age - 80) * 0.025)

def calculate_prime_deces_temporaire(capital, age, duree, taux, facteur_risque):
    """Calcul prime pour décès temporaire - CORRIGÉ"""
    prime = 0
    taux_interet = taux / 100

    for annee in range(1, int(duree) + 1):
        age_actuel = age + annee - 1
        taux_mortalite = get_taux_mortalite_etendu(age_actuel)
        facteur_actualisation = (1 + taux_interet) ** -annee
        prime += capital * taux_mortalite * facteur_actualisation

    return prime * facteur_risque * 1.2  # 20% de chargement


def calculate_prime_vie_entiere(capital, age, taux, facteur_risque):
    """Calcul prime pour vie entière - FORMULE CORRECTE"""
    prime = 0
    taux_interet = taux / 100
    age_limite = 120

    # La prime est la valeur actuelle de l'espérance de paiement du capital au décès
    for annee in range(1, int(age_limite - age) + 1):
        age_actuel = age + annee - 1

        # Probabilité de mourir précisément à cet âge
        probabilite_deces_precis = 1.0
        for a in range(age, age_actuel):
            probabilite_deces_precis *= (1 - get_taux_mortalite_etendu(a))
        probabilite_deces_precis *= get_taux_mortalite_etendu(age_actuel)

        facteur_actualisation = (1 + taux_interet) ** -annee
        prime += capital * probabilite_deces_precis * facteur_actualisation

    return prime * facteur_risque * 1.15  # 15% de chargement

def calculate_prime_rente_viagere(capital, age, taux, facteur_risque):
    """Calcul prime pour rente viagère - CORRIGÉ"""
    taux_interet = taux / 100
    valeur_actuelle_rente = 0
    age_limite = 120

    # La rente verse un revenu ANNUEL jusqu'au décès (8% du capital)
    rente_annuelle = capital * 0.08

    for annee in range(1, int(age_limite - age) + 1):
        age_actuel = age + annee - 1

        # Probabilité d'être en vie à l'âge actuel
        probabilite_survie = 1.0
        for a in range(age, age_actuel):
            probabilite_survie *= (1 - get_taux_mortalite_etendu(a))

        facteur_actualisation = (1 + taux_interet) ** -annee
        valeur_actuelle_rente += rente_annuelle * probabilite_survie * facteur_actualisation

    # Pour une rente, la prime est la valeur actuelle de tous les flux futurs
    return valeur_actuelle_rente * facteur_risque * 1.15  # 15% de chargement

def calculate_life_insurance(params):
    """Calcul principal pour assurance vie"""
    # Récupération des paramètres avec les mêmes noms que le JavaScript
    capital = get_safe_float(params.get('coverageAmount', 100000))
    age = get_safe_float(params.get('age', 40))
    duree = get_safe_float(params.get('term', 20))
    taux = get_safe_float(params.get('interestRate', 1.5))
    type_contrat = params.get('coverageType', 'deces')

    print(f"📊 Calcul vie - Type: {type_contrat}, Capital: {capital}, Âge: {age}, Durée: {duree}, Taux: {taux}")

    # Validation
    if capital < 1000:
        return 0.0
    if age < 18 or age > 80:
        raise ValueError('L\'âge doit être entre 18 et 80 ans')
    if (type_contrat == 'deces' or type_contrat == 'rente') and (duree < 5 or duree > 40):
        raise ValueError('La durée doit être entre 5 et 40 ans pour ce type de contrat')

        # Pour vie entière, ignorer la durée
    if type_contrat == 'vie_entiere':
        duree = 120 - age  # Couverture jusqu'à 120 ans
    # Facteurs de risque (MÊME LOGIQUE QUE JAVASCRIPT)
    facteur_risque = 1.0

    # Facteur fumeur
    if get_safe_bool(params.get('smokingStatus')):
        facteur_risque *= 1.8
        print("  → Fumeur: ×1.8")

    # Facteur profession à risque
    if get_safe_bool(params.get('highRisk')):
        facteur_risque *= 1.4
        print("  → Profession à risque: ×1.4")

    # Facteurs médicaux
    if get_safe_bool(params.get('hypertension')):
        facteur_risque *= 1.3
        print("  → Hypertension: ×1.3")

    if get_safe_bool(params.get('diabetes')):
        facteur_risque *= 1.5
        print("  → Diabète: ×1.5")

    if get_safe_bool(params.get('heart_disease')):
        facteur_risque *= 2.0
        print("  → Maladie cardiaque: ×2.0")

    print(f"  → Facteur risque total: {facteur_risque}")

    # Calcul selon le type de contrat
    prime_annuelle = 0

    if type_contrat == 'deces':
        prime_annuelle = calculate_prime_deces_temporaire(capital, age, duree, taux, facteur_risque)
        print(f"  → Décès temporaire - Prime annuelle: {prime_annuelle:.2f} UM")
    elif type_contrat == 'vie_entiere':
        prime_annuelle = calculate_prime_vie_entiere(capital, age, taux, facteur_risque)
        print(f"  → Vie entière - Prime annuelle: {prime_annuelle:.2f} UM")
    elif type_contrat == 'rente':
        prime_annuelle = calculate_prime_rente_viagere(capital, age, taux, facteur_risque)
        print(f"  → Rente viagère - Prime annuelle: {prime_annuelle:.2f} UM")
    else:
        raise ValueError('Type de contrat non reconnu')

    # Conversion en mensuel
    prime_mensuelle = prime_annuelle / 12
    resultat = max(5.0, round(prime_mensuelle, 2))

    print(f"💰 Prime mensuelle finale: {resultat} UM")
    return resultat


def calculate_non_life_insurance(params):
    """Calcul pour assurance non-vie - CORRECTION FINALE"""
    valeur = get_safe_float(params.get('coverageAmount', 50000))
    risque = get_safe_float(params.get('riskLevel', 1.0))
    garanties = get_safe_float(params.get('guaranteeLevel', 1.0))

    if valeur < 1000:
        raise ValueError('La valeur assurée doit être d\'au moins 1 000 UM')

    # Taux de base selon le type
    taux_base = 0.015
    type_couverture = params.get('coverageType', 'auto')

    if type_couverture == 'auto':
        taux_base = 0.02
    elif type_couverture == 'home':
        taux_base = 0.012
    elif type_couverture == 'accident':
        taux_base = 0.008

    # Facteurs supplémentaires - APPLIQUER TOUS LES FACTEURS
    facteur_total = 1.0

    # Facteur risque
    facteur_total *= risque

    # Facteur garanties
    facteur_total *= garanties

    # Garanties supplémentaires (multiplicatives)
    if get_safe_bool(params.get('accident')):
        facteur_total *= 1.2
    if get_safe_bool(params.get('theft')):
        facteur_total *= 1.15
    if get_safe_bool(params.get('natural_disaster')):
        facteur_total *= 1.25

    print(f"🔍 Non-Vie - Valeur: {valeur}, Taux: {taux_base}, Facteur total: {facteur_total}")

    prime = valeur * taux_base * facteur_total
    return round(prime, 2)

def calculate_mandatory_insurance(params):
    """Calcul pour assurance obligatoire"""
    base = get_safe_float(params.get('coverageAmount', 20000))
    categorie = get_safe_float(params.get('riskCategory', 1.0))
    region = get_safe_float(params.get('region', 1.0))

    if base < 1000:
        raise ValueError('La base de calcul doit être d\'au moins 1 000 UM')

    # Taux réglementaire selon le type
    taux_reglementaire = 0.02
    type_couverture = params.get('coverageType', 'auto_liability')

    if type_couverture == 'auto_liability':
        taux_reglementaire = 0.015
    elif type_couverture == 'health':
        taux_reglementaire = 0.025
    elif type_couverture == 'professional':
        taux_reglementaire = 0.018

    prime = base * taux_reglementaire * categorie * region
    return round(prime, 2)

# Historique
@app.route('/history')
@login_required
def history():
    calculations = Calculation.query.filter_by(user_id=current_user.id) \
        .order_by(Calculation.date.desc()) \
        .all()
    return render_template('history.html', calculations=calculations)

# Détails du calcul
@app.route('/calculation_details/<int:calculation_id>')
@login_required
def calculation_details(calculation_id):
    calculation = Calculation.query.get_or_404(calculation_id)
    if calculation.user_id != current_user.id:
        flash('Accès non autorisé')
        return redirect(url_for('history'))

    return render_template('calculation_details.html',
                           calculation=calculation,
                           parameters=json.loads(calculation.parameters))

# Génération PDF
@app.route('/generate_pdf/<int:calculation_id>')
@login_required
def generate_pdf(calculation_id):
    try:
        calculation = Calculation.query.get_or_404(calculation_id)
        if calculation.user_id != current_user.id:
            return "Accès non autorisé", 403

        parameters = json.loads(calculation.parameters)

        # Créer le PDF avec reportlab
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=50, bottomMargin=50)
        styles = getSampleStyleSheet()
        story = []

        # Style personnalisé
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            spaceAfter=30,
            alignment=1,
            textColor=colors.HexColor('#2c3e50'),
            fontName='Helvetica-Bold'
        )

        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            spaceAfter=12,
            spaceBefore=20,
            textColor=colors.HexColor('#3498db'),
            fontName='Helvetica-Bold'
        )

        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=10,
            spaceAfter=6
        )

        # Titre principal
        title = Paragraph("RAPPORT DE CALCUL ACTUARIEL", title_style)
        story.append(title)
        story.append(Spacer(1, 20))

        # Informations générales
        story.append(Paragraph("INFORMATIONS GÉNÉRALES", heading_style))

        info_data = [
            [Paragraph("<b>Référence</b>", normal_style), Paragraph(f"CAL-{calculation.id:04d}", normal_style)],
            [Paragraph("<b>Date de génération</b>", normal_style),
             Paragraph(datetime.now().strftime('%d/%m/%Y à %H:%M'), normal_style)],
            [Paragraph("<b>Date du calcul</b>", normal_style),
             Paragraph(calculation.date.strftime('%d/%m/%Y à %H:%M'), normal_style)],
            [Paragraph("<b>Type d'assurance</b>", normal_style), Paragraph(calculation.type, normal_style)],
            [Paragraph("<b>Montant calculé</b>", normal_style),
             Paragraph(f"{calculation.amount:,.2f} UM", normal_style)],
        ]

        info_table = Table(info_data, colWidths=[120, 250])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8f9fa')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#dee2e6')),
        ]))
        story.append(info_table)
        story.append(Spacer(1, 25))

        # Paramètres du calcul
        story.append(Paragraph("PARAMÈTRES DU CALCUL", heading_style))

        # Organiser les paramètres
        param_data = []
        for key, value in parameters.items():
            if key not in ['insuranceBranch']:
                formatted_key = key.replace('_', ' ').title()
                param_data.append([formatted_key, str(value)])

        if param_data:
            param_table = Table(param_data, colWidths=[180, 190])
            param_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e8f4fd')),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e9ecef')),
            ]))
            story.append(param_table)

        story.append(Spacer(1, 25))

        # Notes et mentions légales
        story.append(Paragraph("INFORMATIONS COMPLÉMENTAIRES", heading_style))

        notes_style = ParagraphStyle(
            'NotesStyle',
            parent=styles['Italic'],
            fontSize=9,
            textColor=colors.HexColor('#6c757d'),
            leftIndent=10
        )

        notes = [
            "Ce rapport a été généré automatiquement par le Calculateur Actuariel.",
            "Les calculs sont basés sur les paramètres fournis par l'utilisateur.",
            "Ce document est fourni à titre informatif et ne constitue pas une offre contractuelle.",
            f"Document généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')}"
        ]

        for note in notes:
            story.append(Paragraph(f"• {note}", notes_style))
            story.append(Spacer(1, 4))

        story.append(Spacer(1, 20))

        # Pied de page
        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=8,
            textColor=colors.HexColor('#6c757d'),
            alignment=1
        )

        footer = Paragraph(
            "Calculateur Actuariel - Développé par Enock NIHORIMBERE",
            footer_style
        )
        story.append(footer)

        # Générer le PDF
        doc.build(story)
        buffer.seek(0)

        return send_file(
            buffer,
            as_attachment=True,
            download_name=f'rapport_calcul_{calculation.id}.pdf',
            mimetype='application/pdf'
        )

    except Exception as e:
        print(f"Erreur génération PDF: {str(e)}")
        return f"Erreur lors de la génération du PDF: {str(e)}", 500

# Initialisation de la base de données
with app.app_context():
    db.create_all()

    # Créer un utilisateur admin par défaut si nécessaire
    if not User.query.filter_by(username='admin').first():
        admin = User(
            username='admin',
            password_hash=generate_password_hash('admin123')
        )
        db.session.add(admin)
        db.session.commit()

if __name__ == '__main__':
    app.run(debug=True)