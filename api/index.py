from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Set, Tuple, Union
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

URL_SIIAU = "https://siiauescolar.siiau.udg.mx/wal/sspseca.consulta_oferta"
FALLBACK_CENTROS = [
    {"val": "D", "text": "D - C.U. DE CS. EXACTAS E ING. (CUCEI)"},
    {"val": "3", "text": "3 - C. U. DE TLAJOMULCO"},
    {"val": "4", "text": "4 - C. U. DE GUADALAJARA"},
    {"val": "5", "text": "5 - C.U. DE TLAQUEPAQUE"},
    {"val": "6", "text": "6 - C.U. DE CHAPALA"},
    {"val": "A", "text": "A - C.U. DE ARTE, ARQ. Y DISEÑO (CUAAD)"},
    {"val": "B", "text": "B - C.U. DE CS. BIOLOGICO Y AGR. (CUCBA)"},
    {"val": "C", "text": "C - C.U. DE CS. ECONOMICO-ADMVAS. (CUCEA)"},
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
    {"val": "202620", "text": "202620 - Calendario 26 B"},
    {"val": "202710", "text": "202710 - Calendario 27 A"},
    {"val": "202680", "text": "202680 - Ciclo de Verano 2026"},
    {"val": "202610", "text": "202610 - Calendario 26 A"},
    {"val": "202580", "text": "202580 - Ciclo de Verano 2025"},
    {"val": "202520", "text": "202520 - Calendario 25 B"},
    {"val": "202510", "text": "202510 - Calendario 25 A"}
]

def parsear_dias(dias_raw: str) -> List[str]:
    # SIIAU representa los días con iniciales (L, M, I, J, V, S), a veces
    # separados por puntos. No usar el índice de los tokens: los puntos
    # desplazan los días y producen asignaciones incorrectas.
    letras = {"L": "Lunes", "M": "Martes", "I": "Miércoles",
              "X": "Miércoles", "J": "Jueves", "V": "Viernes", "S": "Sábado", "D": "Domingo"}
    encontrados = []
    for token in re.findall(r"[A-ZÁÉÍÓÚÑ]+", (dias_raw or "").upper()):
        dia = letras.get(token) or (letras.get(token[0]) if len(token) == 1 else None)
        if dia and dia not in encontrados:
            encontrados.append(dia)
    return encontrados


DIAS_ALIASES = {
    "L": "Lunes", "LU": "Lunes", "LUN": "Lunes", "LUNES": "Lunes",
    "M": "Martes", "MA": "Martes", "MAR": "Martes", "MARTES": "Martes",
    "I": "Miércoles", "X": "Miércoles", "MI": "Miércoles", "MIE": "Miércoles", "MIERCOLES": "Miércoles",
    "J": "Jueves", "JU": "Jueves", "JUE": "Jueves", "JUEVES": "Jueves",
    "V": "Viernes", "VI": "Viernes", "VIE": "Viernes", "VIERNES": "Viernes",
    "S": "Sábado", "SA": "Sábado", "SAB": "Sábado", "SABADO": "Sábado",
    "D": "Domingo", "DO": "Domingo", "DOM": "Domingo", "DOMINGO": "Domingo",
}


def normalizar_materia(raw: str) -> str:
    """Normaliza una clave y rechaza valores que no parecen claves académicas."""
    clave = (raw or "").strip().upper()
    if not re.fullmatch(r"[A-Z0-9]{2,12}", clave):
        raise ValueError("La clave debe tener entre 2 y 12 letras o números, sin espacios ni símbolos.")
    return clave


def parsear_hora(valor: str) -> Optional[int]:
    if not valor:
        return None
    match = re.fullmatch(r"\s*(\d{1,2}):?(\d{2})\s*", str(valor))
    if not match:
        return None
    hora, minuto = int(match.group(1)), int(match.group(2))
    if hora > 23 or minuto > 59:
        return None
    return hora * 60 + minuto


def seccion_cumple_disponibilidad(seccion: dict, dias: Optional[Set[str]], inicio: Optional[int], fin: Optional[int]) -> bool:
    for horario in seccion.get("horarios", []):
        dias_clase = set(horario.get("dias") or parsear_dias(horario.get("dias_raw", "")))
        hora_inicio = parsear_hora(horario.get("hora_inicio", ""))
        hora_fin = parsear_hora(horario.get("hora_fin", ""))
        # Si SIIAU entrega un horario incompleto, no se puede asegurar que
        # cumpla disponibilidad ni que esté libre de empalmes.
        if not dias_clase or hora_inicio is None or hora_fin is None or hora_inicio >= hora_fin:
            return False
        if dias and dias_clase and not dias_clase.issubset(dias):
            return False
        if inicio is not None and hora_inicio < inicio:
            return False
        if fin is not None and hora_fin > fin:
            return False
    return True


