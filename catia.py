#catIA code for Valentina Palma, 2024

import os
import configparser
import azure.cognitiveservices.speech as speechsdk
import openai
import time
from RPLCD.i2c import CharLCD
from board import SCL, SDA
import busio
from adafruit_pca9685 import PCA9685

# Configuración de la pantalla LCD
lcd = CharLCD('PCF8574', 0x27)

# Configuración del PCA9685
i2c = busio.I2C(SCL, SDA)
pca = PCA9685(i2c, address=0x40)
pca.frequency = 50

# Caracteres personalizados
ojo_abierto = [
    [0b00000, 0b00011, 0b00111, 0b01111, 0b11111, 0b11111, 0b11111, 0b11111],  # ojo_abierto1
    [0b00000, 0b11000, 0b11100, 0b11110, 0b00111, 0b00111, 0b00011, 0b00011],  # ojo_abierto2
    [0b11111, 0b11001, 0b11001, 0b11001, 0b01111, 0b00111, 0b00011, 0b00000],  # ojo_abierto3
    [0b11111, 0b11111, 0b11111, 0b11111, 0b11110, 0b11100, 0b11000, 0b00000],  # ojo_abierto4
]

ojo_cerrado = [
    [0b00000, 0b00000, 0b00000, 0b00000, 0b10000, 0b10000, 0b10000, 0b10000],  # ojo_cerrado1
    [0b00000, 0b00000, 0b00000, 0b00000, 0b00001, 0b00001, 0b00001, 0b00001],  # ojo_cerrado2
    [0b10000, 0b10000, 0b10000, 0b11000, 0b01100, 0b00111, 0b00011, 0b00000],  # ojo_cerrado3
    [0b00001, 0b00001, 0b00001, 0b00001, 0b00110, 0b11100, 0b11000, 0b00000],  # ojo_cerrado4
]

boca_cerrada = [
    [0b00000, 0b0000, 0b01000, 0b01000, 0b00100, 0b00100, 0b00011, 0b00000],  # boca1
    [0b00000, 0b00000, 0b00010, 0b00010, 0b00100, 0b00100, 0b11000, 0b00000],  # boca2
]

boca_abierta = [
    [0b00000, 0b00000, 0b01111, 0b01000, 0b00100, 0b00100, 0b00011, 0b00000],  # boca1
    [0b00000, 0b00000, 0b11110, 0b00010, 0b00100, 0b00100, 0b11000, 0b00000],  # boca2
]

def create_custom_chars(patterns, start_index=0):
    for i, pattern in enumerate(patterns):
        lcd.create_char(start_index + i, pattern)

def display_features(open=True):
    if open:
        create_custom_chars(ojo_abierto, 0)
        create_custom_chars(boca_abierta, 4)
    else:
        create_custom_chars(ojo_cerrado, 0)
        create_custom_chars(boca_cerrada, 4)

    # Ojos
    lcd.cursor_pos = (0, 3)
    for i in range(2):
        lcd.write_string(chr(i))
    lcd.cursor_pos = (1, 3)
    for i in range(2, 4):
        lcd.write_string(chr(i))

    # Boca
    lcd.cursor_pos = (1, 7)
    for i in range(4, 6):
        lcd.write_string(chr(i))

    # Ojos
    lcd.cursor_pos = (0, 11)
    for i in range(2):
        lcd.write_string(chr(i))
    lcd.cursor_pos = (1, 11)
    for i in range(2, 4):
        lcd.write_string(chr(i))

# Configuración de los servomotores
def set_servo_angle(channel, angle):
    # Convertir ángulo a valor de pulso
    pulse = int((angle * (650 - 150) / 180) + 150)
    pca.channels[channel].duty_cycle = int(pulse * 65536 / 4096)

def move_arms():
    # Mover los brazos
    set_servo_angle(0, 90)
    set_servo_angle(1, 90)
    time.sleep(1)
    set_servo_angle(0, 0)
    set_servo_angle(1, 0)
    time.sleep(1)

# archivo keys.txt
config = configparser.ConfigParser()
config.read('keys.txt')

#llamada de OpenAI
openai.api_key = config.get('openai', 'OPENAI_API_KEY')

#llamada de Azure Speech
speech_key = config.get('azure', 'SPEECH_KEY')
service_region = config.get('azure', 'SPEECH_REGION')
speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=service_region)
speech_config.speech_recognition_language = "es-CL"  # Español - Chile
speech_config.speech_synthesis_voice_name = "es-CL-CatalinaNeural"  # Voz femenina en español de Chile

# Configuración de audio para entrada utilizando el micrófono predeterminado
audio_config_input = speechsdk.audio.AudioConfig(use_default_microphone=True)

# Función para transcribir audio a texto
def recognize_from_mic():
    speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config_input)
    print("Escuchando...")
    speech_recognition_result = speech_recognizer.recognize_once_async().get()
    if speech_recognition_result.reason == speechsdk.ResultReason.RecognizedSpeech:
        print(f"Reconocido: {speech_recognition_result.text}")
        return speech_recognition_result.text
    else:
        print(f"No se pudo reconocer el audio: {speech_recognition_result.reason}")
        return ""

# Función para sintetizar texto a audio
def speak_text(text):
    display_features(open=True)  #mostrar expresión de boca abierta y ojos abiertos
    move_arms()  #mover los brazos mientras habla
    speech_synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config)
    speech_synthesis_result = speech_synthesizer.speak_text_async(text).get()
    if speech_synthesis_result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        print(f"Hablando: {text}")
    else:
        print(f"No se pudo sintetizar el audio: {speech_synthesis_result.reason}")
    display_features(open=False)  # Mostrar expresión de boca cerrada y ojos cerrados

# Función para obtener respuesta de OpenAI
def get_openai_response(prompt):
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "Eres un asistente de voz amigable para niños hospitalizados entre 6 y 10 años. Debes responder y jugar con ellos de manera divertida y apropiada para su edad."},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message['content'].strip()

# Función principal
def main():
    speak_text("¡Hola! Mucho gusto, soy Catia, tu compañero en tu estadía aquí. ¡Puedes hablarme de lo que sea!")
    keep_listening = True
    while keep_listening:
        text = recognize_from_mic().lower()
        if text:
            if "chao katia" in text:
                speak_text("¡Adiós! Espero que te mejores pronto. Nos vemos luego, estoy para ti para lo que sea.")
                keep_listening = False
            else:
                response = get_openai_response(text)
                speak_text(response)
        time.sleep(1)  # Esperar un segundo antes de volver a escuchar

#iniciar el script con "Hola Katia"
def listen_for_activation():
    while True:
        text = recognize_from_mic().lower()
        if "hola" in text or "hola katia" in text:
            main()
            break

if __name__ == "__main__":
    listen_for_activation()
