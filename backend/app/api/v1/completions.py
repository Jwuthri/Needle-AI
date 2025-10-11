"""
Completion endpoints for NeedleAi.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import check_rate_limit, get_user_id_from_header
from app.core.llm.base import BaseLLMClient
from app.dependencies import get_llm_service
from app.exceptions import LLMError, ValidationError
from app.models.completion import (
    CompletionRequest,
    CompletionResponse,
    StreamingCompletionResponse,
)

router = APIRouter()


@router.post("/", response_model=CompletionResponse)
async def create_completion(
    request: CompletionRequest,
    llm_service: BaseLLMClient = Depends(get_llm_service),
    user_id: Optional[str] = Depends(get_user_id_from_header),
    _rate_limit_check = Depends(check_rate_limit)
) -> CompletionResponse:
    """
    Create a text completion using the configured LLM.

    This endpoint provides direct access to the LLM for generating
    text completions without the chat interface abstractions.
    """
    try:
        # Validate request
        if not request.prompt or not request.prompt.strip():
            raise ValidationError("Prompt cannot be empty")

        # Generate completion
        response_text = await llm_service.generate_completion(
            prompt=request.prompt.strip(),
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            top_p=request.top_p,
            stop_sequences=request.stop,
            system_message=request.system_message
        )

        return CompletionResponse(
            text=response_text,
            model=llm_service.get_model_name(),
            usage={
                "prompt_tokens": len(request.prompt.split()),
                "completion_tokens": len(response_text.split()),
                "total_tokens": len(request.prompt.split()) + len(response_text.split())
            }
        )

    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message
        )
    except LLMError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=e.message
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate completion: {str(e)}"
        )


@router.post("/stream")
async def create_streaming_completion(
    request: CompletionRequest,
    llm_service: BaseLLMClient = Depends(get_llm_service),
    user_id: Optional[str] = Depends(get_user_id_from_header),
    _rate_limit_check = Depends(check_rate_limit)
):
    """
    Create a streaming text completion.

    Returns a server-sent events stream of completion tokens.
    This is useful for real-time applications that want to show
    the completion as it's being generated.
    """
    import json

    from fastapi.responses import StreamingResponse

    try:
        # Validate request
        if not request.prompt or not request.prompt.strip():
            raise ValidationError("Prompt cannot be empty")

        async def generate_stream():
            try:
                async for chunk in llm_service.generate_streaming_completion(
                    prompt=request.prompt.strip(),
                    max_tokens=request.max_tokens,
                    temperature=request.temperature,
                    top_p=request.top_p,
                    stop_sequences=request.stop,
                    system_message=request.system_message
                ):
                    response = StreamingCompletionResponse(
                        text=chunk,
                        model=llm_service.get_model_name(),
                        done=False
                    )
                    yield f"data: {json.dumps(response.dict())}\n\n"

                # Send completion signal
                final_response = StreamingCompletionResponse(
                    text="",
                    model=llm_service.get_model_name(),
                    done=True
                )
                yield f"data: {json.dumps(final_response.dict())}\n\n"

            except Exception as e:
                error_response = {
                    "error": str(e),
                    "type": "completion_error"
                }
                yield f"data: {json.dumps(error_response)}\n\n"

        return StreamingResponse(
            generate_stream(),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Encoding": "identity"
            }
        )

    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message
        )
    except LLMError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=e.message
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate streaming completion: {str(e)}"
        )