def secciones_se_empalman(a: dict, b: dict) -> bool:
    for ha in a.get("horarios", []):
        dias_a = set(ha.get("dias") or parsear_dias(ha.get("dias_raw", "")))
        ia, fa = parsear_hora(ha.get("hora_inicio", "")), parsear_hora(ha.get("hora_fin", ""))
        if not dias_a or ia is None or fa is None:
            continue
        for hb in b.get("horarios", []):
            dias_b = set(hb.get("dias") or parsear_dias(hb.get("dias_raw", "")))
            ib, fb = parsear_hora(hb.get("hora_inicio", "")), parsear_hora(hb.get("hora_fin", ""))
            if dias_a.intersection(dias_b) and ib is not None and fb is not None and ia < fb and ib < fa:
                return True
    return False


def puntuar_horario(secciones: List[dict], profesores_deseados: Set[str]) -> dict:
    """Menor puntuación es mejor: penaliza huecos y jornadas largas."""
    por_dia: Dict[str, List[Tuple[int, int]]] = {}
    profesores = {p.casefold() for sec in secciones for p in sec.get("profesores", [])}
    for sec in secciones:
        for h in sec.get("horarios", []):
            inicio, fin = parsear_hora(h.get("hora_inicio", "")), parsear_hora(h.get("hora_fin", ""))
            if inicio is None or fin is None:
                continue
            for dia in h.get("dias") or parsear_dias(h.get("dias_raw", "")):
                por_dia.setdefault(dia, []).append((inicio, fin))
    huecos, amplitud = 0, 0
    for tramos in por_dia.values():
        tramos.sort()
        amplitud += tramos[-1][1] - tramos[0][0]
        fin_anterior = tramos[0][1]
        for inicio, fin in tramos[1:]:
            if inicio > fin_anterior:
                huecos += inicio - fin_anterior
            fin_anterior = max(fin_anterior, fin)
    coincidencias = sum(1 for prof in profesores_deseados if any(prof in p for p in profesores))
    lugares = sum(1 for sec in secciones if sec.get("disponibles", 0) > 0)
    score = huecos + amplitud * 0.05 + len(por_dia) * 25 - coincidencias * 120 - lugares * 5
    return {"puntuacion": round(score, 2), "minutos_libres": huecos,
            "dias_con_clase": len(por_dia), "minutos_de_jornada": amplitud,
            "profesores_deseados_encontrados": coincidencias}

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

        # T05: Clasificamos el estado de la sección (útil para el frontend)
        if disponibles > 0:
            status = "disponible"
        else:
            status = "lleno"

        secciones.append({
            "nrc": nrc,
            "clave": clave,
            "materia": nombre_materia,
            "seccion": seccion,
            "creditos": creditos,
            "cupo": cupo,
            "disponibles": disponibles,
            "status": status,
            "tipo": "seccion",
            "profesores": profesores,
            "horarios": horarios
        })

    return secciones

@app.get("/api/opciones")
@app.get("/opciones")
def obtener_opciones():
    return {"ciclos": FALLBACK_CICLOS, "centros": FALLBACK_CENTROS}

