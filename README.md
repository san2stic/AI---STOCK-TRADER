# Multi-AI Autonomous Trading System 🤖📈

Une plateforme de trading algorithmique utilisant 6 modèles d'IA générative (GPT-4, Claude, Gemini, Grok, DeepSeek, Mistral) qui tradent de manière autonome sur les marchés américains.

## 🎯 Caractéristiques

- **6 Agents IA** avec personnalités et stratégies distinctes
- **Trading Autonome** 24/7 pendant les heures de marché US
- **Paper Trading** par défaut (simulation sécurisée)
- **Gestion des Risques** automatique (stop-loss, circuit breakers)
- **Dashboard Temps Réel** avec WebSocket
- **Auto-Critique** - Les agents apprennent de leurs erreurs
- **API Alpaca Markets 100% Gratuite** pour trading réel et paper

## 🤖 Les Agents

1. **GPT-4 "The Holder"** - Investisseur long terme (stratégie Buy & Hold)
2. **Claude "L'Équilibré"** - Gestionnaire prudent diversifié
3. **Grok "Le Sniper"** - Trader agressif opportuniste
4. **Gemini "Le Gestionnaire"** - Spécialiste risk management ultra-conservateur  
5. **DeepSeek "Le Nerveux"** - Chasseur de momentum réactif
6. **Mistral "Le Marine"** - Trader actif persistant

## 🚀 Démarrage Rapide

### Prérequis

- Docker & Docker Compose
- Clé API OpenRouter
- (Optionnel) Compte Alpaca Markets gratuit pour trading réel

### Installation

1. **Cloner et configurer**

```bash
cd "AI - STOCK TRADER"
cp .env.example .env
```

2. **Configurer .env**

Éditer `.env` et renseigner:
```bash
OPENROUTER_API_KEY=your_key_here
TRADING_MODE=PAPER  # ou LIVE pour trading réel
INITIAL_CAPITAL=10000
```

3. **Lancer le système**

```bash
docker-compose up -d
```

4. **Accéder au dashboard**

- Frontend: http://localhost:3000
- API Backend: http://localhost:8000
- API Docs: http://localhost:8000/docs

## 📊 API Endpoints

- `GET /` - Informations système
- `GET /health` - Status santé
- `GET /agents` - Liste tous les agents et performances
- `GET /agents/{agent_name}` - Détails d'un agent
- `GET /trades` - Historique des trades
- `POST /agents/{agent_name}/reflect` - Déclencher réflexion agent
- `WebSocket /ws` - Flux temps réel

## 🛡️ Gestion des Risques

### Paramètres par Défaut

- ⚠️ Max 10% du capital par trade
- 🛑 Stop-loss automatique à -15% par position
- 🚨 Circuit breaker si perte journalière > 5%
- 📊 Max 10 positions simultanées par agent

### Modification

Ajuster dans `.env`:
```bash
MAX_TRADE_PERCENT=10
STOP_LOSS_PERCENT=15
CIRCUIT_BREAKER_PERCENT=5
```

## 🔄 Cycle de Trading

```
09:25 CET - Préparation pré-marché
09:30 CET - Début trading
Toutes les 30 min:
  1. Collecte données marché
  2. Agents prennent décisions en parallèle
  3. Exécution des ordres validés
  4. Mise à jour portfolios
  5. Broadcast WebSocket
22:00 CET - Clôture et rapport journalier
22:15 CET - Auto-critiques si seuil atteint
```

## 📁 Structure du Projet

```
AI - STOCK TRADER/
├── backend/
│   ├── agents/         # 6 agents IA
│   ├── services/       # OpenRouter, IB, data collector
│   ├── tools/          # Trading tools (buy/sell/etc)
│   ├── models/         # Database models
│   ├── main.py         # FastAPI app
│   ├── scheduler.py    # Orchestrateur
│   └── config.py       # Configuration
├── frontend/           # Dashboard Next.js
├── docker-compose.yml
└── .env
```

## ⚙️ Configuration Avancée

### Symboles Autorisés

Limiter les actions tradables:
```bash
ALLOWED_SYMBOLS=AAPL,MSFT,GOOGL,NVDA,TSLA
```

### Fréquence de Trading

```bash
TRADING_INTERVAL_MINUTES=30  # Décisions toutes les 30 min
```

### Auto-Critique

```bash
AUTO_CRITIQUE_FREQUENCY=5  # Réflexion après 5 trades
```

## 🔌 Alpaca Markets API

**API 100% Gratuite - Aucun frais d'abonnement**

### Inscription (Gratuite)

1. Aller sur https://alpaca.markets/
2. Créer un compte (Paper Trading - aucune carte bancaire requise)
3. Récupérer vos clés API dans le dashboard

### Configuration

```bash
# Dans .env
ALPACA_API_KEY=votre_clé_api
ALPACA_API_SECRET=votre_secret_api

# Paper trading (par défaut)
ALPACA_BASE_URL=https://paper-api.alpaca.markets

# Live trading (trading réel)
# ALPACA_BASE_URL=https://api.alpaca.markets
```

### Avantages Alpaca

✅ **Gratuit** : Pas de frais mensuels, pas de minimum de dépôt
✅ **Simple** : API REST moderne, pas besoin d'installer de logiciel
✅ **Paper Trading** : Environnement de test complet avec capital virtuel
✅ **Données gratuites** : Prix en temps réel inclus
✅ **Documentation** : https://alpaca.markets/docs/

### Migration depuis Interactive Brokers

Pour passer en trading réel (NON recommandé sans expérience):

1. Créer un compte Alpaca Live (vérification d'identité requise)
2. Changer `ALPACA_BASE_URL` vers l'URL live
3. Définir `TRADING_MODE=LIVE` dans `.env`

## 📈 Dashboard Features

- 📊 Performance globale et par agent
- 📉 Graphiques P&L temps réel
- 🏆 Leaderboard des agents
- 📰 Flux de décisions en direct
- 💬 Raisonnements des IA
- 📝 Auto-critiques et apprentissage

## 🧪 Mode Paper Trading

Le système démarre en **paper trading** par défaut:
- Capital virtuel de $10,000 par agent
- Simulation réaliste avec slippage
- Zéro risque financier
- Données de marché réelles ou mockées

## ⚠️ Avertissements

> **IMPORTANT**: Ce système peut effectuer des transactions réelles.
> - Commencez TOUJOURS en mode PAPER
> - Testez pendant au moins 2 semaines
> - Utilisez un capital limité en mode LIVE
> - Les performances passées ne garantissent pas les résultats futurs
> - Le trading comporte des risques de perte de capital

## 🛠️ Développement

### Tests

```bash
cd backend
pytest tests/ -v
```

### Logs

```bash
docker-compose logs -f backend
```

### Base de Données

```bash
# Accéder à PostgreSQL
docker-compose exec postgres psql -U trader -d trading_system
```

## 📝 Licence

MIT License - Utilisez à vos risques et périls

## 🤝 Support

Pour questions et issues, créer une issue GitHub.

---

**Disclaimer**: Ce projet est à des fins éducatives. L'utilisation pour du trading réel est à vos propres risques.
