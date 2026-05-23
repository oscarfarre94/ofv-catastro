import requests
import xml.etree.ElementTree as ET

print("BUSCADOR CATASTRO OFV")
print("----------------------")

provincia = input("Provincia: ")
municipio = input("Municipio: ")
tipo_via = input("Tipo vía (CL, AV, PL...): ")
nombre_via = input("Nombre vía: ")
numero = input("Número: ")

# =========================================================
# CONSULTA DIRECCIÓN -> REFERENCIA CATASTRAL
# =========================================================

url = "https://ovc.catastro.meh.es/ovcservweb/OVCSWLocalizacionRC/OVCCallejero.asmx/Consulta_DNPLOC"

params = {
    "Provincia": provincia,
    "Municipio": municipio,
    "Sigla": tipo_via,
    "Calle": nombre_via,
    "Numero": numero,
    "Bloque": "",
    "Escalera": "",
    "Planta": "",
    "Puerta": ""
}

respuesta = requests.get(url, params=params)

root = ET.fromstring(respuesta.content)

namespace = {'cat': 'http://www.catastro.meh.es/'}

pc1 = root.find('.//cat:pc1', namespace)
pc2 = root.find('.//cat:pc2', namespace)

direccion = root.find('.//cat:ldt', namespace)
uso = root.find('.//cat:luso', namespace)

print("\nRESULTADOS")
print("----------------------")

if pc1 is not None and pc2 is not None:

    referencia = pc1.text + pc2.text

    print("Referencia catastral:", referencia)

    if direccion is not None:
        print("Dirección:", direccion.text)

    if uso is not None:
        print("Uso:", uso.text)

    # =========================================================
    # CONSULTA SUPERFICIE PARCELA INSPIRE WFS
    # =========================================================

    url_parcela = "https://ovc.catastro.meh.es/INSPIRE/wfsCP.aspx"

    params_parcela = {
        "service": "WFS",
        "version": "2.0.0",
        "request": "GetFeature",
        "STOREDQUERY_ID": "GetParcel",
        "refcat": referencia,
        "srsname": "EPSG::25831"
    }

    respuesta_parcela = requests.get(url_parcela, params=params_parcela)

    root_parcela = ET.fromstring(respuesta_parcela.content)

    area = None

    for elem in root_parcela.iter():
        if elem.tag.endswith("areaValue"):
            area = elem
            break

    if area is not None:
        print("Superficie parcela:", area.text, "m²")
    else:
        print("Superficie parcela no encontrada")

else:
    print("Referencia catastral no encontrada")