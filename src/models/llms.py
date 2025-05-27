from openai import OpenAI
from pydantic import BaseModel
from typing import Any
import os
import dotenv

dotenv.load_dotenv()


text_model = "openai/gpt-4.1-mini"
client = OpenAI(
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1",
)


def llm_call(
    prompt: str,
    system_prompt: str | None = None,
    response_format: BaseModel | None = None,
    model: str = text_model,
) -> str | BaseModel:
    """
    Make a LLM call

    ### Args:
        `prompt` (`str`): The user prompt to send to the LLM.
        `system_prompt` (`str`, optional): System-level instructions for the LLM. Defaults to None.
        `response_format` (`BaseModel`, optional): Pydantic model for structured responses. Defaults to None.
        `model` (`str`, optional): Model identifier to use. Defaults to "openai/gpt-4.1-mini".

    ### Returns:
        The LLM's response, either as raw text or as a parsed object according to `response_format`.
    """
    messages = [
        {"role": "system", "content": system_prompt} if system_prompt else None,
        {"role": "user", "content": prompt},
    ]
    messages = [msg for msg in messages if msg is not None]

    kwargs: dict[str, Any] = {"model": model, "messages": messages}

    if response_format is not None:
        schema = response_format.model_json_schema()
        # print("schema", schema)

        def process_schema(schema_dict: dict[str, Any]) -> dict[str, Any]:
            if schema_dict.get("type") not in ["object", "array"]:
                return schema_dict

            processed = {
                "type": schema_dict.get("type", "object"),
                "additionalProperties": False,
            }

            if "$defs" in schema_dict:
                processed["$defs"] = {}
                for def_name, def_schema in schema_dict["$defs"].items():
                    processed["$defs"][def_name] = process_schema(def_schema)

            if "required" in schema_dict:
                processed["required"] = schema_dict["required"]

            if "title" in schema_dict:
                processed["title"] = schema_dict["title"]

            if "properties" in schema_dict:
                processed["properties"] = {}
                for prop_name, prop_schema in schema_dict["properties"].items():
                    processed["properties"][prop_name] = process_schema(prop_schema)

            if "items" in schema_dict:
                processed["items"] = process_schema(schema_dict["items"])

            return processed

        processed_schema = process_schema(schema)

        kwargs["response_format"] = {
            "type": "json_schema",
            "json_schema": {
                "name": response_format.__name__,
                "strict": True,
                "schema": processed_schema,
            },
        }

        response = client.chat.completions.create(**kwargs)

        if not response.choices or not response.choices[0].message.content:
            raise ValueError(
                "No valid response content received from the API", response
            )

        try:
            return response_format.model_validate_json(
                response.choices[0].message.content
            )
        except Exception as e:
            print("Failed to parse response:", response.choices[0].message.content)
            raise ValueError(f"Failed to parse response: {e}")

    return client.chat.completions.create(**kwargs).choices[0].message.content


def llm_call_messages(
    messages: list[dict[str, str]],
    response_format: BaseModel = None,
    model: str = text_model,
) -> str | BaseModel:
    """
    Make a LLM call with a list of messages instead of a prompt + system prompt

    ### Args:
        `messages` (`list[dict]`): The list of messages to send to the LLM.
        `response_format` (`BaseModel`, optional): Pydantic model for structured responses. Defaults to None.
        `model` (`str`, optional): Model identifier to use. Defaults to "quasar-alpha".
    """
    kwargs: dict[str, Any] = {"model": model, "messages": messages}

    if response_format is not None:
        schema = response_format.schema()
        kwargs["response_format"] = {
            "type": "json_schema",
            "json_schema": {
                "name": response_format.__name__,
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": schema["properties"],
                    "required": schema["required"],
                    "additionalProperties": False,
                },
            },
        }

        response = client.chat.completions.create(**kwargs)
        try:
            return response_format.parse_raw(response.choices[0].message.content)
        except Exception as e:
            print("Failed to parse response:", response)
            raise ValueError(f"Failed to parse response: {e}")

    response = client.chat.completions.create(**kwargs)
    try:
        return response.choices[0].message.content
    except Exception as e:
        print("Failed to parse response:", response)
        raise ValueError(f"Failed to parse response: {e}")
