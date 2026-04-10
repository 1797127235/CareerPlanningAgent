import os
from openai import OpenAI
import anthropic
from utils.errors import APIError
from typing import List, Dict, Generator, Optional, Tuple, Any
import logging

class PromptManager:
 def \_\_init\_\_(self, prompts: Dict\[str, str\]):
 """
 Initialize the PromptManager.

 Args:
 prompts (Dict\[str, str\]): A dictionary of prompt keys and their corresponding text.
 """
 self.prompts: Dict\[str, str\] = prompts
 self.limit: Optional\[str\] = os.getenv("DEMO\_WORD\_LIMIT")

 def add\_limit(self, prompt: str) -> str:
 """
 Add word limit to the prompt if specified in the environment variables.

 Args:
 prompt (str): The original prompt.

 Returns:
 str: The prompt with added word limit if applicable.
 """
 if self.limit:
 prompt += f" Keep your responses very short and simple, no more than {self.limit} words."
 return prompt

 def get\_system\_prompt(self, key: str) -> str:
 """
 Retrieve and limit a system prompt by its key.

 Args:
 key (str): The key for the desired prompt.

 Returns:
 str: The retrieved prompt with added word limit if applicable.

 Raises:
 KeyError: If the key is not found in the prompts dictionary.
 """
 prompt = self.prompts\[key\]
 return self.add\_limit(prompt)

 def get\_problem\_requirements\_prompt(
 self, type: str, difficulty: Optional\[str\] = None, topic: Optional\[str\] = None, requirements: Optional\[str\] = None
 ) -\> str:
 """
 Create a problem requirements prompt with optional parameters.

 Args:
 type (str): The type of problem.
 difficulty (Optional\[str\]): The difficulty level of the problem.
 topic (Optional\[str\]): The topic of the problem.
 requirements (Optional\[str\]): Additional requirements for the problem.

 Returns:
 str: The constructed problem requirements prompt.
 """
 prompt = f"Create a {type} problem. Difficulty: {difficulty}. Topic: {topic}. Additional requirements: {requirements}."
 return self.add\_limit(prompt)

