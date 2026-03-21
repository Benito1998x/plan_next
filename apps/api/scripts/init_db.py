# -*- coding: utf-8 -*-
"""
Script para inicializar la base de datos y poblarla con datos por defecto.

Sprint 1: incluye tablas nuevas DatosNegocio, BuyerPersona, ConfiguracionMetodologica
y seed completo de datos globales bolivianos.
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlmodel import Session, text
from database import get_database
from models.db import (
    Moneda,
    Impuesto,
    Ciudad,
    TipoCambio,
    IndicadorEconomico,
    DatosNegocio,
    BuyerPersona,
    ConfiguracionMetodologica,
)


def seed_monedas(session: Session) -> None:
    """Poblar tabla de monedas."""
    monedas = [
        Moneda(codigo="BS", nombre="Boliviano", simbolo="Bs", es_default=True),
        Moneda(
            codigo="USD", nombre="Dólar Estadounidense", simbolo="$", es_default=False
        ),
    ]
    session.add_all(monedas)
    print(f"[OK] Insertadas {len(monedas)} monedas")


def seed_impuestos(session: Session) -> None:
    """Poblar tabla de impuestos bolivianos."""
    impuestos = [
        Impuesto(
            codigo="IUE",
            nombre="Impuesto a las Utilidades de las Empresas",
            porcentaje=25.0,
            descripcion="Impuesto sobre las ganancias empresariales",
        ),
        Impuesto(
            codigo="IT",
            nombre="Impuesto a las Transacciones",
            porcentaje=3.0,
            descripcion="Impuesto sobre transacciones comerciales",
        ),
        Impuesto(
            codigo="IVA",
            nombre="Impuesto al Valor Agregado",
            porcentaje=13.0,
            descripcion="Impuesto al valor agregado en ventas",
        ),
    ]
    session.add_all(impuestos)
    print(f"[OK] Insertados {len(impuestos)} impuestos")


def seed_ciudades(session: Session) -> None:
    """Poblar tabla de ciudades (9 capitales departamentales de Bolivia)."""
    ciudades = [
        Ciudad(nombre="Santa Cruz de la Sierra", departamento="Santa Cruz", pais="Bolivia"),
        Ciudad(nombre="La Paz", departamento="La Paz", pais="Bolivia"),
        Ciudad(nombre="Cochabamba", departamento="Cochabamba", pais="Bolivia"),
        Ciudad(nombre="Sucre", departamento="Chuquisaca", pais="Bolivia"),
        Ciudad(nombre="Oruro", departamento="Oruro", pais="Bolivia"),
        Ciudad(nombre="Potosí", departamento="Potosí", pais="Bolivia"),
        Ciudad(nombre="Tarija", departamento="Tarija", pais="Bolivia"),
        Ciudad(nombre="Trinidad", departamento="Beni", pais="Bolivia"),
        Ciudad(nombre="Cobija", departamento="Pando", pais="Bolivia"),
    ]
    session.add_all(ciudades)
    print(f"[OK] Insertadas {len(ciudades)} ciudades")


def seed_indicadores(session: Session) -> None:
    """Poblar tabla de indicadores económicos (fuente: BCB 2025)."""
    indicadores = [
        IndicadorEconomico(
            pais="Bolivia",
            nombre="Inflación Anual",
            valor=3.5,
            unidad="%",
            anio=2025,
        ),
        IndicadorEconomico(
            pais="Bolivia",
            nombre="Tipo de Cambio USD",
            valor=6.96,
            unidad="Bs/USD",
            anio=2025,
        ),
        IndicadorEconomico(
            pais="Bolivia",
            nombre="Tasa de Interés Promedio",
            valor=8.5,
            unidad="%",
            anio=2025,
        ),
    ]
    session.add_all(indicadores)
    print(f"[OK] Insertados {len(indicadores)} indicadores economicos")


def seed_tipo_cambio(session: Session) -> None:
    """Poblar tabla de tipo de cambio."""
    # Primero obtener los IDs de las monedas
    boliviano = session.exec(text("SELECT id FROM moneda WHERE codigo = 'BS'")).first()
    dolar = session.exec(text("SELECT id FROM moneda WHERE codigo = 'USD'")).first()

    if boliviano and dolar:
        tipo_cambio = TipoCambio(
            moneda_origen_id=dolar[0],
            moneda_destino_id=boliviano[0],
            valor=6.96,
            fuente="manual",
        )
        session.add(tipo_cambio)
        print("[OK] Insertado tipo de cambio USD -> Bs")


def init_database() -> None:
    """Inicializar base de datos con datos por defecto."""
    print("=" * 50)
    print("Inicializando base de datos...")
    print("=" * 50)

    # Crear instancia de base de datos
    db = get_database()

    # Crear tablas
    print("\n1. Creando tablas...")
    db.create_tables()
    print("[OK] Tablas creadas")

    # Poblar con datos por defecto
    print("\n2. Poblando datos por defecto...")
    with db.get_session() as session:
        # Verificar si ya hay datos
        existing = session.exec(text("SELECT COUNT(*) FROM moneda")).first()
        if existing and existing[0] > 0:
            print("[WARN] La base de datos ya contiene datos. Saltando seed.")
            return

        seed_monedas(session)
        seed_impuestos(session)
        seed_ciudades(session)
        seed_indicadores(session)
        seed_tipo_cambio(session)
        session.commit()
        print("\n[OK] Datos insertados correctamente")

    print("\n" + "=" * 50)
    print("Base de datos inicializada!")
    print("=" * 50)


if __name__ == "__main__":
    init_database()
