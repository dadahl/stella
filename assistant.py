import json
from datetime import datetime
import os
import nasa_api 
import re

conversation_state = {}
    
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

def generate_response(inputOVON, sender_from):
    global server_info
    global conversation_history
    server_info = ""
    response_text = "I'm not sure how to respond."
    detected_intents = []
    include_manifest_request = False

    for event in inputOVON["ovon"]["events"]:
        event_type = event["eventType"]
        if event_type == "invite":
            # Check if there is a whisper event
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

            for intent in detected_intents:
                print(intent)
                if intent["intent"] == "nasa":
                   nasa_data = nasa_api.get_nasa()
                   explanation, picture_url = nasa_api.parse_nasa_data(nasa_data)
                   conversation_state[conversation_id]["explanation"] = explanation
                   response_text = f"Today's astronomy picture can be found at: {picture_url}. Here's an explanation {explanation}" 
                   print(f"Generated nasa response:{response_text}")
            if response_text == "":
               response_text = "How can I assist you today?"

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
                "manifest" : {
                    "identification":
                    {
                        "serviceEndpoint": "http://localhost:8767",
                        "organization": "Sandbox_LFAI",
                        "conversationalName": "Stella",
                        "serviceName": "Python Anywhere",
                        "role": "NASA images",
                        "synopsis" : "find a astronomy picture."
                    },
                    "capabilities": [
                        {
                            "keyphrases": [
                                "nasa",
                                "images",
                                "astronomy"
                            ],
                            "languages": [
                                "en-us"
                            ],
                            "descriptions": [
                                "astronomy picture of the day"
                            ],
                            "supportedLayers": [
                                "text"
                            ]
                        }
                    ]
                }
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