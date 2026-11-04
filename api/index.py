from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Union
import requests
import re
from bs4 import BeautifulSoup

app = FastAPI(title="SIIAU Oferta Académica API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

URL_FORMA = "https://siiauescolar.siiau.udg.mx/wal/sspseca.forma_consulta"
URL_SIIAU = "https://siiauescolar.siiau.udg.mx/wal/sspseca.consulta_oferta"
DIAS_MAP = {0: "Lunes", 1: "Martes", 2: "Miércoles", 3: "Jueves", 4: "Viernes", 5: "Sábado"}

CACHE_FILTROS = {"ciclos": [], "centros": []}

FALLBACK_CENTROS = [
    {"val": "3", "text": "3 - C. U. DE TLAJOMULCO"},
    {"val": "4", "text": "4 - C. U. DE GUADALAJARA"},
    {"val": "5", "text": "5 - C.U. DE TLAQUEPAQUE"},
    {"val": "6", "text": "6 - C.U. DE CHAPALA"},
    {"val": "A", "text": "A - C.U. DE ARTE, ARQ. Y DISEÑO (CUAAD)"},
    {"val": "B", "text": "B - C.U. DE CS. BIOLOGICO Y AGR. (CUCBA)"},
    {"val": "C", "text": "C - C.U. DE CS. ECONOMICO-ADMVAS. (CUCEA)"},
    {"val": "D", "text": "D - C.U. DE CS. EXACTAS E ING. (CUCEI)"},
    {"val": "E", "text": "E - C.U. DE CS. DE LA SALUD (CUCS)"},
    {"val": "F", "text": "F - C.U. DE CS. SOCIALES Y HUM. (CUCSH)"},
    {"val": "G", "text": "G - C.U. DE LOS ALTOS"},
    {"val": "H", "text": "H - C.U. DE LA CIENEGA"},
    {"val": "I", "text": "I - C.U. DE LA COSTA"},
    {"val": "J", "text": "J - C.U. DE LA COSTA SUR"},
    {"val": "K", "text": "K - C.U. DEL SUR"},
    {"val": "M", "text": "M - C. U. DE LOS VALLES"},
    {"val": "N", "text": "N - C.U. DEL NORTE"},
    {"val": "O", "text": "O - CUCEI SEDE VALLES"},
    {"val": "P", "text": "P - CUCSUR SEDE VALLES"},
    {"val": "Q", "text": "Q - CUCEI SEDE NORTE"},
    {"val": "U", "text": "U - SISTEMA DE UNIVERSIDAD VIRTUAL (SUV)"}
]

FALLBACK_CICLOS = [
    {"val": "202710", "text": "202710 - Calendario 27 A"},
    {"val": "202680", "text": "202680 - Ciclo de Verano 2026"},
    {"val": "202620", "text": "202620 - Calendario 26 B"},
    {"val": "202610", "text": "202610 - Calendario 26 A"},
    {"val": "202580", "text": "202580 - Ciclo de Verano 2025"},
    {"val": "202520", "text": "202520 - Calendario 25 B"},
    {"val": "202510", "text": "202510 - Calendario 25 A"}
]

def cargar_opciones_siiau():
    if CACHE_FILTROS["ciclos"] and CACHE_FILTROS["centros"]:
        return CACHE_FILTROS

    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        res = requests.get(URL_FORMA, headers=headers, timeout=6)
        res.encoding = 'latin-1'
        soup = BeautifulSoup(res.text, 'html.parser')

        select_ciclo = soup.find('select', {'name': 'ciclop'})
        ciclos = []
        if select_ciclo:
            for opt in select_ciclo.find_all('option'):
                val = opt.get('value', '').strip()
                txt = opt.get_text(strip=True)
                if val:
                    ciclos.append({"val": val, "text": txt})

        select_cup = soup.find('select', {'name': 'cup'})
        centros = []
        if select_cup:
            for opt in select_cup.find_all('option'):
                val = opt.get('value', '').strip()
                txt = opt.get_text(strip=True)
                if val:
                    centros.append({"val": val, "text": txt})

        if ciclos and centros:
            CACHE_FILTROS["ciclos"] = ciclos
            CACHE_FILTROS["centros"] = centros
            return CACHE_FILTROS
    except Exception:
        pass

    return {"ciclos": FALLBACK_CICLOS, "centros": FALLBACK_CENTROS}

def parsear_dias(dias_raw: str) -> List[str]:
    dias_encontrados = []
    partes = [c for c in dias_raw.strip().split() if c]
    for idx, char in enumerate(partes):
        if char != '.' and idx in DIAS_MAP:
            dias_encontrados.append(DIAS_MAP[idx])
    return dias_encontrados

def extraer_oferta_siiau(ciclo: str, centro: str, materia: str):
    payload = {
        'ciclop': ciclo,
        'cup': centro,
        'crsep': materia.upper(),
        'ordenp': '0',
        'mostrarp': '1000'
    }
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    try:
        response = requests.post(URL_SIIAU, data=payload, headers=headers, timeout=10)
        response.encoding = 'latin-1'
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Error conectando con SIIAU: {str(e)}")

    soup = BeautifulSoup(response.text, 'html.parser')
    tabla = soup.find('table', {'border': '1'})
    if not tabla:
        return []

    filas = tabla.find_all('tr')
    secciones = []

    for fila in filas:
        celdas = fila.find_all('td', recursive=False)
        if len(celdas) < 9:
            continue

        nrc = celdas[0].get_text(strip=True)
        if not nrc.isdigit():
            continue

        clave = celdas[1].get_text(strip=True)
        nombre_materia = celdas[2].get_text(strip=True)
        seccion = celdas[3].get_text(strip=True)
        
        try:
            creditos = int(celdas[4].get_text(strip=True))
            cupo = int(celdas[5].get_text(strip=True))
            disponibles = int(celdas[6].get_text(strip=True))
        except ValueError:
            creditos, cupo, disponibles = 0, 0, 0

        horarios = []
        tabla_horarios = celdas[7].find('table')
        if tabla_horarios:
            for h_fila in tabla_horarios.find_all('tr'):
                h_cols = h_fila.find_all('td')
                if len(h_cols) >= 6:
                    hora_split = h_cols[1].get_text(strip=True).split('-')
                    horarios.append({
                        "sesion": h_cols[0].get_text(strip=True),
                        "hora_inicio": hora_split[0] if len(hora_split) > 0 else "",
                        "hora_fin": hora_split[1] if len(hora_split) > 1 else "",
                        "dias": parsear_dias(h_cols[2].get_text(strip=True)),
                        "dias_raw": h_cols[2].get_text(strip=True),
                        "edificio": h_cols[3].get_text(strip=True),
                        "aula": h_cols[4].get_text(strip=True),
                        "periodo": h_cols[5].get_text(strip=True)
                    })

        profesores = []
        tabla_profesores = celdas[8].find('table')
        if tabla_profesores:
            for p_fila in tabla_profesores.find_all('tr'):
                p_cols = p_fila.find_all('td')
                if len(p_cols) >= 2:
                    nombre_prof = p_cols[1].get_text(strip=True)
                    if nombre_prof and nombre_prof not in profesores:
                        profesores.append(nombre_prof)

        secciones.append({
            "nrc": nrc,
            "clave": clave,
            "materia": nombre_materia,
            "seccion": seccion,
            "creditos": creditos,
            "cupo": cupo,
            "disponibles": disponibles,
            "profesores": profesores,
            "horarios": horarios
        })

    return secciones

@app.get("/api/opciones")
@app.get("/opciones")
def obtener_opciones():
    return cargar_opciones_siiau()

@app.get("/")
@app.get("/api")
@app.get("/api/index.py")
@app.get("/api/oferta")
@app.get("/oferta")
def obtener_oferta(
    materia: Optional[str] = Query(None),
    ciclo: str = Query("202620"),
    centro: str = Query("D")
):
    if not materia:
        return {"status": "ok", "message": "SIIAU API activa"}

    # Extraer claves únicas separadas por comas, espacios o saltos de línea
    lista_materias = []
    for item in re.split(r'[\n,;\s]+', materia):
        clean = item.strip().upper()
        if clean and clean not in lista_materias:
            lista_materias.append(clean)

    if len(lista_materias) == 1:
        m_code = lista_materias[0]
        secciones = extraer_oferta_siiau(ciclo, centro, m_code)
        return {
            "ciclo": ciclo,
            "centro": centro,
            "materia_buscada": m_code,
            "total_secciones": len(secciones),
            "secciones": secciones
        }

    resultados = {}
    total_secciones_global = 0
    for m_code in lista_materias:
        sec = extraer_oferta_siiau(ciclo, centro, m_code)
        resultados[m_code] = sec
        total_secciones_global += len(sec)

    return {
        "ciclo": ciclo,
        "centro": centro,
        "total_materias": len(resultados),
        "total_secciones_global": total_secciones_global,
        "resultados": resultados
    }

class BatchQuery(BaseModel):
    materias: Union[List[str], str]
    ciclo: Optional[str] = "202620"
    centro: Optional[str] = "D"

@app.post("/")
@app.post("/api")
@app.post("/api/index.py")
@app.post("/api/oferta/batch")
@app.post("/oferta/batch")
def obtener_oferta_batch(query: BatchQuery):
    materias_limpias = []
    
    # Procesar string o lista de strings
    input_items = [query.materias] if isinstance(query.materias, str) else query.materias
    for raw_item in input_items:
        for clean_m in re.split(r'[\n,;\s]+', raw_item):
            clean = clean_m.strip().upper()
            if clean and clean not in materias_limpias:
                materias_limpias.append(clean)

    resultados = {}
    total_secciones_global = 0
    for m in materias_limpias:
        sec = extraer_oferta_siiau(query.ciclo, query.centro, m)
        resultados[m] = sec
        total_secciones_global += len(sec)

    return {
        "ciclo": query.ciclo,
        "centro": query.centro,
        "total_materias": len(resultados),
        "total_secciones_global": total_secciones_global,
        "resultados": resultados
    }
