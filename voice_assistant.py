import tkinter as tk
from tkinter import font as tkFont, filedialog
import webbrowser
import pyttsx3
import os
import datetime
import threading
import re
import speech_recognition as sr
from youtube_transcript_api import YouTubeTranscriptApi
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lsa import LsaSummarizer

# Assuming 'default_api' is available and has a 'google_web_search' method.
# If not, you'll need to implement or mock it.
class MockDefaultAPI:
    def google_web_search(self, query):
        return {"answer": f"This is a mock answer for '{query}'."}

default_api = MockDefaultAPI()

def summarize_text(text, sentences_count=5):
    try:
        parser = PlaintextParser.from_string(text, Tokenizer("english"))
        summarizer = LsaSummarizer()
        summary_sentences = summarizer(parser.document, sentences_count)
        summary = " ".join([str(sentence) for sentence in summary_sentences])
        return summary
    except Exception as e:
        return f"Error summarizing text: {e}"

def summarize_youtube_video(youtube_url):
    try:
        video_id_match = re.search(r"v=([\w-]+)", youtube_url)
        if not video_id_match:
            return "Invalid YouTube URL."
        video_id = video_id_match.group(1)

        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        full_transcript = " ".join([item['text'] for item in transcript_list])
        return summarize_text(full_transcript)
    except Exception as e:
        return f"Error summarizing video: {e}"

