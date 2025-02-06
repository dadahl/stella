#import openai
import json
from datetime import datetime
import os
import nasa_api 

import re

conversation_state = {}

with open("./assistant_config.json", "r") as file:
    agent_config = json.load(file)

#openai.api_key = os.getenv("OpenAI_APIKEY")
nasa_key = agent_config.get("nasaAPI")
manifest = agent_config.get("manifest")

messages = [
    {"role": "system", "content": agent_config["personalPrompt"]},
    {"role": "system", "content": agent_config["functionPrompt"]}
]

def extract_location(input_text):
    location_match = re.search(r"(in|for|at) (.+)", input_text, re.IGNORECASE)
    if location_match:
        return location_match.group(2)
    else:
        return None

def search_intent(input_text):
    my_dir = os.path.dirname(__file__)
    json_file_path = os.path.join(my_dir, 'intentConcepts.json')
    with open(json_file_path, 'r') as f:
        concepts_data = json.load(f)

    matched_intents = []
    input_text_lower = input_text.lower()

    if "astronomy" in input_text_lower or "space" in input_text_lower:
        intent = "intent"
        matched_intents.append({intent:"nasa"})
    for concept in concepts_data["concepts"]:
        matched_words = [word for word in concept["examples"] if word in input_text.lower()]
        if matched_words:
            matched_intents.append({"intent": concept["name"], "matched_words": matched_words})
    return matched_intents if matched_intents else None

server_info = ""


# def generate_openai_response(prompt):
#     """Call OpenAI's API to generate a response based on the prompt."""
#     try:
#         # Build the message history from conversation_state, if available
#         message_history = [{"role": "system", "content": "You are a helpful assistant named pete"}]

#         # Add prior context/messages from the conversation state
#         if "messages" in conversation_state:
#             message_history.extend(conversation_state["messages"])  # Assuming conversation_state["messages"] is a list of messages

#         # Add the latest user message to the conversation
#         message_history.append({"role": "user", "content": prompt})

#         # Make the API call
#         response = openai.ChatCompletion.create(
#             model="gpt-4",
#             messages=message_history,
#             max_tokens=200,
#             temperature=0.7
#         )

#         # Ensure response is available before trying to access it
#         if response and "choices" in response and len(response.choices) > 0:
#             assistant_reply = response.choices[0].message["content"].strip()

#             # Update conversation_state with the latest assistant reply
#             if "messages" not in conversation_state:
#                 conversation_state["messages"] = []
#             conversation_state["messages"].append({"role": "user", "content": prompt})
#             conversation_state["messages"].append({"role": "assistant", "content": assistant_reply})

#             return assistant_reply
#         else:
#             return "Error: No valid response received."
#     except openai.OpenAIError as e:  # Catch OpenAI API errors
#         print(f"Error with OpenAI API: {e}")
#         return f"Error with OpenAI API: {str(e)}"
#     except Exception as e:  # Catch general errors
#         print(f"Unexpected error: {e}")
#         return f"Unexpected error: {str(e)}"

def generate_response(inputOVON, sender_from):
    global server_info
    global conversation_history
    server_info = ""
    response_text = "I'm not sure how to respond."
    detected_intents = []
    include_manifest_request = False

    #openai_api_key = inputOVON["ovon"]["conversation"].get("openAIKey", None)

    # if openai_api_key:
    #     openai.api_key = openai_api_key

    for event in inputOVON["ovon"]["events"]:
        event_type = event["eventType"]
        if event_type == "invite":
            # Handle invite events
            utt_event = next((e for e in inputOVON["ovon"]["events"] if e["eventType"] == "whisper"), None)

            if utt_event:
                # Handle the invite with whisper event
                whisper_text = utt_event["parameters"]["dialogEvent"]["features"]["text"]["tokens"][0]["value"]
                detected_intents.extend(search_intent(whisper_text) or [])
                if detected_intents:
                    response_text = "Hello! How can I assist you today?"
            else:
                # Handle the bare invite event
                print(event_type)
                if event_type == "invite":
                    to_url = event.get("sender", {}).get("to", "Unknown")
                    server_info = f"Server: {to_url}"
                    response_text = "Thanks for the invitation, I am ready to assist."

        elif event_type == "requestManifest":
            to_url = event.get("sender", {}).get("to", "Unknown")
            server_info = f"Server: {to_url}"
            response_text = "Thanks for asking, here is my manifest."
            include_manifest_request = True

        elif event_type == "utterance":
            user_input = event["parameters"]["dialogEvent"]["features"]["text"]["tokens"][0]["value"]
            detected_intents.extend(search_intent(user_input) or [])
            print(f"Detected intents: {detected_intents}")
            conversation_id = inputOVON["ovon"]["conversation"]["id"]
            response_text = ""

            if conversation_id not in conversation_state:
                conversation_state[conversation_id] = {}

            if detected_intents:
                for intent in detected_intents:
                   print(intent)
                if intent["intent"] == "nasa":
                   nasa_data = nasa_api.get_nasa()
                   explanation, picture_url = nasa_api.parse_nasa_data(nasa_data)
                   conversation_state[conversation_id]["explanation"] = explanation
                   response_text = f"Today's astronomy picture can be found at: {picture_url}. Here's an explanation {explanation}" 
                   print(f"Generated nasa response:{response_text}")
                else:
                        #response_text = generate_openai_response(user_input)
                        response_text = "I don't know the answer to that"
            

    currentTime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # /find the one with utterance, make if statement
    ovon_response = {
        "ovon": {
            "conversation": inputOVON["ovon"]["conversation"],
            "schema": {
                "version": "0.9.0",
                "url": "not_published_yet"
            },
            "sender": {"from": sender_from},
            "events": []
        }
    }

    # Construct a single whisper event containing all intents
    if detected_intents:
        whisper_event = {
            "eventType": "whisper",
            "parameters": {
                "concepts": [
                    {
                        "concept": intent_info["intent"],
                        "matchedWords": intent_info["matched_words"]
                    }
                    for intent_info in detected_intents if "matched_words" in intent_info
                ]
            }
        }
        ovon_response["ovon"]["events"].append(whisper_event)

    if include_manifest_request:
        manifestRequestEvent = {
            "eventType": "publishManifest",
            "parameters": {
                "manifest":
                    manifest

            }
        }
        ovon_response["ovon"]["events"].append(manifestRequestEvent)

    utterance_event = {
        "eventType": "utterance",
        "parameters": {
            "dialogEvent": {
                "speakerId": "assistant",
                "span": {
                    "startTime": currentTime
                },
                "features": {
                    "text": {
                        "mimeType": "text/plain",
                        "tokens": [{"value": response_text}]
                    }
                }
            }
        }
    }
    ovon_response["ovon"]["events"].append(utterance_event)

    ovon_response_json = json.dumps(ovon_response)

    return ovon_response_json