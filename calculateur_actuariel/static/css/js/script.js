$(document).ready(function() {
    console.log("Calculateur actuariel initialisé");

    // Fonction pour changer de branche d'assurance
    function selectBranch(branch) {
        console.log("Sélection de la branche:", branch);

        // Masquer toutes les sections
        $('.branch-section').hide();

        // Afficher la section sélectionnée
        $('#' + branch + '-section').show();

        // Mettre à jour le champ caché
        $('#insuranceBranch').val(branch);

        // Mettre à jour l'apparence des options
        $('.branch-option').removeClass('active');
        $('.branch-option[data-branch="' + branch + '"]').addClass('active');

        // Désactiver tous les champs de formulaire d'abord
        $('select[name="coverageType"], input[name="coverageAmount"], input[name="term"]').prop('disabled', true);

        // Activer seulement les champs de la section active
        $('#' + branch + '-section select, #' + branch + '-section input').prop('disabled', false);
    }

    // Gestionnaire de clic pour les options de branche
    $('.branch-option').click(function() {
        const branch = $(this).data('branch');
        selectBranch(branch);
    });

    // Gestionnaire de soumission du formulaire
    $('#premiumForm').submit(function(e) {
        const calculateBtn = $('#calculateBtn');
        calculateBtn.html('<i class="fas fa-spinner fa-spin"></i> Calcul en cours...');
        calculateBtn.prop('disabled', true);

        // Désactiver tous les champs avant soumission pour éviter les conflits
        $('.branch-section select, .branch-section input').prop('disabled', true);
    });

    // Initialisation
    selectBranch('vie');
});
        // Gestion des onglets
        document.querySelectorAll('[data-tab]').forEach(tab => {
            tab.addEventListener('click', (e) => {
                this.switchTab(tab.getAttribute('data-tab'));
            });
        });
    }

    setupCharts() {
        // Initialiser les graphiques avec Chart.js
        this.charts = {
            allocation: this.createAllocationChart(),
            risk: this.createRiskChart(),
            stressTest: this.createStressTestChart()
        };
    }

    createAllocationChart() {
        const ctx = document.getElementById('allocation-chart');
        if (!ctx) return null;

        return new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: [],
                datasets: [{
                    data: [],
                    backgroundColor: [
                        '#3b82f6', '#ef4444', '#10b981', '#f59e0b',
                        '#8b5cf6', '#06b6d4', '#84cc16', '#f97316'
                    ]
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        position: 'bottom'
                    },
                    title: {
                        display: true,
                        text: 'Répartition du Portefeuille'
                    }
                }
            }
        });
    }

    createRiskChart() {
        const ctx = document.getElementById('risk-chart');
        if (!ctx) return null;

        return new Chart(ctx, {
            type: 'bar',
            data: {
                labels: ['VaR 95%', 'Expected Shortfall', 'Stress Test Max', 'SCR'],
                datasets: [{
                    label: 'Exposition au Risque (€)',
                    data: [],
                    backgroundColor: '#ef4444'
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    title: {
                        display: true,
                        text: 'Métriques de Risque'
                    }
                }
            }
        });
    }

    async runSimulation() {
        const form = document.querySelector('#simulation-form');
        const formData = new FormData(form);

        const simulationData = {
            type: formData.get('simulation-type'),
            portfolio: this.getSelectedPortfolio(),
            parameters: this.getSimulationParameters(),
            scenarios: this.getSelectedScenarios()
        };

        try {
            this.showLoading();
            const response = await fetch(`${this.baseUrl}/simulations/${simulationData.type}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(simulationData)
            });

            if (!response.ok) throw new Error('Erreur lors de la simulation');

            const result = await response.json();
            this.currentSimulation = result;
            this.showSimulationResults(result);
            this.loadRecentSimulations(); // Rafraîchir la liste

        } catch (error) {
            console.error('Simulation error:', error);
            this.showError('Erreur lors de l\'exécution de la simulation');
        } finally {
            this.hideLoading();
        }
    }

    showSimulationResults(result) {
        this.showSection('results');
        this.updateResultsDisplay(result);
        this.updateChartsWithResults(result);
    }

    updateResultsDisplay(result) {
        const resultsDiv = document.getElementById('simulation-results');
        if (!resultsDiv) return;

        resultsDiv.innerHTML = `
            <div class="bg-white rounded-lg shadow-lg p-6 animate-fade-in">
                <h3 class="text-xl font-bold mb-4">Résultats de la Simulation</h3>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div class="space-y-4">
                        <div class="metric-card">
                            <h4 class="font-semibold">Valeur du Portefeuille</h4>
                            <p class="text-2xl text-green-600">${this.formatCurrency(result.results.portfolio_value)}</p>
                        </div>
                        <div class="metric-card">
                            <h4 class="font-semibold">Perte Maximale</h4>
                            <p class="text-2xl text-red-600">${this.formatCurrency(result.results.max_loss)}</p>
                        </div>
                    </div>
                    <div class="space-y-4">
                        <div class="metric-card">
                            <h4 class="font-semibold">Scénario le Plus Sévère</h4>
                            <p class="text-lg">${result.results.most_severe_scenario}</p>
                        </div>
                        <div class="metric-card">
                            <h4 class="font-semibold">Ratio de Perte</h4>
                            <p class="text-2xl ${(result.results.max_loss / result.results.portfolio_value * 100) > 20 ? 'text-red-600' : 'text-green-600'}">
                                ${(result.results.max_loss / result.results.portfolio_value * 100).toFixed(2)}%
                            </p>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    async viewSimulation(simulationId) {
        try {
            const response = await fetch(`${this.baseUrl}/reports/${simulationId}`);
            const report = await response.json();
            this.showReportModal(report);
        } catch (error) {
            console.error('Error viewing simulation:', error);
            this.showError('Erreur lors du chargement du rapport');
        }
    }

    async downloadSimulation(simulationId) {
        try {
            const response = await fetch(`${this.baseUrl}/download/${simulationId}`);
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `simulation_${simulationId}_report.json`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        } catch (error) {
            console.error('Error downloading simulation:', error);
            this.showError('Erreur lors du téléchargement');
        }
    }

    showSection(sectionId) {
        // Masquer toutes les sections
        document.querySelectorAll('.section').forEach(section => {
            section.classList.add('hidden');
        });

        // Afficher la section demandée
        const targetSection = document.getElementById(sectionId);
        if (targetSection) {
            targetSection.classList.remove('hidden');
        }

        // Mettre à jour la navigation
        document.querySelectorAll('nav a').forEach(link => {
            link.classList.remove('active');
            if (link.getAttribute('href') === `#${sectionId}`) {
                link.classList.add('active');
            }
        });
    }

    switchTab(tabName) {
        // Masquer tous les contenus d'onglets
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.add('hidden');
        });

        // Afficher l'onglet sélectionné
        const targetTab = document.getElementById(`${tabName}-tab`);
        if (targetTab) {
            targetTab.classList.remove('hidden');
        }

        // Mettre à jour les onglets actifs
        document.querySelectorAll('[data-tab]').forEach(tab => {
            tab.classList.remove('active');
            if (tab.getAttribute('data-tab') === tabName) {
                tab.classList.add('active');
            }
        });
    }

    showLoading() {
        const loading = document.getElementById('loading');
        if (loading) loading.classList.remove('hidden');
    }

    hideLoading() {
        const loading = document.getElementById('loading');
        if (loading) loading.classList.add('hidden');
    }

    showError(message) {
        // Implémenter un système de notification d'erreur
        console.error('Error:', message);
        alert(message); // À remplacer par un système de notification plus élégant
    }

    formatCurrency(amount) {
        return new Intl.NumberFormat('fr-FR', {
            style: 'currency',
            currency: 'EUR',
            minimumFractionDigits: 2
        }).format(amount);
    }

    truncateText(text, maxLength) {
        return text.length > maxLength ? text.substring(0, maxLength) + '...' : text;
    }

    populatePortfolioSelect() {
        const select = document.getElementById('portfolio-select');
        if (!select) return;

        select.innerHTML = this.portfolios.map(portfolio => `
            <option value="${portfolio.id}">${portfolio.name} (${this.formatCurrency(portfolio.total_value)})</option>
        `).join('');
    }

    populateScenarioSelect() {
        const container = document.getElementById('scenarios-container');
        if (!container) return;

        container.innerHTML = this.scenarios.map(scenario => `
            <label class="flex items-center space-x-2 p-2 border rounded">
                <input type="checkbox" name="scenarios" value="${scenario.id}" ${scenario.is_default ? 'checked' : ''}>
                <span>${scenario.name}</span>
                <span class="text-sm text-gray-500">${scenario.description}</span>
            </label>
        `).join('');
    }

    getSelectedPortfolio() {
        const select = document.getElementById('portfolio-select');
        return this.portfolios.find(p => p.id == select.value) || this.portfolios[0];
    }

    getSelectedScenarios() {
        const checkboxes = document.querySelectorAll('input[name="scenarios"]:checked');
        return Array.from(checkboxes).map(cb => {
            return this.scenarios.find(s => s.id == cb.value);
        }).filter(Boolean);
    }

    getSimulationParameters() {
        // Récupérer les paramètres spécifiques au type de simulation
        const type = document.querySelector('#simulation-type').value;
        const params = {};

        if (type === 'market-risk') {
            params.confidence_level = parseFloat(document.querySelector('#confidence-level').value);
            params.time_horizon = parseInt(document.querySelector('#time-horizon').value);
            params.method = document.querySelector('#var-method').value;
        }

        return params;
    }
}

// Initialiser l'application lorsque la page est chargée
document.addEventListener('DOMContentLoaded', () => {
    window.app = new FinRiskSimulator();
});