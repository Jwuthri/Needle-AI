# from app.core.config.settings import get_settings
# from llama_index.core.agent.workflow import FunctionAgent, AgentStreamStructuredOutput
# from llama_index.llms.openai import OpenAI
# from pydantic import BaseModel
# import asyncio

# settings = get_settings()

# # Get API key from settings
# api_key = settings.get_secret("openai_api_key")
# if not api_key:
#     raise ValueError("OpenAI API key not configured")

# # Convert SecretStr to str if needed
# api_key_str = str(api_key) if hasattr(api_key, '__str__') else api_key


# class MathResult(BaseModel):
#     operation: str
#     result: int

# def multiply(x: int, y: int):
#     return x * y

# async def main():
#     agent = FunctionAgent(
#         tools=[multiply],
#         llm=OpenAI(model="gpt-5-mini", api_key=api_key_str),
#         output_cls=MathResult,
#     )
#     handler = agent.run("What is 2 * 3?")
#     async for event in handler.stream_events():
#         if isinstance(event, AgentStreamStructuredOutput):
#             print(event.output)  # dict
#             print(event.get_pydantic_model(MathResult))  # Pydantic model
    
# if __name__ == "__main__":
#     asyncio.run(main())
from app.core.config.settings import get_settings
from llama_index.core.agent.workflow import FunctionAgent, AgentStreamStructuredOutput
from llama_index.llms.openai import OpenAI
from llama_index.core.workflow import Event
from pydantic import BaseModel, Field
import asyncio
from typing import List
from enum import Enum

settings = get_settings()

# Get API key from settings
api_key = settings.get_secret("openai_api_key")
if not api_key:
    raise ValueError("OpenAI API key not configured")

# Convert SecretStr to str if needed
api_key_str = str(api_key) if hasattr(api_key, '__str__') else api_key


class SentimentLabel(str, Enum):
    positive = "positive"
    negative = "negative"
    neutral = "neutral"


class EntityType(str, Enum):
    person = "person"
    organization = "organization"
    location = "location"
    product = "product"


class Sentiment(BaseModel):
    label: SentimentLabel = Field(description="Sentiment classification")
    score: float = Field(ge=0.0, le=1.0, description="Confidence score from 0 to 1")


class Entity(BaseModel):
    text: str = Field(description="The entity text")
    type: EntityType = Field(description="Type of entity")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score")


class TextAnalysisResult(BaseModel):
    original_text: str = Field(description="The original input text")
    summary: str = Field(description="Brief summary of the text")
    sentiment: Sentiment = Field(description="Overall sentiment analysis")
    entities: List[Entity] = Field(description="Named entities found in text")
    key_themes: List[str] = Field(description="Main themes or topics")
    language: str = Field(description="Detected language (e.g., 'English')")
    readability_score: float = Field(ge=0, le=100, description="Readability score 0-100")


async def main():
    # Simpler version - no tools, just structured output
    agent = FunctionAgent(
        tools=[],  # No tools needed for this example
        llm=OpenAI(model="gpt-4o-mini", api_key=api_key_str),
        output_cls=TextAnalysisResult,
        system_prompt="""You are a text analysis expert. Analyze the given text and provide:
        1. A brief summary
        2. Sentiment analysis (positive/negative/neutral with confidence score)
        3. Named entities (people, organizations, locations, products)
        4. Key themes or topics
        5. Language detection
        6. Readability score (0-100, where 100 is easiest to read)
        
        Provide your analysis in the structured format specified."""
    )
    
    # Complex text for analysis
    sample_text = """
    Apple Inc. announced today that they are partnering with Microsoft to develop 
    cutting-edge AI solutions. The collaboration will take place in San Francisco 
    and Seattle. Tim Cook expressed his enthusiasm about the partnership, stating 
    that this could revolutionize the industry. The company aims to create sustainable 
    and innovative products that benefit millions of users worldwide.
    """
    
    print(f"Analyzing text:\n{sample_text.strip()}\n")
    print("=" * 80)
    print("STREAMING EVENTS:")
    print("=" * 80)
    
    handler = agent.run(f"Analyze this text: {sample_text}")
    
    event_count = 0
    async for event in handler.stream_events():
        event_count += 1
        event_type = type(event).__name__
        print(f"\n[Event #{event_count}] Type: {event_type}")
        
        if isinstance(event, AgentStreamStructuredOutput):
            print("  ✓ STRUCTURED OUTPUT RECEIVED")
            print("-" * 80)
            
            # Access the output directly as dict
            output_dict = event.output
            print(f"  Raw output keys: {list(output_dict.keys())}")
            
            # Get as Pydantic model
            try:
                pydantic_result = event.get_pydantic_model(TextAnalysisResult)
                
                print(f"\n  📄 Original Text: {pydantic_result.original_text[:50]}...")
                print(f"\n  📝 Summary: {pydantic_result.summary}")
                
                print(f"\n  😊 Sentiment:")
                print(f"     Label: {pydantic_result.sentiment.label}")
                print(f"     Score: {pydantic_result.sentiment.score:.2f}")
                
                print(f"\n  🏷️  Named Entities ({len(pydantic_result.entities)}):")
                for entity in pydantic_result.entities:
                    print(f"     - {entity.text} ({entity.type.value}) - Confidence: {entity.confidence:.2f}")
                
                print(f"\n  🎯 Key Themes:")
                for theme in pydantic_result.key_themes:
                    print(f"     - {theme}")
                
                print(f"\n  🌐 Language: {pydantic_result.language}")
                print(f"  📊 Readability Score: {pydantic_result.readability_score}/100")
            except Exception as e:
                print(f"  ❌ Error parsing structured output: {e}")
                print(f"  Raw output: {output_dict}")
            
            print("-" * 80)
        else:
            # Print other event types for debugging
            print(f"  ⚙ Event: {event}")
            if hasattr(event, '__dict__'):
                print(f"     Attributes: {event.__dict__}")
    
    print("\n" + "=" * 80)
    print(f"Total events streamed: {event_count}")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())