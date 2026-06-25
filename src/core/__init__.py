"""core — dominio puro: entidades, reglas de negocio y puertos.

NO importar Qt ni sqlite3 aquí. El acceso a datos se define como puertos (interfaces)
`RepositorioX`; los adaptadores concretos viven en los módulos de cada capa.
"""
