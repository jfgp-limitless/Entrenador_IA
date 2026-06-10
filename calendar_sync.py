import os
import pickle
from datetime import datetime, timedelta, timezone
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from database import get_connection

SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
CREDENTIALS_FILE = 'google_credentials.json'
TOKEN_FILE = 'google_token.pickle'

# Solo estos dos calendarios
CALENDARIOS_PERMITIDOS = ['competencias', 'examenes']

CATEGORIAS = {
    'competencia': ['carrera','race','triatlón','triatlon','competencia','competition','5k','10k','21k','marathon','ironman'],
    'examen':      ['examen','exam','final','parcial','quiz','midterm'],
    'medico':      ['medico','doctor','fisio','fisioterapia','physio','cita'],
    'descanso':    ['rest','descanso','recovery','recuperacion'],
}

def clasificar_evento(nombre_calendario, titulo, descripcion=''):
    cal = nombre_calendario.lower()
    if 'competencia' in cal:
        return 'competencia'
    if 'examen' in cal or 'parcial' in cal:
        return 'examen'
    texto = (titulo + ' ' + (descripcion or '')).lower()
    for categoria, palabras in CATEGORIAS.items():
        for palabra in palabras:
            if palabra in texto:
                return categoria
    return 'otro'

def get_calendar_service():
    creds = None
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'rb') as f:
            creds = pickle.load(f)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, 'wb') as f:
            pickle.dump(creds, f)
    return build('calendar', 'v3', credentials=creds)

def crear_tabla():
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS eventos (
            id INTEGER PRIMARY KEY,
            google_id TEXT UNIQUE,
            nombre TEXT,
            categoria TEXT,
            fecha TEXT,
            fecha_fin TEXT,
            hora TEXT,
            descripcion TEXT,
            todo_el_dia INTEGER DEFAULT 0,
            calendario TEXT,
            creado_en TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def sincronizar_eventos():
    crear_tabla()
    service = get_calendar_service()

    ahora = datetime.now(timezone.utc)
    hasta = ahora + timedelta(days=365)

    calendars_result = service.calendarList().list().execute()
    todos = calendars_result.get('items', [])

    # Filtrar solo los calendarios que nos interesan
    calendarios = [
        c for c in todos
        if any(p in c['summary'].lower() for p in CALENDARIOS_PERMITIDOS)
    ]

    if not calendarios:
        print("No se encontraron los calendarios 'Competencias' o 'Examenes'")
        print(f"Calendarios disponibles: {[c['summary'] for c in todos]}")
        return

    print(f"Leyendo: {[c['summary'] for c in calendarios]}")

    conn = get_connection()
    c = conn.cursor()
    nuevos = 0
    actualizados = 0

    for calendario in calendarios:
        cal_id = calendario['id']
        cal_nombre = calendario['summary']

        try:
            result = service.events().list(
                calendarId=cal_id,
                timeMin=ahora.isoformat(),
                timeMax=hasta.isoformat(),
                maxResults=100,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
        except Exception as ex:
            print(f"  Error leyendo {cal_nombre}: {ex}")
            continue

        eventos = result.get('items', [])
        print(f"  {cal_nombre}: {len(eventos)} eventos")

        for e in eventos:
            google_id = e['id']
            nombre = e.get('summary', 'Sin titulo')
            descripcion = e.get('description', '')
            categoria = clasificar_evento(cal_nombre, nombre, descripcion)

            start = e['start']
            if 'dateTime' in start:
                dt = datetime.fromisoformat(start['dateTime'].replace('Z', '+00:00'))
                fecha = dt.strftime('%Y-%m-%d')
                hora = dt.strftime('%H:%M')
                todo_el_dia = 0
            else:
                fecha = start['date']
                hora = ''
                todo_el_dia = 1

            end = e.get('end', {})
            if 'dateTime' in end:
                dt_fin = datetime.fromisoformat(end['dateTime'].replace('Z', '+00:00'))
                fecha_fin = dt_fin.strftime('%Y-%m-%d')
            else:
                fecha_fin = end.get('date', fecha)

            existe = c.execute(
                "SELECT id FROM eventos WHERE google_id = ?", (google_id,)
            ).fetchone()

            if existe:
                c.execute("""
                    UPDATE eventos
                    SET nombre=?, categoria=?, fecha=?, fecha_fin=?,
                        hora=?, descripcion=?, todo_el_dia=?, calendario=?
                    WHERE google_id=?
                """, (nombre, categoria, fecha, fecha_fin, hora,
                      descripcion, todo_el_dia, cal_nombre, google_id))
                actualizados += 1
            else:
                c.execute("""
                    INSERT INTO eventos
                    (google_id, nombre, categoria, fecha, fecha_fin, hora, descripcion, todo_el_dia, calendario)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (google_id, nombre, categoria, fecha, fecha_fin,
                      hora, descripcion, todo_el_dia, cal_nombre))
                nuevos += 1

    conn.commit()
    conn.close()
    print(f"\nNuevos: {nuevos} | Actualizados: {actualizados}")

if __name__ == "__main__":
    print("Sincronizando Google Calendar...")
    sincronizar_eventos()