from fastapi.responses import FileResponse
import requests
import xml.etree.ElementTree as ET
import ezdxf
import os

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

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/xml,text/xml;q=0.9,*/*;q=0.8"
    }

    url_direccion = "https://ovc.catastro.meh.es/ovcservweb/OVCSWLocalizacionRC/OVCCallejero.asmx/Consulta_DNPLOC"

    params_direccion = {
        "Provincia": provincia.upper(),
        "Municipio": municipio.upper(),
        "Sigla": tipo_via.upper(),
        "Calle": nombre_via.upper(),
        "Numero": numero,
        "Bloque": "",
        "Escalera": "",
        "Planta": "",
        "Puerta": ""
    }

    respuesta = requests.get(
        url_direccion,
        params=params_direccion,
        headers=headers,
        timeout=30
    )

    if respuesta.status_code != 200:
        return {
            "error": "Error consultando Catastro",
            "status_code": respuesta.status_code,
            "respuesta": respuesta.text[:500]
        }

    try:
        root = ET.fromstring(respuesta.content)
    except ET.ParseError:
        return {
            "error": "Catastro no ha devuelto XML válido",
            "respuesta": respuesta.text[:1000]
        }

    ns = {"cat": "http://www.catastro.meh.es/"}

    pc1 = root.find(".//cat:pc1", ns)
    pc2 = root.find(".//cat:pc2", ns)
    direccion = root.find(".//cat:ldt", ns)
    uso = root.find(".//cat:luso", ns)

    if pc1 is None or pc2 is None:
        return {
            "error": "Referencia catastral no encontrada",
            "respuesta_catastro": respuesta.text[:1000]
        }

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

    respuesta_parcela = requests.get(
        url_parcela,
        params=params_parcela,
        headers=headers,
        timeout=30
    )

    if respuesta_parcela.status_code != 200:
        return {
            "error": "Error consultando geometría INSPIRE",
            "status_code": respuesta_parcela.status_code,
            "respuesta": respuesta_parcela.text[:500]
        }

    try:
        root_parcela = ET.fromstring(respuesta_parcela.content)
    except ET.ParseError:
        return {
            "error": "INSPIRE no ha devuelto XML válido",
            "respuesta": respuesta_parcela.text[:1000]
        }

    coords_text = None
    area = None

    for elem in root_parcela.iter():
        if elem.tag.endswith("posList"):
            coords_text = elem.text

        if elem.tag.endswith("areaValue"):
            area = elem.text

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

    if "PARCELA_CATASTRAL" not in doc.layers:
        doc.layers.add("PARCELA_CATASTRAL")

    msp.add_lwpolyline(
        puntos,
        close=True,
        dxfattribs={"layer": "PARCELA_CATASTRAL"}
    )

    nombre_archivo = os.path.join("/tmp", f"parcela_{refcat}.dxf")

    doc.saveas(nombre_archivo)

    return FileResponse(
        nombre_archivo,
        media_type="application/dxf",
        filename=f"parcela_{refcat}.dxf"
    )