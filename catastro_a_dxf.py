import requests
import xml.etree.ElementTree as ET
import ezdxf

print("CATASTRO A DXF - OFV")
print("--------------------")

provincia = input("Provincia: ").strip()
municipio = input("Municipio: ").strip()
tipo_via = input("Tipo vía (CL, AV, PL...): ").strip()
nombre_via = input("Nombre vía: ").strip()
numero = input("Número: ").strip()

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
direccion = root.find(".//cat:ldt", ns)
uso = root.find(".//cat:luso", ns)

if pc1 is None or pc2 is None:
    print("No se ha encontrado referencia catastral.")
    exit()

refcat = pc1.text + pc2.text

print("\nRESULTADOS CATASTRO")
print("--------------------")
print("Referencia catastral:", refcat)

if direccion is not None:
    print("Dirección:", direccion.text)

if uso is not None:
    print("Uso:", uso.text)

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
area = None

for elem in root_parcela.iter():
    if elem.tag.endswith("posList"):
        coords_text = elem.text
    if elem.tag.endswith("areaValue"):
        area = elem.text

if coords_text is None:
    print("No se ha encontrado geometría de parcela.")
    exit()

valores = coords_text.split()
puntos = []

for i in range(0, len(valores), 2):
    x = float(valores[i])
    y = float(valores[i + 1])
    puntos.append((x, y))

doc = ezdxf.new("R2010")
msp = doc.modelspace()

doc.layers.add("PARCELA_CATASTRAL")
doc.layers.add("TEXTO")

msp.add_lwpolyline(
    puntos,
    close=True,
    dxfattribs={"layer": "PARCELA_CATASTRAL"}
)

texto = f"Ref. catastral: {refcat}"

if area is not None:
    texto += f" | Sup. parcela: {area} m2"
    print("Superficie parcela:", area, "m²")

msp.add_text(
    texto,
    dxfattribs={"height": 1.5, "layer": "TEXTO"}
).set_placement(puntos[0])

nombre_archivo = f"parcela_{refcat}.dxf"
doc.saveas(nombre_archivo)

print("\nDXF generado correctamente:")
print(nombre_archivo)