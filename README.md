
# adhess

> Kevin GUARATO — Mael SOURISSEAU — Cameron LEFEVRE - Martin JAUDINOT  

**Roguelite d’arène 2D sous Pygame** : affrontez des vagues de gobelins, améliorez votre personnage et survivez

## ⚔️ Fonctionnalités

- Vagues successives avec pauses, soins partiels et difficulté croissante  
- Combat dynamique : attaques, dash  
- Améliorations aléatoires entre les vagues (vie, dégâts, vitesse, dash, etc.)  
- Sauvegarde/chargement de la partie  

## 🧩 Prérequis

- Python ≥ 3.10
- Pygame 2.6.1 (`pip install -r requirements.txt`)

## 🚀 Installation

```bash
git clone https://github.com/maelsrs/adhess.git
cd adhess
python -m venv .venv
# Windows .\.venv\Scripts\Activate.ps1
.venv/Scripts/activate
pip install -r requirements.txt
python main.py
````

## 🎮 Commandes par défaut

| Action                 | Touche / Souris                |
| ---------------------- | ------------------------------ |
| Déplacements           | WASD / flèches                 |
| Attaque                | J / clic gauche                |
| Dash                   | Espace ou clic droit   |
| Pause                  | Échap                          |
| Configurer les touches | M                              |

## 📁 Structure

```
.
|-- main.py
|-- requirements.txt
|-- savegame.json
|-- assets/
|   |-- maps/
|   `-- sprites/
`-- adhess/
    |-- animations.py
    |-- constants.py
    |-- data.py
    |-- game.py
    |-- map.py
    `-- entities/
        |-- enemy.py
        `-- player.py
```

## 🛠️ Technologies

* Python 3 / Pygame 2.6.1
* JSON (saves)