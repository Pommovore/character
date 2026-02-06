"""Service d'extraction de traits utilisant les modèles Hugging Face.

Ce module fournit des fonctionnalités pour extraire les traits de caractère à partir de descriptions textuelles
en utilisant des modèles transformer pré-entraînés de Hugging Face.
"""

import logging
from typing import Dict, List, Optional, Tuple

from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline
import numpy as np

from src.models.character_traits import CharacterTrait

# Configuration du logging
logger = logging.getLogger(__name__)

# Catégories de traits de caractère prédéfinies et traits associés
TRAIT_CATEGORIES = {
    "Personnalité": [
        "Courageux", "Ambitieux", "Intelligent", "Compatissant", "Curieux",
        "Loyal", "Indépendant", "Créatif", "Responsable", "Optimiste",
        "Pessimiste", "Prudent", "Aventureux", "Introverti", "Extraverti"
    ],
    "Valeurs": [
        "Honnête", "Fiable", "Juste", "Honorable", "Respectueux",
        "Généreux", "Égoïste", "Matérialiste", "Spirituel", "Traditionnel"
    ],
    "Émotions": [
        "Joyeux", "Craintif", "Colérique", "Mélancolique", "Serein",
        "Anxieux", "Passionné", "Apathique", "Enthousiaste", "Jaloux"
    ]
}


class TraitsExtractor:
    """Service pour extraire les traits de caractère à partir de descriptions textuelles."""

    def __init__(self, model_name: str = "distilbert-base-uncased"):
        """
        Initialise l'extracteur de traits avec un modèle spécifique.

        Args:
            model_name: Nom du modèle Hugging Face à utiliser pour l'extraction
        """
        self.model_name = model_name
        logger.info(f"Initialisation de TraitsExtractor avec le modèle : {model_name}")
        
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModelForSequenceClassification.from_pretrained(model_name)
            
            # Pour la démonstration, nous utilisons un pipeline de classification de texte
            # Dans une application réelle, vous utiliseriez un modèle plus spécifique ou affiné
            self.classifier = pipeline(
                "zero-shot-classification", 
                model=self.model_name,
                tokenizer=self.tokenizer
            )
            logger.info(f"Modèle chargé avec succès : {model_name}")
        except Exception as e:
            logger.error(f"Échec du chargement du modèle {model_name} : {str(e)}")
            raise

    def extract_traits(self, text: str, directive: Optional[str] = None) -> List[CharacterTrait]:
        """
        Extrait les traits de caractère à partir de la description textuelle fournie.

        Args:
            text: Texte de description du personnage

        Returns:
            Liste d'objets CharacterTrait avec noms de traits et scores de confiance
        """
        logger.info(f"Extraction des traits à partir d'un texte de longueur : {len(text)}")
        
        if directive:
            logger.info(f"Directive fournie pour l'extraction : {directive}")
            # Dans une implémentation réelle, nous utiliserions la directive pour guider le modèle
            # Par exemple, en l'ajoutant au contexte ou en ajustant les paramètres du modèle
        
        all_traits = []
        for category, traits in TRAIT_CATEGORIES.items():
            try:
                # Utiliser la classification zero-shot pour identifier les traits dans cette catégorie
                result = self.classifier(text, traits, multi_label=True)
                
                # Traiter les résultats
                for trait, score in zip(result["labels"], result["scores"]):
                    # Inclure uniquement les traits avec des scores au-dessus du seuil
                    if score > 0.3:  
                        all_traits.append(CharacterTrait(
                            trait=trait,
                            score=score,
                            category=category
                        ))
            except Exception as e:
                logger.error(f"Erreur lors de l'extraction des traits pour la catégorie {category} : {str(e)}")
        
        # Trier par score (du plus élevé au plus bas)
        all_traits.sort(key=lambda x: x.score, reverse=True)
        logger.info(f"Extraction de {len(all_traits)} traits avec des scores au-dessus du seuil")
        
        return all_traits
    
    def generate_summary(self, traits: List[CharacterTrait]) -> str:
        """
        Génère un résumé du personnage basé sur les traits extraits.

        Args:
            traits: Liste d'objets CharacterTrait

        Returns:
            Résumé textuel des principaux traits du personnage
        """
        if not traits:
            return "Aucun trait de caractère significatif n'a été identifié."
            
        # Prendre les 5 premiers traits ou tous s'il y en a moins
        top_traits = traits[:min(5, len(traits))]
        
        # Créer le résumé
        trait_phrases = [f"{t.trait} ({t.category})" for t in top_traits]
        traits_text = ", ".join(trait_phrases[:-1])
        if len(trait_phrases) > 1:
            traits_text += f" and {trait_phrases[-1]}"
        else:
            traits_text = trait_phrases[0]
            
        summary = f"Ce personnage est principalement caractérisé par {traits_text}."
        return summary