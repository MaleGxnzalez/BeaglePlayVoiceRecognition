import alsaaudio
import numpy as np
import wave
import socket
import os
import json
import time
import paho.mqtt.client as mqtt
import ssl
import threading

# ================= CONFIGURACIÓN ==================
FS = 44100
CHANNELS = 1
DURACION = 4
FORMATO = alsaaudio.PCM_FORMAT_S16_LE
ARCHIVO_SALIDA = "audio_grabado.wav"
HOST_PC = "192.168.7.1"  # 🔹 IP del PC
PORT_ENVIO = 5000
PORT_TRANSCRIPCION = 5001
BUFFER_SIZE = 1024

# 🔹 AWS IoT Core Configuración
AWS_IOT_ENDPOINT = "a2284eoi46pj4v-ats.iot.us-east-1.amazonaws.com"
CLIENT_ID = "BeaglePlay"
TOPIC_REQUEST = "test/solicitud"
TOPIC_RESPONSE = "test/+/respuesta"
CERTIFICATE_PATH = "/home/debian/certificate.pem.crt"
PRIVATE_KEY_PATH = "/home/debian/private.pem.key"
ROOT_CA_PATH = "/home/debian/AmazonRootCA1.pem"

# Variable global para almacenar la transcripción y la respuesta de AWS
ultima_transcripcion = "Sin transcripción disponible"
ultima_respuesta = None

def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print("✅ Conectado a AWS IoT Core")
        client.subscribe(TOPIC_RESPONSE)
    else:
        print(f"❌ Error de conexión: {rc}")

def on_message(client, userdata, msg):
    global ultima_respuesta
    try:
        payload = msg.payload.decode()
        print(f"\n📥 Mensaje bruto recibido de AWS IoT Core: {payload}")  # Debug
        ultima_respuesta = json.loads(payload)  # Convertir a diccionario
        print(f"\n📥 *Dato procesado*: {ultima_respuesta}\n")  # Mostrar en formato claro
    except Exception as e:
        print(f"Error procesando mensaje: {str(e)}")


def grabar_audio():
    """Graba el audio usando ALSA directamente"""
    print("🎙 Grabando audio...")

    try:
        inp = alsaaudio.PCM(alsaaudio.PCM_CAPTURE, alsaaudio.PCM_NORMAL, device="plughw:0,0")
        inp.setchannels(CHANNELS)
        inp.setrate(FS)
        inp.setformat(FORMATO)
        inp.setperiodsize(160)

        frames = []
        num_frames = int(DURACION * FS / 160)

        for _ in range(num_frames):
            length, data = inp.read()
            if length > 0:
                frames.append(data)

        with wave.open(ARCHIVO_SALIDA, 'wb') as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(2)  
            wf.setframerate(FS)
            wf.writeframes(b''.join(frames))

        print("✅ Grabación finalizada.")
    except Exception as e:
        print(f"❌ Error durante la grabación: {str(e)}")

def enviar_audio():
    """Envía el archivo de audio al PC"""
    if not os.path.exists(ARCHIVO_SALIDA):
        print("❌ No se encontró el archivo de audio.")
        return False

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.connect((HOST_PC, PORT_ENVIO))
            print(f"📤 Enviando archivo de audio a {HOST_PC}...")

            with open(ARCHIVO_SALIDA, "rb") as f:
                while chunk := f.read(BUFFER_SIZE):
                    s.sendall(chunk)

            print("✅ Archivo enviado correctamente.")
            return True
        except Exception as e:
            print(f"❌ Error enviando archivo: {str(e)}")
            return False

def recibir_transcripcion():
    """Recibe la transcripción del PC"""
    global ultima_transcripcion

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("0.0.0.0", PORT_TRANSCRIPCION))
        s.listen(1)

        print(f"📡 Esperando transcripción en puerto {PORT_TRANSCRIPCION}...")

        conn, addr = s.accept()
        data = conn.recv(BUFFER_SIZE).decode('utf-8')
        
        if data:
            ultima_transcripcion = data
            print(f"\n📄 Transcripción recibida: {ultima_transcripcion}")
            return True
        else:
            print("❌ No se recibió ninguna transcripción.")
            return False

def solicitar_datos(tipo_sensor):
    """Envía una solicitud a AWS IoT Core y espera la respuesta"""
    global ultima_respuesta

    topic = f"test/{tipo_sensor}"
    mensaje = {"payload": json.dumps({"sensor": tipo_sensor})}
    client.publish(topic, json.dumps(mensaje))  # Enviar solicitud

    print(f"\n📤 Solicitud enviada para: {tipo_sensor}")

    # Esperar respuesta de AWS IoT Core
    time.sleep(1)  
    if ultima_respuesta:
        print(f"🔍 Valor actual de {tipo_sensor}: {ultima_respuesta['valor']} {ultima_respuesta['unidad']}")
        ultima_respuesta = None  # Resetear para la próxima solicitud
    else:
        print("⚠ No se recibió respuesta. Verifica conexión o permisos.")

# Configurar cliente MQTT
client = mqtt.Client(client_id=CLIENT_ID, callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
client.tls_set(ca_certs=ROOT_CA_PATH, certfile=CERTIFICATE_PATH, keyfile=PRIVATE_KEY_PATH, tls_version=ssl.PROTOCOL_TLSv1_2)
client.on_connect = on_connect
client.on_message = on_message
client.connect(AWS_IOT_ENDPOINT, 8883, 60)
client.loop_start()

# 🔄 Flujo de ejecución
while True:
    input("\n🔄 Presiona Enter para grabar y procesar audio...")
    grabar_audio()
    
    if enviar_audio():
        if recibir_transcripcion():
            if "temperatura" in ultima_transcripcion.lower():
                solicitar_datos("temperatura")
            if "voltaje" in ultima_transcripcion.lower():
                solicitar_datos("voltaje")