class VoiceAssistant:
    def __init__(self, root):
        self.root = root
        self.root.title("Voice Assistant")
        self.root.geometry("500x700")
        self.root.configure(bg="#2c3e50")

        self.engine = pyttsx3.init()
        self.speak_lock = threading.Lock()

        self.recognizer = sr.Recognizer()
        self.microphone = None
        self.mic_status_message = ""
        try:
            self.microphone = sr.Microphone()
        except OSError:
            self.mic_status_message = "ERROR: No default microphone found. Voice input is disabled."

        self.is_listening = False
        self.transcript = []

        self.create_widgets()
        self.add_to_conversation("Assistant: Hello! How can I assist you today?", "assistant")
        if self.mic_status_message:
            self.add_to_conversation(f"Assistant: {self.mic_status_message}", "assistant")

    def create_widgets(self):
        self.primary_font = tkFont.Font(family="Roboto", size=12)
        self.title_font = tkFont.Font(family="Roboto", size=16, weight="bold")

        main_frame = tk.Frame(self.root, bg="#2c3e50")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        title_label = tk.Label(main_frame, text="Conversation", font=self.title_font, bg="#2c3e50", fg="white")
        title_label.pack(pady=(0, 10))

        self.conversation_text = tk.Text(main_frame, bg="#34495e", fg="white", font=self.primary_font, wrap=tk.WORD, borderwidth=0, highlightthickness=0)
        self.conversation_text.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        self.conversation_text.tag_configure("user", foreground="#95a5a6", justify='right')
        self.conversation_text.tag_configure("assistant", foreground="#ecf0f1", justify='left')
        self.conversation_text.config(state=tk.DISABLED)

        controls_frame = tk.Frame(main_frame, bg="#2c3e50")
        controls_frame.pack(fill=tk.X, pady=5)

        self.listen_button = tk.Button(controls_frame, text="Start Listening", font=self.primary_font, bg="#27ae60", fg="white", relief=tk.FLAT, command=self.start_listening_thread)
        self.listen_button.pack(side=tk.LEFT, expand=True, padx=5)

        self.stop_button = tk.Button(controls_frame, text="Stop Listening", font=self.primary_font, bg="#c0392b", fg="white", relief=tk.FLAT, command=self.stop_listening, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, expand=True, padx=5)

        transcript_frame = tk.Frame(main_frame, bg="#2c3e50")
        transcript_frame.pack(fill=tk.X, pady=5)

        self.save_button = tk.Button(transcript_frame, text="Save Transcript", font=self.primary_font, bg="#3498db", fg="white", relief=tk.FLAT, command=self.save_transcript)
        self.save_button.pack(side=tk.LEFT, expand=True, padx=5)

        self.summarize_button = tk.Button(transcript_frame, text="Summarize Transcript", font=self.primary_font, bg="#f39c12", fg="white", relief=tk.FLAT, command=self.summarize_full_transcript)
        self.summarize_button.pack(side=tk.LEFT, expand=True, padx=5)

        input_frame = tk.Frame(main_frame, bg="#2c3e50")
        input_frame.pack(fill=tk.X, pady=(10, 0))
        self.text_input = tk.Entry(input_frame, font=self.primary_font, bg="#34495e", fg="white", relief=tk.FLAT, insertbackground='white')
        self.text_input.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=10, padx=(0, 10))
        self.text_input.bind("<Return>", self.process_text_query)
        self.send_button = tk.Button(input_frame, text="Send", font=self.primary_font, bg="#3498db", fg="white", relief=tk.FLAT, command=self.process_text_query)
        self.send_button.pack(side=tk.RIGHT)

        if self.microphone is None:
            self.listen_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.DISABLED)

    def add_to_conversation(self, message, sender):
        self.conversation_text.config(state=tk.NORMAL)
        self.conversation_text.insert(tk.END, f"{message}\n\n", sender)
        self.conversation_text.config(state=tk.DISABLED)
        self.conversation_text.see(tk.END)

    def speak(self, text):
        threading.Thread(target=self._speak_async, args=(text,)).start()

    def _speak_async(self, text):
        with self.speak_lock:
            self.engine.say(text)
            self.engine.runAndWait()

    def start_listening_thread(self):
        if self.microphone is None:
            self.add_to_conversation("Assistant: Cannot start listening, no microphone found.", "assistant")
            return
        self.is_listening = True
        self.listen_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.add_to_conversation("Assistant: Listening...", "assistant")
        threading.Thread(target=self.listen_continuously, daemon=True).start()

    def stop_listening(self):
        self.is_listening = False
        self.listen_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.add_to_conversation("Assistant: Stopped listening.", "assistant")

    def listen_continuously(self):
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
            while self.is_listening:
                try:
                    audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=15)
                    text = self.recognizer.recognize_google(audio)
                    self.root.after(0, self.handle_transcribed_text, text)
                except sr.WaitTimeoutError:
                    continue
                except sr.UnknownValueError:
                    pass
                except sr.RequestError as e:
                    self.root.after(0, self.add_to_conversation, f"Assistant: API error; {e}", "assistant")
                    self.root.after(0, self.stop_listening)
                    break

    def handle_transcribed_text(self, text):
        if not self.is_listening:
            return
        self.transcript.append(text)
        self.add_to_conversation(f"You: {text}", "user")
        if "stop listening" in text.lower():
            self.stop_listening()
        elif "summarize transcript" in text.lower():
            self.summarize_full_transcript()
        elif "save transcript" in text.lower():
            self.save_transcript()

    def save_transcript(self):
        if not self.transcript:
            self.add_to_conversation("Assistant: Transcript is empty.", "assistant")
            return
        file_path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text files", "*.txt"), ("All files", "*.*")], title="Save Transcript")
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write("\n".join(self.transcript))
                self.add_to_conversation(f"Assistant: Transcript saved to {os.path.basename(file_path)}", "assistant")
            except Exception as e:
                self.add_to_conversation(f"Assistant: Error saving file: {e}", "assistant")

    def summarize_full_transcript(self):
        if not self.transcript:
            self.add_to_conversation("Assistant: Transcript is empty. Nothing to summarize.", "assistant")
            return
        full_text = " ".join(self.transcript)
        self.add_to_conversation("Assistant: Summarizing transcript...", "assistant")
        summary = summarize_text(full_text)
        self.add_to_conversation(f"Assistant (Summary): {summary}", "assistant")
        self.speak(summary)

    def process_text_query(self, event=None):
        query = self.text_input.get()
        if query:
            self.add_to_conversation(f"You: {query}", "user")
            self.text_input.delete(0, tk.END)
            threading.Thread(target=self.process_command, args=(query,)).start()

    def process_command(self, query):
        query = query.lower()
        if "open youtube" in query:
            self.speak("Opening YouTube")
            webbrowser.open("https://www.youtube.com")
        elif "search for" in query:
            search_term = query.split("search for")[-1].strip()
            url = f"https://www.google.com/search?q={search_term}"
            webbrowser.open(url)
            self.speak(f"Searching for {search_term}")
        elif "what time is it" in query:
            now = datetime.datetime.now().strftime("%I:%M %p")
            self.speak(f"The current time is {now}")
            self.add_to_conversation(f"Assistant: The current time is {now}.", "assistant")
        elif "summarize" in query and ("youtube" in query or "video" in query):
            url_match = re.search(r"(https?://[^\s]+)", query)
            if url_match:
                youtube_url = url_match.group(1)
                self.speak("Summarizing the YouTube video.")
                summary = summarize_youtube_video(youtube_url)
                self.speak(summary)
                self.add_to_conversation(f"Assistant: {summary}", "assistant")
            else:
                self.speak("Please provide a valid YouTube video URL.")
        elif query.startswith(("what is", "who is", "tell me about")):
            self.answer_question(query)
        else:
            self.speak(f"Searching for {query} in your browser.")
            self.add_to_conversation(f"Assistant: Searching for '{query}' in your browser.", "assistant")
            try:
                webbrowser.open(f"https://www.google.com/search?q={query}")
            except Exception as e:
                self.speak("Sorry, I encountered an error trying to open your web browser.")
                self.add_to_conversation(f"Assistant: Error opening browser: {e}", "assistant")

    def answer_question(self, query):
        try:
            self.speak(f"Searching for an answer to {query}")
            search_result = default_api.google_web_search(query=query)
            if search_result and search_result.get("answer"):
                answer = search_result.get("answer")
                self.speak(answer)
                self.add_to_conversation(f"Assistant: {answer}", "assistant")
            else:
                self.speak("Sorry, I couldn't find an answer.")
        except Exception as e:
            self.speak("Sorry, an error occurred.")
            self.add_to_conversation(f"Assistant: Error: {e}", "assistant")

if __name__ == "__main__":
    root = tk.Tk()
    app = VoiceAssistant(root)
    root.mainloop()