@app.get("/")
@app.get("/api")
@app.get("/api/oferta")
@app.get("/oferta")
def obtener_oferta(
    materia: Optional[str] = Query(None),
    ciclo: str = Query("202620"),
    centro: str = Query("D")
):
    if not materia:
        return {"status": "ok", "message": "SIIAU API activa"}

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
@app.post("/api/oferta/batch")
@app.post("/oferta/batch")
def obtener_oferta_batch(query: BatchQuery):
    materias_limpias = []
    validacion = {}
    input_items = [query.materias] if isinstance(query.materias, str) else query.materias
    for raw_item in input_items:
        for clean_m in re.split(r'[\n,;\s]+', raw_item):
            if not clean_m.strip():
                continue
            try:
                clean = normalizar_materia(clean_m)
                if clean not in materias_limpias:
                    materias_limpias.append(clean)
                    validacion[clean] = {"valida": True, "estado": "pendiente"}
            except ValueError as exc:
                validacion[clean_m.strip()] = {"valida": False, "estado": "clave_invalida", "mensaje": str(exc)}

    if len(materias_limpias) > 20:
        raise HTTPException(status_code=422, detail="Se permite consultar un máximo de 20 materias por solicitud.")

    resultados = {}
    total_secciones_global = 0
    for m in materias_limpias:
        sec = extraer_oferta_siiau(query.ciclo, query.centro, m)
        resultados[m] = sec
        total_secciones_global += len(sec)
        validacion[m] = {"valida": True, "estado": "con_oferta" if sec else "sin_oferta",
                         "total_secciones": len(sec)}

    return {
        "ciclo": query.ciclo,
        "centro": query.centro,
        "total_materias": len(resultados),
        "total_secciones_global": total_secciones_global,
        "resultados": resultados,
        "validacion": validacion
    }


@app.get("/api/index.py")
async def vercel_get_dispatch(request: Request):
    # vercel.json forwards /api/* to this function and carries the original
    # subpath in `path`, so route lookup still reaches the intended endpoint.
    path = request.query_params.get("path", "").strip("/")
    if path == "opciones":
        return obtener_opciones()
    params = request.query_params
    return obtener_oferta(
        materia=params.get("materia"),
        ciclo=params.get("ciclo", "202620"),
        centro=params.get("centro", "D"),
    )


@app.post("/api/index.py")
async def vercel_post_dispatch(request: Request):
    path = request.query_params.get("path", "").strip("/")
    body = await request.json()
    if path == "materias/validar":
        return validar_materias(BatchQuery.parse_obj(body))
    if path == "horarios/generar":
        return generar_horarios(GenerarHorariosRequest.parse_obj(body))
    return obtener_oferta_batch(BatchQuery.parse_obj(body))


class GenerarHorariosRequest(BatchQuery):
    dias_disponibles: Optional[List[str]] = None
    hora_inicio: Optional[str] = None
    hora_fin: Optional[str] = None
    profesores_deseados: List[str] = Field(default_factory=list)
    profesores_excluidos: List[str] = Field(default_factory=list)
    max_resultados: int = 20


def normalizar_dias(dias: Optional[List[str]]) -> Optional[Set[str]]:
    if not dias:
        return None
    normalizados = set()
    for valor in dias:
        clave = re.sub(r"[^A-ZÁÉÍÓÚÑ]", "", valor.upper())
        dia = DIAS_ALIASES.get(clave)
        if not dia:
            raise HTTPException(status_code=422, detail=f"Día no reconocido: {valor}")
        normalizados.add(dia)
    return normalizados


def generar_combinaciones(materias: List[str], resultados: dict, dias: Optional[Set[str]],
                          inicio: Optional[int], fin: Optional[int], excluidos: Set[str],
                          deseados: Set[str], limite: int) -> Tuple[List[dict], int, bool]:
    opciones = []
    for materia in materias:
        candidatas = []
        for sec in resultados.get(materia, []):
            profes = [p.casefold() for p in sec.get("profesores", [])]
            if any(excluido in p for excluido in excluidos for p in profes):
                continue
            if seccion_cumple_disponibilidad(sec, dias, inicio, fin):
                candidatas.append(sec)
        if not candidatas:
            return [], 0, False
        opciones.append(candidatas)

    combinaciones = []
    evaluadas = 0
    visitadas = 0
    max_evaluadas = 100000
    max_visitadas = 1000000

    def explorar(indice: int, elegidas: List[dict]):
        nonlocal evaluadas, visitadas
        if evaluadas >= max_evaluadas or visitadas >= max_visitadas:
            return
        visitadas += 1
        if indice == len(opciones):
            evaluadas += 1
            combinaciones.append({"secciones": list(elegidas), **puntuar_horario(elegidas, deseados)})
            return
        for seccion in opciones[indice]:
            if any(secciones_se_empalman(seccion, existente) for existente in elegidas):
                continue
            elegidas.append(seccion)
            explorar(indice + 1, elegidas)
            elegidas.pop()
            if evaluadas >= max_evaluadas or visitadas >= max_visitadas:
                break

    explorar(0, [])
    combinaciones.sort(key=lambda h: (h["puntuacion"], h["minutos_libres"], h["dias_con_clase"]))
    limitada = evaluadas >= max_evaluadas or visitadas >= max_visitadas
    return combinaciones[:limite], evaluadas, limitada


