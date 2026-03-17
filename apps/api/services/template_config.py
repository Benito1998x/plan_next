"""
Template Configuration - Carga configuración de plantillas desde YAML.

Soporta múltiples versiones de plantilla y mapeo dinámico de celdas.
"""

from pathlib import Path
from typing import Dict, Any, List, Optional
import yaml


class TemplateConfig:
    """
    Carga y gestiona configuración de plantillas Excel.

    Permite:
    - Cargar configuración desde YAML
    - Obtener configuración por versión
    - Obtener secciones específicas
    - Obtener campos requeridos
    - Validar estructura

    Usage:
        config = TemplateConfig("config/excel_templates.yaml")
        v1_params = config.get_section("v1", "parametros_globales")
    """

    def __init__(self, config_path: Optional[Path] = None):
        """
        Inicializa la configuración de plantillas.

        Args:
            config_path: Ruta al archivo YAML. Si es None, usa el default.
        """
        if config_path is None:
            # Ruta por defecto
            current_dir = Path(__file__).parent.parent
            config_path = current_dir / "config" / "excel_templates.yaml"

        self.config_path = Path(config_path)
        self._config: Optional[Dict[str, Any]] = None
        self._types: Dict[str, Any] = {}

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

            # Cargar tipos
            self._types = self._config.get("types", {})

        return self._config

    def get_template(self, version: str = "v1") -> Dict[str, Any]:
        """
        Obtiene la configuración de una versión de plantilla.

        Args:
            version: Versión de la plantilla (ej: "v1", "v2")

        Returns:
            Dict con la configuración de la plantilla

        Raises:
            KeyError: Si la versión no existe
        """
        if self._config is None:
            self.load()

        templates = self._config.get("templates", {})

        if version not in templates:
            available = list(templates.keys())
            raise KeyError(
                f"Versión '{version}' no encontrada. Disponibles: {available}"
            )

        return templates[version]

    def get_section(self, version: str, section: str) -> Dict[str, Any]:
        """
        Obtiene la configuración de una sección específica.

        Args:
            version: Versión de la plantilla
            section: Nombre de la sección (ej: "parametros_globales")

        Returns:
            Dict con la configuración de la sección

        Raises:
            KeyError: Si la sección no existe
        """
        template = self.get_template(version)
        sections = template.get("sections", {})

        if section not in sections:
            available = list(sections.keys())
            raise KeyError(
                f"Sección '{section}' no encontrada en versión '{version}'. "
                f"Disponibles: {available}"
            )

        return sections[section]

    def get_required_fields(self, version: str, section: str) -> List[str]:
        """
        Obtiene los campos requeridos de una sección.

        Args:
            version: Versión de la plantilla
            section: Nombre de la sección

        Returns:
            Lista de nombres de campos requeridos
        """
        section_config = self.get_section(version, section)

        # Formato nuevo: fields con required: true
        if "fields" in section_config:
            fields = section_config["fields"]
            return [
                f["name"]
                for f in fields
                if isinstance(f, dict) and f.get("required", False)
            ]

        # Formato antiguo: lista de required
        return section_config.get("required", [])

    def get_field_config(
        self, version: str, section: str, field_name: str
    ) -> Dict[str, Any]:
        """
        Obtiene la configuración de un campo específico.

        Args:
            version: Versión de la plantilla
            section: Nombre de la sección
            field_name: Nombre del campo

        Returns:
            Dict con la configuración del campo
        """
        section_config = self.get_section(version, section)

        # Formato con fields
        if "fields" in section_config:
            for field in section_config["fields"]:
                if isinstance(field, dict) and field.get("name") == field_name:
                    return field

        # Formato con columns
        if "columns" in section_config:
            return section_config["columns"].get(field_name, {})

        return {}

    def get_all_fields(self, version: str, section: str) -> List[Dict[str, Any]]:
        """
        Obtiene todos los campos de una sección.

        Args:
            version: Versión de la plantilla
            section: Nombre de la sección

        Returns:
            Lista de configuraciones de campos
        """
        section_config = self.get_section(version, section)

        # Formato con fields (key-value)
        if "fields" in section_config:
            return section_config["fields"]

        # Formato con columns (table)
        if "columns" in section_config:
            columns = section_config["columns"]
            return [{"name": name, **config} for name, config in columns.items()]

        return []

    def get_type_config(self, type_name: str) -> Dict[str, Any]:
        """
        Obtiene la configuración de un tipo de dato.

        Args:
            type_name: Nombre del tipo (ej: "percentage", "year")

        Returns:
            Dict con la configuración del tipo
        """
        if self._config is None:
            self.load()

        return self._types.get(type_name, {})

    def get_default_value(self, version: str, section: str, field_name: str) -> Any:
        """
        Obtiene el valor por defecto de un campo.

        Args:
            version: Versión de la plantilla
            section: Nombre de la sección
            field_name: Nombre del campo

        Returns:
            Valor por defecto del campo, o None
        """
        field_config = self.get_field_config(version, section, field_name)

        if "default" in field_config:
            return field_config["default"]

        # Obtener default del tipo
        type_name = field_config.get("type", "string")
        type_config = self.get_type_config(type_name)

        return type_config.get("default")

    def get_available_versions(self) -> List[str]:
        """
        Obtiene todas las versiones disponibles.

        Returns:
            Lista de nombres de versiones
        """
        if self._config is None:
            self.load()

        return list(self._config.get("templates", {}).keys())

    def get_available_sections(self, version: str) -> List[str]:
        """
        Obtiene todas las secciones de una versión.

        Args:
            version: Versión de la plantilla

        Returns:
            Lista de nombres de secciones
        """
        template = self.get_template(version)
        return list(template.get("sections", {}).keys())


# Singleton instance
_template_config: Optional[TemplateConfig] = None


def get_template_config() -> TemplateConfig:
    """
    Factory function que retorna una instancia singleton de TemplateConfig.

    Returns:
        TemplateConfig instance
    """
    global _template_config
    if _template_config is None:
        _template_config = TemplateConfig()
    return _template_config
