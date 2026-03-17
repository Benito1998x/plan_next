"""
Config Service - Carga y provee configuración desde YAML
"""

import yaml
from pathlib import Path
from typing import Dict, Any, Optional


class ConfigService:
    """
    Servicio para cargar y acceder a la configuración de la aplicación.

    Lee los valores por defecto desde config/defaults.yaml y los pone
    disponibles para otros servicios.

    Usage:
        config = ConfigService()
        moneda = config.get("moneda.codigo")  # "Bs"
        impuestos = config.get("impuestos.iue.porcentaje")  # 25.0
    """

    def __init__(self, config_path: Optional[Path] = None):
        """
        Inicializa el servicio de configuración.

        Args:
            config_path: Ruta al archivo YAML. Si es None, usa el default.
        """
        if config_path is None:
            # Calcula la ruta relativa a este archivo
            current_dir = Path(__file__).parent.parent
            self.config_path = current_dir / "config" / "defaults.yaml"
        else:
            self.config_path = config_path

        self._config: Optional[Dict[str, Any]] = None

    def load(self) -> Dict[str, Any]:
        """
        Carga la configuración desde el archivo YAML.

        Returns:
            Dict con toda la configuración

        Raises:
            FileNotFoundError: Si no existe el archivo
            yaml.YAMLError: Si el YAML tiene error de sintaxis
        """
        if self._config is None:
            if not self.config_path.exists():
                raise FileNotFoundError(
                    f"Archivo de configuración no encontrado: {self.config_path}"
                )

            with open(self.config_path, "r", encoding="utf-8") as f:
                self._config = yaml.safe_load(f)

            # Asegurar que nunca retornamos None
            if self._config is None:
                self._config = {}

        return self._config

    def get(self, key: str, default: Any = None) -> Any:
        """
        Obtiene un valor de configuración usando notación de puntos.

        Args:
            key: Clave en notación de puntos (ej: "moneda.codigo")
            default: Valor por defecto si la clave no existe

        Returns:
            El valor de configuración o el default

        Example:
            >>> config.get("pais.nombre")
            "Bolivia"
            >>> config.get("impuestos.iue.porcentaje")
            25.0
        """
        if self._config is None:
            self.load()

        keys = key.split(".")
        value = self._config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def get_all(self) -> Dict[str, Any]:
        """
        Retorna toda la configuración como diccionario.

        Returns:
            Dict completo con la configuración
        """
        config = self.load()
        return config.copy()

    def reload(self) -> None:
        """
        Recarga la configuración desde el archivo.
        Útil si el archivo cambia en runtime.
        """
        self._config = None
        self.load()


# Singleton instance para uso global
_config_service: Optional[ConfigService] = None


def get_config_service() -> ConfigService:
    """
    Factory function que retorna una instancia singleton de ConfigService.

    Esto asegura que todos los servicios usen la misma configuración
    sin necesidad de recargar el archivo múltiples veces.

    Returns:
        ConfigService instance
    """
    global _config_service
    if _config_service is None:
        _config_service = ConfigService()
    return _config_service
