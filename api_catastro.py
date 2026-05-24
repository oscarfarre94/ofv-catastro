from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
import requests
import xml.etree.ElementTree as ET
import ezdxf
import os

app = FastAPI()

BASE_URL = "https://ofv-catastro.onrender.com"


@app.get("/")
def inicio():
    return {"mensaje": "API Catastro OFV funcionando"}


def obtener_referencia(provincia, municipio, tipo_via, nombre_via, numero):
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/xml,text/xml;q=0.9,*/*;q=0.8"
    }

    url = "https://ovc.catastro.meh.es/ovcservweb/OVCSWLocalizacionRC/OVCCallejero.asmx/Consulta_DNPLOC"

    params = {
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

    respuesta = requests.get(url, params=params, headers=headers, timeout=30)

    if respuesta.status_code != 200:
        return None

    try:
        root = ET.fromstring(respuesta.content)
    except ET.ParseError:
        return None

    ns = {"cat": "http://www.catastro.meh.es/"}

    pc1 = root.find(".//cat:pc1", ns)
    pc2 = root.find(".//cat:pc2", ns)

    if pc1 is None or pc2 is None:
        return None

    return pc1.text + pc2.text


def limpiar_refcat(refcat):
    refcat = refcat.strip().upper().replace(" ", "").replace("-", "")
    if len(refcat) >= 14:
        return refcat[:14]
    return refcat


def crear_dxf(refcat):
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/xml,text/xml;q=0.9,*/*;q=0.8"
    }

    refcat = limpiar_refcat(refcat)

    url_parcela = "https://ovc.catastro.meh.es/INSPIRE/wfsCP.aspx"

    params_parcela = {
        "service": "WFS",
        "version": "2.0.0",
        "request": "GetFeature",
        "STOREDQUERY_ID": "GetParcel",
        "refcat": refcat,
        "srsname": "EPSG::25831"
    }

    respuesta = requests.get(url_parcela, params=params_parcela, headers=headers, timeout=30)

    if respuesta.status_code != 200:
        return None, None

    try:
        root = ET.fromstring(respuesta.content)
    except ET.ParseError:
        return None, None

    coords_text = None
    area = None

    for elem in root.iter():
        if elem.tag.endswith("posList"):
            coords_text = elem.text
        if elem.tag.endswith("areaValue"):
            area = elem.text

    if coords_text is None:
        return None, None

    valores = coords_text.split()
    puntos = []

    for i in range(0, len(valores), 2):
        puntos.append((float(valores[i]), float(valores[i + 1])))

    nombre_archivo = f"parcela_{refcat}.dxf"
    ruta_archivo = os.path.join("/tmp", nombre_archivo)

    doc = ezdxf.new("R2010")
    msp = doc.modelspace()

    if "PARCELA_CATASTRAL" not in doc.layers:
        doc.layers.add("PARCELA_CATASTRAL")

    msp.add_lwpolyline(
        puntos,
        close=True,
        dxfattribs={"layer": "PARCELA_CATASTRAL"}
    )

    doc.saveas(ruta_archivo)

    return ruta_archivo, area


@app.get("/generar-dxf")
def generar_dxf(
    provincia: str = None,
    municipio: str = None,
    tipo_via: str = None,
    nombre_via: str = None,
    numero: str = None,
    refcat: str = None
):
    if refcat:
        referencia = limpiar_refcat(refcat)
    else:
        if not all([provincia, municipio, tipo_via, nombre_via, numero]):
            return JSONResponse(
                status_code=400,
                content={
                    "error": "Debes indicar refcat o bien provincia, municipio, tipo_via, nombre_via y numero"
                }
            )

        referencia = obtener_referencia(
            provincia,
            municipio,
            tipo_via,
            nombre_via,
            numero
        )

    if referencia is None:
        return JSONResponse(
            status_code=404,
            content={"error": "Referencia catastral no encontrada"}
        )

    ruta_archivo, area = crear_dxf(referencia)

    if ruta_archivo is None:
        return JSONResponse(
            status_code=500,
            content={"error": "No se pudo generar el DXF"}
        )

    return FileResponse(
        path=ruta_archivo,
        media_type="application/octet-stream",
        filename=f"parcela_{referencia}.dxf"
    )


@app.get("/generar-dxf-info")
def generar_dxf_info(
    provincia: str = None,
    municipio: str = None,
    tipo_via: str = None,
    nombre_via: str = None,
    numero: str = None,
    refcat: str = None
):
    if refcat:
        referencia = limpiar_refcat(refcat)
    else:
        if not all([provincia, municipio, tipo_via, nombre_via, numero]):
            return JSONResponse(
                status_code=400,
                content={
                    "error": "Debes indicar refcat o bien provincia, municipio, tipo_via, nombre_via y numero"
                }
            )

        referencia = obtener_referencia(
            provincia,
            municipio,
            tipo_via,
            nombre_via,
            numero
        )

    if referencia is None:
        return JSONResponse(
            status_code=404,
            content={"error": "Referencia catastral no encontrada"}
        )

    ruta_archivo, area = crear_dxf(referencia)

    if ruta_archivo is None:
        return JSONResponse(
            status_code=500,
            content={"error": "No se pudo generar el DXF"}
        )

    return {
        "referencia_catastral": referencia,
        "superficie_parcela_m2": area,
        "download_url": f"{BASE_URL}/descargar-dxf/{referencia}"
    }


@app.get("/descargar-dxf/{refcat}")
def descargar_dxf(refcat: str):
    referencia = limpiar_refcat(refcat)

    ruta_archivo, area = crear_dxf(referencia)

    if ruta_archivo is None:
        return JSONResponse(
            status_code=500,
            content={"error": "No se pudo generar el DXF"}
        )

    return FileResponse(
        path=ruta_archivo,
        media_type="application/octet-stream",
        filename=f"parcela_{referencia}.dxf"
    )