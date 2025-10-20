
# TODO: https://avoin.metsakeskus.fi/aineistot/Metsavarakuviot/Karttalehti/

SCHEMA = """
CREATE TABLE terrain
(
    name TEXT,
    x_etrs DOUBLE,
    y_etrs DOUBLE,
    lon DOUBLE,
    lat DOUBLE,
    elevation DOUBLE,
    tpi_10m DOUBLE,
    tpi_20m DOUBLE,
    tpi_30m DOUBLE,
    slope DOUBLE,
    aspect DOUBLE
)
"""
