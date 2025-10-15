import math


class PremiumCalculator:
    def __init__(self, age, gender, coverage_type, insurance_branch, coverage_amount,
                 term, smoking_status, health_conditions, risk_factors=None):
        self.age = age
        self.gender = gender
        self.coverage_type = coverage_type
        self.insurance_branch = insurance_branch  # vie, non_vie, obligatoire
        self.coverage_amount = coverage_amount
        self.term = term
        self.smoking_status = smoking_status
        self.health_conditions = health_conditions
        self.risk_factors = risk_factors or {}

        # Tables de mortalité simplifiées (taux annuels de mortalité par âge)
        self.mortality_table = {
            'male': [0.001, 0.001, 0.001, 0.001, 0.001, 0.001, 0.002, 0.002, 0.003, 0.003,
                     0.004, 0.004, 0.005, 0.006, 0.007, 0.008, 0.009, 0.011, 0.013, 0.015,
                     0.018, 0.021, 0.025, 0.029, 0.034, 0.04, 0.047, 0.055, 0.064, 0.075,
                     0.087, 0.101, 0.117, 0.135, 0.155, 0.178, 0.203, 0.231, 0.262, 0.296,
                     0.333, 0.374, 0.418, 0.466, 0.518, 0.574, 0.634, 0.698, 0.766, 0.838,
                     0.914, 0.994, 1.078, 1.166, 1.258, 1.354, 1.454, 1.558, 1.666, 1.778],
            'female': [0.001, 0.001, 0.001, 0.001, 0.001, 0.001, 0.001, 0.001, 0.002, 0.002,
                       0.002, 0.002, 0.003, 0.003, 0.004, 0.004, 0.005, 0.005, 0.006, 0.007,
                       0.008, 0.009, 0.01, 0.012, 0.014, 0.016, 0.019, 0.022, 0.026, 0.03,
                       0.035, 0.041, 0.048, 0.056, 0.065, 0.075, 0.087, 0.1, 0.115, 0.131,
                       0.149, 0.169, 0.191, 0.215, 0.241, 0.27, 0.301, 0.335, 0.371, 0.41,
                       0.452, 0.497, 0.545, 0.596, 0.65, 0.707, 0.767, 0.83, 0.896, 0.965]
        }

        # Taux d'intérêt technique (3%)
        self.interest_rate = 0.03

        # Facteurs de risque selon les conditions de santé
        self.health_risk_factors = {
            'hypertension': 1.2,
            'diabetes': 1.5,
            'heart_disease': 2.0,
            'cancer': 2.5,
            'asthma': 1.1,
            'none': 1.0
        }

        # Facteurs de risque pour l'assurance non-vie
        self.non_life_risk_factors = {
            'accident': 1.3,
            'theft': 1.5,
            'natural_disaster': 2.0,
            'liability': 1.8,
            'professional': 2.2
        }

        # Tarifs de base par type d'assurance obligatoire
        self.mandatory_insurance_rates = {
            'auto_liability': 0.025,  # 2.5% de la valeur du véhicule
            'health': 0.015,  # 1.5% du revenu annuel
            'professional': 0.02,  # 2% du chiffre d'affaires
            'home': 0.01  # 1% de la valeur du bien
        }

    def get_mortality_rate(self, age_offset=0):
        """Obtenir le taux de mortalité selon l'âge et le sexe"""
        age_index = min(self.age + age_offset - 18, 59)  # À partir de 18 ans
        age_index = max(0, age_index)  # Éviter les index négatifs

        if self.gender == 'male':
            return self.mortality_table['male'][age_index] / 1000
        else:
            return self.mortality_table['female'][age_index] / 1000

    def calculate_premium(self):
        """Calculer la prime actuarielle selon la branche d'assurance"""
        if self.insurance_branch == 'vie':
            return self.calculate_life_insurance_premium()
        elif self.insurance_branch == 'non_vie':
            return self.calculate_non_life_insurance_premium()
        else:  # obligatoire
            return self.calculate_mandatory_insurance_premium()

    def calculate_life_insurance_premium(self):
        """Calculer la prime pour une assurance vie"""
        # Prime de base selon le type de couverture
        if self.coverage_type == 'life':
            base_premium = self.calculate_life_insurance()
        elif self.coverage_type == 'health':
            base_premium = self.calculate_health_insurance()
        else:
            base_premium = self.calculate_annuity_premium()

        # Appliquer les facteurs de risque
        risk_factor = self.get_risk_factor()

        # Prime finale
        final_premium = base_premium * risk_factor

        return final_premium

    def calculate_life_insurance(self):
        """Calculer la prime pour une assurance vie classique"""
        # Probabilité de survie et facteur d'actualisation
        premium = 0
        for t in range(self.term):
            # Probabilité de décès durant l'année t
            mortality_rate_t = self.get_mortality_rate(t)

            # Facteur d'actualisation
            discount_factor = 1 / ((1 + self.interest_rate) ** (t + 1))

            # Prime pour l'année t
            premium += mortality_rate_t * self.coverage_amount * discount_factor

        # Prime annuelle
        annual_premium = premium / self.calculate_annuity_factor()

        return annual_premium

    def calculate_health_insurance(self):
        """Calculer la prime pour une assurance santé"""
        # Prime basée sur l'âge et le montant de couverture
        base_rate = 0.005  # 0.5% du montant de couverture

        # Majoration selon l'âge
        age_factor = 1 + (self.age - 30) * 0.03  # 3% par année au-dessus de 30

        premium = self.coverage_amount * base_rate * age_factor

        return premium

    def calculate_annuity_premium(self):
        """Calculer la prime pour une rente"""
        # Calcul simplifié d'une rente viagère
        survival_probabilities = 1.0
        annuity_value = 0

        for t in range(self.term):
            # Probabilité de survie jusqu'à l'année t
            if t > 0:
                mortality_rate_prev = self.get_mortality_rate(t - 1)
                survival_probabilities *= (1 - mortality_rate_prev)

            # Facteur d'actualisation
            discount_factor = 1 / ((1 + self.interest_rate) ** t)

            # Valeur de la rente pour l'année t
            annuity_value += survival_probabilities * discount_factor

        # Prime unique pour la rente
        premium = self.coverage_amount * annuity_value

        return premium

    def calculate_non_life_insurance_premium(self):
        """Calculer la prime pour une assurance non-vie"""
        # Tarif de base selon le type de couverture
        base_rates = {
            'auto': 0.04,  # 4% de la valeur du véhicule
            'home': 0.002,  # 0.2% de la valeur du bien
            'accident': 0.0015,  # 0.15% du capital
            'liability': 0.003,  # 0.3% du plafond de garantie
            'travel': 0.005  # 0.5% du capital
        }

        base_rate = base_rates.get(self.coverage_type, 0.003)
        base_premium = self.coverage_amount * base_rate

        # Appliquer les facteurs de risque spécifiques
        risk_factor = 1.0
        for risk, value in self.risk_factors.items():
            if value:  # Si le risque est présent
                risk_factor *= self.non_life_risk_factors.get(risk, 1.0)

        # Majoration selon l'âge pour certaines assurances
        if self.coverage_type in ['auto', 'accident']:
            age_factor = 1.0
            if self.age < 25:
                age_factor = 1.5
            elif self.age > 65:
                age_factor = 1.3
            risk_factor *= age_factor

        return base_premium * risk_factor

    def calculate_mandatory_insurance_premium(self):
        """Calculer la prime pour une assurance obligatoire"""
        base_rate = self.mandatory_insurance_rates.get(self.coverage_type, 0.02)

        # Calcul selon le type d'assurance obligatoire
        if self.coverage_type == 'auto_liability':
            # Basé sur la valeur du véhicule
            return self.coverage_amount * base_rate

        elif self.coverage_type == 'health':
            # Basé sur le revenu annuel
            return self.coverage_amount * base_rate

        elif self.coverage_type == 'professional':
            # Basé sur le chiffre d'affaires
            return self.coverage_amount * base_rate

        elif self.coverage_type == 'home':
            # Basé sur la valeur du bien
            return self.coverage_amount * base_rate

        else:
            return self.coverage_amount * 0.015  # Tarif par défaut

    def calculate_annuity_factor(self):
        """Calculer le facteur de rente pour le paiement de la prime"""
        annuity_factor = 0
        survival_probability = 1.0

        for t in range(self.term):
            # Probabilité de survie jusqu'à l'année t
            if t > 0:
                mortality_rate_prev = self.get_mortality_rate(t - 1)
                survival_probability *= (1 - mortality_rate_prev)

            # Facteur d'actualisation
            discount_factor = 1 / ((1 + self.interest_rate) ** t)

            # Contribution au facteur de rente
            annuity_factor += survival_probability * discount_factor

        return annuity_factor

    def get_premium_breakdown(self):
        """Obtenir une décomposition détaillée de la prime"""
        if self.insurance_branch == 'vie':
            base_premium = self.calculate_premium() / self.get_risk_factor()
            return {
                'base_premium': round(base_premium, 2),
                'smoking_surcharge': round(base_premium * (1.8 - 1) if self.smoking_status else 0, 2),
                'health_surcharge': round(base_premium * (self.get_health_factor() - 1), 2),
                'total_premium': round(self.calculate_premium(), 2)
            }
        elif self.insurance_branch == 'non_vie':
            base_premium = self.calculate_premium() / self.get_non_life_risk_factor()
            return {
                'base_premium': round(base_premium, 2),
                'risk_surcharge': round(self.calculate_premium() - base_premium, 2),
                'total_premium': round(self.calculate_premium(), 2)
            }
        else:  # obligatoire
            return {
                'base_premium': round(self.calculate_premium(), 2),
                'total_premium': round(self.calculate_premium(), 2)
            }

    def get_risk_factor(self):
        """Calculer le facteur de risque total pour l'assurance vie"""
        risk_factor = 1.0
        if self.smoking_status:
            risk_factor *= 1.8

        for condition in self.health_conditions:
            risk_factor *= self.health_risk_factors.get(condition, 1.0)

        return risk_factor

    def get_non_life_risk_factor(self):
        """Calculer le facteur de risque pour l'assurance non-vie"""
        risk_factor = 1.0
        for risk, value in self.risk_factors.items():
            if value:  # Si le risque est présent
                risk_factor *= self.non_life_risk_factors.get(risk, 1.0)

        # Majoration selon l'âge pour certaines assurances
        if self.coverage_type in ['auto', 'accident']:
            if self.age < 25:
                risk_factor *= 1.5
            elif self.age > 65:
                risk_factor *= 1.3

        return risk_factor

    def get_health_factor(self):
        """Calculer seulement le facteur de santé"""
        health_factor = 1.0
        for condition in self.health_conditions:
            health_factor *= self.health_risk_factors.get(condition, 1.0)

        return health_factor