class LLMManager:
 def \_\_init\_\_(self, config: Any, prompts: Dict\[str, str\]):
 """
 Initialize the LLMManager.

 Args:
 config (Any): Configuration object containing LLM settings.
 prompts (Dict\[str, str\]): A dictionary of prompts for the PromptManager.
 """
 self.config = config
 self.llm\_type = config.llm.type
 if self.llm\_type == "ANTHROPIC\_API":
 self.client = anthropic.Anthropic(api\_key=config.llm.key)
 else:
 # all other API types suppose to support OpenAI format
 self.client = OpenAI(base\_url=config.llm.url, api\_key=config.llm.key)

 self.prompt\_manager = PromptManager(prompts)

 self.status = self.test\_llm(stream=False)
 self.streaming = self.test\_llm(stream=True) if self.status else False

 def get\_text(self, messages: List\[Dict\[str, str\]\], stream: Optional\[bool\] = None) -> Generator\[str, None, None\]:
 """
 Generate text from the LLM, optionally streaming the response.

 Args:
 messages (List\[Dict\[str, str\]\]): List of message dictionaries.
 stream (Optional\[bool\]): Whether to stream the response. Defaults to self.streaming if not provided.

 Yields:
 str: Generated text chunks.

 Raises:
 APIError: If an unexpected error occurs during text generation.
 """
 if stream is None:
 stream = self.streaming
 try:
 if self.llm\_type == "OPENAI\_API":
 yield from self.\_get\_text\_openai(messages, stream)
 elif self.llm\_type == "ANTHROPIC\_API":
 yield from self.\_get\_text\_anthropic(messages, stream)
 except Exception as e:
 raise APIError(f"LLM Get Text Error: Unexpected error: {e}")

 def \_get\_text\_openai(self, messages: List\[Dict\[str, str\]\], stream: bool) -> Generator\[str, None, None\]:
 """
 Generate text using OpenAI API.

 Args:
 messages (List\[Dict\[str, str\]\]): List of message dictionaries.
 stream (bool): Whether to stream the response.

 Yields:
 str: Generated text chunks.
 """
 if not stream:
 response = self.client.chat.completions.create(model=self.config.llm.name, messages=messages, temperature=1, max\_tokens=2000)
 yield response.choices\[0\].message.content.strip()
 else:
 response = self.client.chat.completions.create(
 model=self.config.llm.name, messages=messages, temperature=1, stream=True, max\_tokens=2000
 )
 for chunk in response:
 if chunk.choices\[0\].delta.content:
 yield chunk.choices\[0\].delta.content

 def \_get\_text\_anthropic(self, messages: List\[Dict\[str, str\]\], stream: bool) -> Generator\[str, None, None\]:
 """
 Generate text using Anthropic API.

 Args:
 messages (List\[Dict\[str, str\]\]): List of message dictionaries.
 stream (bool): Whether to stream the response.

 Yields:
 str: Generated text chunks.
 """
 system\_message, consolidated\_messages = self.\_prepare\_anthropic\_messages(messages)

 if not stream:
 response = self.client.messages.create(
 model=self.config.llm.name, max\_tokens=2000, temperature=1, system=system\_message, messages=consolidated\_messages
 )
 yield response.content\[0\].text
 else:
 with self.client.messages.stream(
 model=self.config.llm.name, max\_tokens=2000, temperature=1, system=system\_message, messages=consolidated\_messages
 ) as stream:
 yield from stream.text\_stream

 def \_prepare\_anthropic\_messages(self, messages: List\[Dict\[str, str\]\]) -> Tuple\[Optional\[str\], List\[Dict\[str, str\]\]\]:
 """
 Prepare messages for Anthropic API format.

 Args:
 messages (List\[Dict\[str, str\]\]): Original messages in OpenAI format.

 Returns:
 Tuple\[Optional\[str\], List\[Dict\[str, str\]\]\]: Tuple containing system message and consolidated messages.
 """
 system\_message = None
 consolidated\_messages = \[\]

 for message in messages:
 if message\["role"\] == "system":
 if system\_message is None:
 system\_message = message\["content"\]
 else:
 system\_message += "\\n" + message\["content"\]
 else:
 if consolidated\_messages and consolidated\_messages\[-1\]\["role"\] == message\["role"\]:
 consolidated\_messages\[-1\]\["content"\] += "\\n" + message\["content"\]
 else:
 consolidated\_messages.append(message.copy())

 return system\_message, consolidated\_messages

 def test\_llm(self, stream: bool = False) -> bool:
 """
 Test the LLM connection with or without streaming.

 Args:
 stream (bool): Whether to test streaming functionality.

 Returns:
 bool: True if the test is successful, False otherwise.
 """
 try:
 test\_messages = \[\
 {"role": "system", "content": "You just help me test the connection."},\
 {"role": "user", "content": "Hi!"},\
 {"role": "user", "content": "Ping!"},\
 \]
 list(self.get\_text(test\_messages, stream=stream))
 return True
 except APIError as e:
 logging.error(f"LLM test failed: {e}")
 return False
 except Exception as e:
 logging.error(f"Unexpected error during LLM test: {e}")
 return False

 def init\_bot(self, problem: str, interview\_type: str = "coding") -> List\[Dict\[str, str\]\]:
 """
 Initialize the bot with a system prompt and problem description.

 Args:
 problem (str): The problem description.
 interview\_type (str): The type of interview. Defaults to "coding".

 Returns:
 List\[Dict\[str, str\]\]: Initial messages for the bot.
 """
 system\_prompt = self.prompt\_manager.get\_system\_prompt(f"{interview\_type}\_interviewer\_prompt")
 return \[{"role": "system", "content": f"{system\_prompt}\\nThe candidate is solving the following problem:\\n {problem}"}\]

 def get\_problem\_prepare\_messages(self, requirements: str, difficulty: str, topic: str, interview\_type: str) -> List\[Dict\[str, str\]\]:
 """
 Prepare messages for generating a problem based on given requirements.

 Args:
 requirements (str): Specific requirements for the problem.
 difficulty (str): Difficulty level of the problem.
 topic (str): Topic of the problem.
 interview\_type (str): Type of interview.

 Returns:
 List\[Dict\[str, str\]\]: Prepared messages for problem generation.
 """
 system\_prompt = self.prompt\_manager.get\_system\_prompt(f"{interview\_type}\_problem\_generation\_prompt")
 full\_prompt = self.prompt\_manager.get\_problem\_requirements\_prompt(interview\_type, difficulty, topic, requirements)
 return \[\
 {"role": "system", "content": system\_prompt},\
 {"role": "user", "content": full\_prompt},\
 \]

 def get\_problem(self, requirements: str, difficulty: str, topic: str, interview\_type: str) -> Generator\[str, None, None\]:
 """
 Get a problem from the LLM based on the given requirements, difficulty, and topic.

 Args:
 requirements (str): Specific requirements for the problem.
 difficulty (str): Difficulty level of the problem.
 topic (str): Topic of the problem.
 interview\_type (str): Type of interview.

 Yields:
 str: Incrementally generated problem statement.
 """
 messages = self.get\_problem\_prepare\_messages(requirements, difficulty, topic, interview\_type)
 problem = ""
 for text in self.get\_text(messages):
 problem += text
 yield problem

 def update\_chat\_history(
 self, code: str, previous\_code: str, chat\_history: List\[Dict\[str, str\]\], chat\_display: List\[List\[Optional\[str\]\]\]
 ) -\> List\[Dict\[str, str\]\]:
 """
 Update chat history with the latest user message and code.

 Args:
 code (str): Current code.
 previous\_code (str): Previous code.
 chat\_history (List\[Dict\[str, str\]\]): Current chat history.
 chat\_display (List\[List\[Optional\[str\]\]\]): Current chat display.

 Returns:
 List\[Dict\[str, str\]\]: Updated chat history.
 """
 message = chat\_display\[-1\]\[0\]
 if not message:
 message = ""
 if code != previous\_code:
 message += "\\nMY NOTES AND CODE:\\n" + code
 chat\_history.append({"role": "user", "content": message})
 return chat\_history

 def end\_interview\_prepare\_messages(
 self, problem\_description: str, chat\_history: List\[Dict\[str, str\]\], interview\_type: str
 ) -\> List\[Dict\[str, str\]\]:
 """
 Prepare messages to end the interview and generate feedback.

 Args:
 problem\_description (str): The original problem description.
 chat\_history (List\[Dict\[str, str\]\]): The chat history.
 interview\_type (str): The type of interview.

 Returns:
 List\[Dict\[str, str\]\]: Prepared messages for generating feedback.
 """
 transcript = \[f"{message\['role'\].capitalize()}: {message\['content'\]}" for message in chat\_history\[1:\]\]
 system\_prompt = self.prompt\_manager.get\_system\_prompt(f"{interview\_type}\_grading\_feedback\_prompt")
 return \[\
 {"role": "system", "content": system\_prompt},\
 {"role": "user", "content": f"The original problem to solve: {problem\_description}"},\
 {"role": "user", "content": "\\n\\n".join(transcript)},\
 {"role": "user", "content": "Grade the interview based on the transcript provided and give feedback."},\
 \]

 def end\_interview(
 self, problem\_description: str, chat\_history: List\[Dict\[str, str\]\], interview\_type: str = "coding"
 ) -\> Generator\[str, None, None\]:
 """
 End the interview and get feedback from the LLM.

 Args:
 problem\_description (str): The original problem description.
 chat\_history (List\[Dict\[str, str\]\]): The chat history.
 interview\_type (str): The type of interview. Defaults to "coding".

 Yields:
 str: Incrementally generated feedback.
 """
 if len(chat\_history) <= 2:
 yield "No interview history available"
 return
 messages = self.end\_interview\_prepare\_messages(problem\_description, chat\_history, interview\_type)
 feedback = ""
 for text in self.get\_text(messages):
 feedback += text
 yield feedback