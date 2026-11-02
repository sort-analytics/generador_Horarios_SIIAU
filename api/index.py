from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import requests
from bs4 import BeautifulSoup

app = FastAPI(title="SIIAU Oferta Académica API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

URL_SIIAU = "https://siiauescolar.siiau.udg.mx/wal/sspseca.consulta_oferta"
DIAS_MAP = {0: "Lunes", 1: "Martes", 2: "Miércoles", 3: "Jueves", 4: "Viernes", 5: "Sábado"}

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

@app.get("/api/oferta")
@app.get("/oferta")
def obtener_oferta(materia: str = Query(...), ciclo: str = Query("202620"), centro: str = Query("D")):
    secciones = extraer_oferta_siiau(ciclo, centro, materia)
    return {
        "ciclo": ciclo,
        "centro": centro,
        "materia_buscada": materia.upper(),
        "total_secciones": len(secciones),
        "secciones": secciones
    }

class BatchQuery(BaseModel):
    materias: List[str]
    ciclo: Optional[str] = "202620"
    centro: Optional[str] = "D"

@app.post("/api/oferta/batch")
@app.post("/oferta/batch")
def obtener_oferta_batch(query: BatchQuery):
    resultados = {}
    for m in query.materias:
        clean = m.strip().upper()
        if clean:
            resultados[clean] = extraer_oferta_siiau(query.ciclo, query.centro, clean)
    return {
        "ciclo": query.ciclo,
        "centro": query.centro,
        "total_materias": len(resultados),
        "resultados": resultados
    }
