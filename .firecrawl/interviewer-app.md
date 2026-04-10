import os
import gradio as gr

from api.audio import STTManager, TTSManager
from api.llm import LLMManager
from utils.config import Config
from resources.prompts import prompts
from ui.coding import get\_problem\_solving\_ui
from ui.instructions import get\_instructions\_ui
from utils.params import default\_audio\_params

def initialize\_services():
 """
 Initialize configuration, LLM, TTS, and STT services.

 Returns:
 tuple: Containing Config, LLMManager, TTSManager, and STTManager instances.
 """
 config = Config()
 llm = LLMManager(config, prompts)
 tts = TTSManager(config)
 stt = STTManager(config)

 # Update default audio parameters with STT streaming setting
 default\_audio\_params\["streaming"\] = stt.streaming

 # Disable TTS in silent mode
 if os.getenv("SILENT", False):
 tts.read\_last\_message = lambda x: None

 return config, llm, tts, stt

def create\_interface(llm, tts, stt, audio\_params):
 """
 Create and configure the Gradio interface.

 Args:
 llm (LLMManager): Language model manager instance.
 tts (TTSManager): Text-to-speech manager instance.
 stt (STTManager): Speech-to-text manager instance.
 audio\_params (dict): Audio parameters for the interface.

 Returns:
 gr.Blocks: Configured Gradio interface.
 """
 with gr.Blocks(title="AI Interviewer", theme=gr.themes.Default()) as demo:
 # Create audio output component (visible only in debug mode)
 audio\_output = gr.Audio(label="Play audio", autoplay=True, visible=os.environ.get("DEBUG", False), streaming=tts.streaming)

 # Render problem-solving and instructions UI components
 get\_problem\_solving\_ui(llm, tts, stt, audio\_params, audio\_output).render()
 get\_instructions\_ui(llm, tts, stt, audio\_params).render()

 return demo

def main():
 """
 Main function to initialize services and launch the Gradio interface.
 """
 config, llm, tts, stt = initialize\_services()
 demo = create\_interface(llm, tts, stt, default\_audio\_params)

 # Launch the Gradio interface
 demo.launch(show\_api=False)

if \_\_name\_\_ == "\_\_main\_\_":
 main()