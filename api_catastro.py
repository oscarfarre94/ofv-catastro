from fastapi import FastAPI
import requests
import xml.etree.ElementTree as ET
import ezdxf

app = FastAPI()

@app.get("/")
def inicio():
    return {"mensaje": "API OFV funcionando"}

@app.get("/generar-dxf")
def generar_dxf(
    provincia: str,
    municipio: str,
    tipo_via: str,
    nombre_via: str,
    numero: str
):

    url_direccion = "https://ovc.catastro.meh.es/ovcservweb/OVCSWLocalizacionRC/OVCCallejero.asmx/Consulta_DNPLOC"

    params_direccion = {
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

    respuesta = requests.get(url_direccion, params=params_direccion)

    root = ET.fromstring(respuesta.content)

    ns = {"cat": "http://www.catastro.meh.es/"}

    pc1 = root.find(".//cat:pc1", ns)
    pc2 = root.find(".//cat:pc2", ns)

    if pc1 is None or pc2 is None:
        return {"error": "Referencia catastral no encontrada"}

    refcat = pc1.text + pc2.text

    url_parcela = "https://ovc.catastro.meh.es/INSPIRE/wfsCP.aspx"

    params_parcela = {
        "service": "WFS",
        "version": "2.0.0",
        "request": "GetFeature",
        "STOREDQUERY_ID": "GetParcel",
        "refcat": refcat,
        "srsname": "EPSG::25831"
    }

    respuesta_parcela = requests.get(url_parcela, params=params_parcela)

    root_parcela = ET.fromstring(respuesta_parcela.content)

    coords_text = None

    for elem in root_parcela.iter():
        if elem.tag.endswith("posList"):
            coords_text = elem.text
            break

    if coords_text is None:
        return {"error": "Geometría no encontrada"}

    valores = coords_text.split()

    puntos = []

    for i in range(0, len(valores), 2):
        x = float(valores[i])
        y = float(valores[i + 1])
        puntos.append((x, y))

    doc = ezdxf.new("R2010")

    msp = doc.modelspace()

    doc.layers.add("PARCELA_CATASTRAL")

    msp.add_lwpolyline(
        puntos,
        close=True,
        dxfattribs={"layer": "PARCELA_CATASTRAL"}
    )

    nombre_archivo = f"parcela_{refcat}.dxf"

    doc.saveas(nombre_archivo)

    return {
        "referencia_catastral": refcat,
        "archivo_dxf": nombre_archivo
    }