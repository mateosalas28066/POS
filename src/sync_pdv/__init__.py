"""sync_pdv — patrón outbox para multi-local (diseñado, no implementado a fondo).

Cola `outbox_eventos` + procesos export/import hacia un servidor central, equivalente a la
transmisión/recepción PDV almacén de Siesa. Se implementa cuando exista un segundo local.
"""
