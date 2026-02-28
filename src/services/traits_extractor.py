"""Service d'extraction de traits utilisant l'API d'Inference Hugging Face.

Ce module interroge des modèles de type Instruct (comme Mistral) via l'API Serverless 
de Hugging Face pour une analyse sémantique précise et multilingue.
"""

import logging
import os
import json
import re
from typing import List, Optional

from huggingface_hub import InferenceClient
from src.models.character_traits import CharacterTrait

# Configuration du logging
logger = logging.getLogger(__name__)


class TraitsExtractor:
    """Service pour extraire les traits de caractère via LLM."""

    def __init__(self, model_name: Optional[str] = None):
        """
        Initialise l'extracteur de traits.

        Args:
            model_name: Nom du modèle Hugging Face (optionnel, sinon utilise HF_MODEL_NAME)
        """
        self.token = os.environ.get("HF_TOKEN")
        self.model_name = model_name or os.environ.get("HF_MODEL_NAME", "mistralai/Mistral-7B-Instruct-v0.3")
        
        if not self.token:
            logger.warning("HF_TOKEN non défini. L'extraction risque d'échouer sur l'API Serverless.")
        
        logger.info(f"Initialisation de TraitsExtractor avec le modèle : {self.model_name}")
        self.client = InferenceClient(model=self.model_name, token=self.token)

    def extract_traits(self, text: str, directive: Optional[str] = None) -> tuple[List[CharacterTrait], bool]:
        """
        Extrait les traits de caractère en interrogeant le LLM via un prompt structuré.

        Args:
            text: Texte de description du personnage
            directive: Instructions supplémentaires

        Returns:
            Tuple: Liste d'objets CharacterTrait, et un booléen (validated_model)
        """
        logger.info(f"Extraction des traits (LLM) pour un texte de {len(text)} caractères")
        
        # Préparation du prompt système pour forcer le JSON
        system_prompt = (
            "Tu es un expert en analyse littéraire et psychologique de personnages. "
            "Ta tâche est d'extraire les traits de caractère (personnalité, valeurs, émotions) du texte fourni. "
            "Ignore les descriptions purement physiques. "
            "Réponds UNIQUEMENT par un objet JSON au format suivant :\n"
            '{"traits": [{"trait": "Nom du trait", "score": 0.95, "category": "Personnalité"}]}'
        )
        
        user_content = f"Description : {text}"
        if directive:
            user_content += f"\nDirective spécifique : {directive}"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]

        try:
            response = self.client.chat_completion(
                messages=messages,
                max_tokens=500,
                temperature=0.1  # Basse pour la répétabilité et la précision
            )
            
            raw_result = response.choices[0].message.content
            logger.debug(f"Réponse brute du modèle : {raw_result}")
            
            
            return self._parse_llm_response(raw_result), True
            
        except Exception as e:
            error_msg = str(e).lower()
            logger.error(f"Erreur lors de l'appel à l'API Hugging Face : {str(e)}")
            
            # Vérifier si c'est une erreur de type modèle non supporté
            if "model_not_supported" in error_msg or "not found" in error_msg:
                # Fallback propre indiquant que le modèle est invalide
                return [], False
                
            # Autre erreur, on retourne vide mais avec modèle potentiellement valide (timeout, surcharge...)
            return [], True

    def _parse_llm_response(self, content: str) -> List[CharacterTrait]:
        """Tente de parser la réponse JSON du modèle."""
        try:
            # Nettoyage minimal pour extraire le JSON si le modèle a ajouté du texte
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                content = json_match.group(0)
                
            data = json.loads(content)
            traits_data = data.get("traits", [])
            
            results = []
            for t in traits_data:
                results.append(CharacterTrait(
                    trait=t.get("trait", "Inconnu"),
                    score=float(t.get("score", 0.5)),
                    category=t.get("category", "Général")
                ))
            
            # Trier par score décroissant
            results.sort(key=lambda x: x.score, reverse=True)
            return results
            
        except Exception as e:
            logger.error(f"Erreur de parsing JSON du résultat LLM : {str(e)}")
            return []

    def generate_summary(self, traits: List[CharacterTrait]) -> str:
        """Génère un résumé textuel basé sur les traits."""
        if not traits:
            return "Aucun trait significatif identifié."
            
        top_traits = traits[:5]
        traits_str = ", ".join([f"{t.trait} ({t.category})" for t in top_traits])
        return f"Basé sur l'analyse, ce personnage se distingue par : {traits_str}."