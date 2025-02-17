import os
import datetime
from flask import Flask, request, render_template, jsonify
import speech_recognition as sr
import firebase_admin
from firebase_admin import credentials, firestore

# Initialize Firebase Admin
cred = credentials.Certificate("./credentials/transcription-de-parole-firebase-adminsdk-pfoqh-46e9e948ce.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

app = Flask(__name__)

TXT_FOLDER = 'transcription'
AUDIO_FOLDER = 'audio'
os.makedirs(TXT_FOLDER, exist_ok=True)
os.makedirs(AUDIO_FOLDER, exist_ok=True)

def transcribe_audio(audio_data) -> str:
   
    r = sr.Recognizer()
    try:
        text = r.recognize_google(audio_data, language="en-US")
        return text
    except sr.UnknownValueError:
        return "Google Speech Recognition could not understand audio."
    except sr.RequestError:
        return "Could not request results from Google Speech Recognition service."

def save_audio_to_storage(audio_file) -> str:
  
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    audio_path = os.path.join(AUDIO_FOLDER, f"audio_{timestamp}.wav")
    audio_file.save(audio_path)
    print(f"Audio file saved at: {audio_path}")  # Debugging statement
    return audio_path

def save_transcription_to_storage(transcription: str) -> str:
   
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    transcription_txt_path = os.path.join(TXT_FOLDER, f"transcription_{timestamp}.txt")

    # Save locally
    with open(transcription_txt_path, 'w') as txt_file:
        txt_file.write(transcription)

    # Save to Firestore
    transcription_data = {
        "file_name": f"transcription_{timestamp}.txt",
        "transcription": transcription,
        "language": "en-US",
        "timestamp": firestore.SERVER_TIMESTAMP,
    }
    db.collection("transcriptions").add(transcription_data)

    return transcription_txt_path

@app.route("/", methods=["GET", "POST"])
def upload_file():
    error = None
    transcription = ""

    if request.method == "POST":
        if 'start_recording' in request.form:
            return jsonify(message="Recording started"), 200

        elif 'stop_recording' in request.form:
            try:
                recognizer = sr.Recognizer()
                with sr.Microphone() as source:
                    print("Say something...")
                    audio_data = recognizer.listen(source)

                transcription = transcribe_audio(audio_data)
                transcription_txt_path = save_transcription_to_storage(transcription)

                return jsonify(message=f"Recording stopped, transcription saved as {transcription_txt_path}."), 200

            except Exception as e:
                error = str(e)

    return render_template("index.html", transcription=transcription, error=error)

@app.route("/transcribe_audio", methods=["POST"])
def transcribe_audio_route():
    if 'audio' not in request.files:
        return jsonify(message="No audio file received."), 400

    audio_file = request.files['audio']
    audio_path = save_audio_to_storage(audio_file)
    recognizer = sr.Recognizer()

    try:
        with sr.AudioFile(audio_path) as source:
            audio_data = recognizer.record(source)
        transcription = transcribe_audio(audio_data)
        transcription_txt_path = save_transcription_to_storage(transcription)
        return jsonify(message=f"Transcription saved as {transcription_txt_path}."), 200
    except ValueError as e:
        print(f"Error processing audio file: {e}")  
        return jsonify(message=f"Error processing audio file: {e}"), 400

@app.route("/save_audio", methods=["POST"])
def save_audio():
    if 'audio' not in request.files:
        return jsonify(message="No audio file received."), 400

    audio_file = request.files['audio']
    audio_path = save_audio_to_storage(audio_file)
    return jsonify(message=f"Audio saved as {audio_path}."), 200

@app.route("/save_transcription", methods=["POST"])
def save_transcription():
    transcription = request.form.get("transcription")
    print(f"Received transcription: {transcription}")  

    if transcription:
        transcription_txt_path = save_transcription_to_storage(transcription)
        print(f"Transcription saved at: {transcription_txt_path}")  
        return jsonify(message=f"Transcription saved as {transcription_txt_path}."), 200
    else:
        print("No transcription data received.")  
        return jsonify(message="No transcription data received."), 400

if __name__ == "__main__":
    app.run(debug=True)