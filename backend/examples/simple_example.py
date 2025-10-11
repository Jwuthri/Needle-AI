
import asyncio

from agno.models.message import Message
from agno.models.openrouter import OpenRouter
from app.core.config.settings import get_settings


async def test_openrouter():
    try:
        model = OpenRouter(
            id='openai/gpt-4o-mini',
            api_key=get_settings().openrouter_api_key.get_secret_value()
        )

        print('🚀 Testing OpenRouter model with proper Message format...')

        # Create proper Agno Message objects
        messages = [Message(role='user', content='Hello! Say hi back in one word.')]
        response = await model.aresponse(messages)

        print('✅ OpenRouter model works!')
        print(f'Response type: {type(response)}')
        print(f'Response: {response}')
        if hasattr(response, 'content'):
            print(f'Content: {response.content}')
        return True

    except Exception as e:
        print(f'❌ OpenRouter model error: {e}')
        import traceback
        traceback.print_exc()
        return False

# Test it
success = asyncio.run(test_openrouter())
if success:
    print('🎉 OpenRouter model works directly!')
else:
    print('❌ OpenRouter model has issues')
