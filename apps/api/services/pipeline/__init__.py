"""
Pipeline de Ingeniería de Datos — Bronze → Silver → Gold

Bronze : datos brutos del Excel de encuesta, almacenados en SQLite sin transformar
Silver : limpieza con pandas (eliminar prefijos "a) ", normalizar texto)
Gold   : groupby → tablas de frecuencia absolutas y relativas listas para el reporte

Cada capa es independiente y testeable por separado.
"""
