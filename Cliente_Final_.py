import socket
import wave
import whisper

# ================= CONFIGURACIÓN ==================
HOST_BEAGLE = "192.168.7.2"  # 🔹 IP REAL DE LA BEAGLEPLAY
PORT_RECIBO = 5000
PORT_ENVIO = 5001
ARCHIVO_RECIBIDO = "audio_recibido.wav"
BUFFER_SIZE = 1024

# Cargar modelo de Whisper
print("🔄 Cargando modelo de Whisper...")
model = whisper.load_model("small")
print("✅ Modelo cargado")

def recibir_audio():
    """Recibe el archivo de audio de la BeaglePlay"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("0.0.0.0", PORT_RECIBO))  # 🔹 Acepta conexiones de cualquier IP
        s.listen(1)
        conn, addr = s.accept()
        
        with open(ARCHIVO_RECIBIDO, "wb") as f:
            while data := conn.recv(BUFFER_SIZE):
                f.write(data)

        print(f"✅ Archivo recibido.")

def transcribir_audio():
    """Transcribe el audio con Whisper"""
    result = model.transcribe(ARCHIVO_RECIBIDO, language="es")
    return result["text"]

def enviar_transcripcion(texto):
    """Envía la transcripción a la BeaglePlay"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST_BEAGLE, PORT_ENVIO))  # 🔹 Ahora usa la IP real de la BeaglePlay
        s.sendall(texto.encode('utf-8'))
        print("✅ Transcripción enviada.")

while True:
    recibir_audio()
    texto = transcribir_audio()
    enviar_transcripcion(texto)