@app.post("/api/materias/validar")
@app.post("/materias/validar")
def validar_materias(query: BatchQuery):
    """Comprueba formato de clave y presencia de oferta en SIIAU."""
    items = [query.materias] if isinstance(query.materias, str) else query.materias
    validacion = {}
    claves = []
    for raw in items:
        for item in re.split(r"[\n,;\s]+", raw):
            if not item:
                continue
            try:
                clave = normalizar_materia(item)
                if clave not in claves:
                    claves.append(clave)
            except ValueError as exc:
                validacion[item] = {"valida": False, "estado": "clave_invalida", "mensaje": str(exc)}
    if len(claves) > 20:
        raise HTTPException(status_code=422, detail="Se permite validar un máximo de 20 materias por solicitud.")
    for clave in claves:
        secciones = extraer_oferta_siiau(query.ciclo, query.centro, clave)
        validacion[clave] = {"valida": True, "estado": "con_oferta" if secciones else "sin_oferta",
                             "total_secciones": len(secciones)}
    return {"ciclo": query.ciclo, "centro": query.centro, "validacion": validacion}


@app.post("/api/horarios/generar")
@app.post("/horarios/generar")
def generar_horarios(query: GenerarHorariosRequest):
    """Obtiene oferta, filtra secciones y devuelve horarios sin empalmes ordenados por calidad."""
    items = [query.materias] if isinstance(query.materias, str) else query.materias
    materias, validacion = [], {}
    for raw in items:
        for item in re.split(r"[\n,;\s]+", raw):
            if not item:
                continue
            try:
                clave = normalizar_materia(item)
                if clave not in materias:
                    materias.append(clave)
                    validacion[clave] = {"valida": True, "estado": "pendiente"}
            except ValueError as exc:
                validacion[item] = {"valida": False, "estado": "clave_invalida", "mensaje": str(exc)}
    if not materias:
        raise HTTPException(status_code=422, detail="Ingresa al menos una clave de materia válida.")
    if any(not item["valida"] for item in validacion.values()):
        return {"ciclo": query.ciclo, "centro": query.centro, "materias": materias,
                "validacion": validacion, "total_combinaciones_evaluadas": 0,
                "busqueda_limitada": False, "total_horarios": 0, "horarios": [],
                "mensaje": "Corrige las claves inválidas antes de generar horarios."}
    if len(materias) > 10:
        raise HTTPException(status_code=422, detail="El generador permite un máximo de 10 materias por solicitud.")
    if query.max_resultados < 1 or query.max_resultados > 50:
        raise HTTPException(status_code=422, detail="max_resultados debe estar entre 1 y 50.")

    dias = normalizar_dias(query.dias_disponibles)
    inicio = parsear_hora(query.hora_inicio) if query.hora_inicio else None
    fin = parsear_hora(query.hora_fin) if query.hora_fin else None
    if query.hora_inicio and inicio is None or query.hora_fin and fin is None:
        raise HTTPException(status_code=422, detail="Usa horas válidas en formato HH:MM, por ejemplo 08:00.")
    if inicio is not None and fin is not None and inicio >= fin:
        raise HTTPException(status_code=422, detail="hora_inicio debe ser anterior a hora_fin.")

    resultados = {m: extraer_oferta_siiau(query.ciclo, query.centro, m) for m in materias}
    for materia, secciones in resultados.items():
        validacion[materia] = {"valida": True, "estado": "con_oferta" if secciones else "sin_oferta",
                               "total_secciones": len(secciones)}
    profesores_excluidos = {p.strip().casefold() for p in query.profesores_excluidos if p.strip()}
    profesores_deseados = {p.strip().casefold() for p in query.profesores_deseados if p.strip()}
    horarios, evaluadas, limitada = generar_combinaciones(
        materias, resultados, dias, inicio, fin, profesores_excluidos, profesores_deseados,
        query.max_resultados
    )
    for numero, horario in enumerate(horarios, 1):
        horario["numero"] = numero
    return {
        "ciclo": query.ciclo, "centro": query.centro, "materias": materias,
        "validacion": validacion, "total_combinaciones_evaluadas": evaluadas,
        "busqueda_limitada": limitada,
        "total_horarios": len(horarios), "horarios": horarios,
        "mensaje": None if horarios else "No se encontró una combinación sin empalmes que cumpla los filtros."
    }
