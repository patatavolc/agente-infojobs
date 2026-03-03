PROVINCIAS_INFOJOBS = {
    "alava": "1", "albacete": "2", "alicante": "3", "almeria": "4", "asturias": "5",
    "avila": "6", "badajoz": "7", "barcelona": "8", "burgos": "9", "caceres": "10",
    "cadiz": "11", "castellon": "12", "ciudad real": "13", "cordoba": "14", "coruña": "15",
    "cuenca": "16", "girona": "17", "granada": "18", "guadalajara": "19", "guipuzcoa": "20",
    "huelva": "21", "huesca": "22", "illes balears": "23", "jaen": "24", "leon": "25",
    "lleida": "26", "la rioja": "27", "lugo": "28", "madrid": "33", "malaga": "29",
    "murcia": "30", "navarra": "31", "ourense": "32", "palencia": "34", "las palmas": "35",
    "pontevedra": "36", "salamanca": "37", "santa cruz de tenerife": "38", "cantabria": "39",
    "segovia": "40", "sevilla": "41", "soria": "42", "tarragona": "43", "teruel": "44",
    "toledo": "45", "valencia": "46", "valladolid": "47", "vizcaya": "48", "zamora": "49",
    "zaragoza": "50", "ceuta": "51", "melilla": "52"
}

def normalizar_texto(texto: str) -> str:
    """Elimina tildes y convierte a minusculas para facilitar el mapeo"""
    import unicodedata
    if not texto:
        return ""
    # Normalizar para eliminar acentos
    texto = "".join(
        c for c in unicodedata.normalize('NFD', texto)
        if unicodedata.category(c) != 'Mn'
    )
    return texto.lower().strip()