# Copyright (c) 2024 Microsoft Corporation.
# Licensed under the MIT License

"""Chat-based OpenAI LLM implementation."""

from collections.abc import Callable
from typing import Any
import time
import asyncio
import async_timeout

from tenacity import (
    AsyncRetrying,
    RetryError,
    Retrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

from graphrag.query.llm.base import BaseLLM, BaseLLMCallback
from graphrag.query.llm.oai.base import OpenAILLMImpl
from graphrag.query.llm.oai.typing import (
    OPENAI_RETRY_ERROR_TYPES,
    OpenaiApiType,
)
from graphrag.query.progress import StatusReporter
from graphrag.llm.extra.factories import is_valid_llm_type, use_chat_llm

_MODEL_REQUIRED_MSG = "model is required"


class ChatOpenAI(BaseLLM, OpenAILLMImpl):
    """Wrapper for OpenAI ChatCompletion models."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        azure_ad_token_provider: Callable | None = None,
        deployment_name: str | None = None,
        api_base: str | None = None,
        api_version: str | None = None,
        api_type: OpenaiApiType = OpenaiApiType.OpenAI,
        organization: str | None = None,
        max_retries: int = 10,
        request_timeout: float = 90.0,
        retry_error_types: tuple[type[BaseException]] = OPENAI_RETRY_ERROR_TYPES,  # type: ignore
        reporter: StatusReporter | None = None,
    ):
        OpenAILLMImpl.__init__(
            self=self,
            api_key=api_key,
            azure_ad_token_provider=azure_ad_token_provider,
            deployment_name=deployment_name,
            api_base=api_base,
            api_version=api_version,
            api_type=api_type,  # type: ignore
            organization=organization,
            max_retries=max_retries,
            request_timeout=request_timeout,
            reporter=reporter,
        )
        self.model = model
        self.retry_error_types = retry_error_types

    def generate(
        self,
        messages: str | list[Any],
        streaming: bool = True,
        callbacks: list[BaseLLMCallback] | None = None,
        **kwargs: Any,
    ) -> str:
        """Generate text."""
        try:
            retryer = Retrying(
                stop=stop_after_attempt(self.max_retries),
                wait=wait_exponential_jitter(max=10),
                reraise=True,
                retry=retry_if_exception_type(self.retry_error_types),
            )
            for attempt in retryer:
                with attempt:
                    return self._generate(
                        messages=messages,
                        streaming=streaming,
                        callbacks=callbacks,
                        **kwargs,
                    )
        except RetryError as e:
            self._reporter.error(
                message="Error at generate()", details={self.__class__.__name__: str(e)}
            )
            return ""
        else:
            # TODO: why not just throw in this case?
            return ""

    async def agenerate(
        self,
        messages: str | list[Any],
        streaming: bool = True,
        callbacks: list[BaseLLMCallback] | None = None,
        **kwargs: Any,
    ) -> str:
        """Generate text asynchronously."""
        try:
            retryer = AsyncRetrying(
                stop=stop_after_attempt(self.max_retries),
                wait=wait_exponential_jitter(max=10),
                reraise=True,
                retry=retry_if_exception_type(self.retry_error_types),  # type: ignore
            )
            async for attempt in retryer:
                with attempt:
                    return await self._agenerate(
                        messages=messages,
                        streaming=streaming,
                        callbacks=callbacks,
                        **kwargs,
                    )
        except RetryError as e:
            self._reporter.error(f"Error at agenerate(): {e}")
            return ""
        else:
            # TODO: why not just throw in this case?
            return ""

    def _generate(
        self,
        messages: str | list[Any],
        streaming: bool = True,
        callbacks: list[BaseLLMCallback] | None = None,
        **kwargs: Any,
    ) -> str:
        model = self.model
        if not model:
            raise ValueError(_MODEL_REQUIRED_MSG)

        llm_type, *models = model.split('.')
        if is_valid_llm_type(llm_type):
            llm_type, *models = model.split('.')
            chat_llm = use_chat_llm(llm_type, model='.'.join(models))
            if streaming:
                return ''.join([chunk.content for chunk in
                                chat_llm.stream(messages, **kwargs)])
            return chat_llm.invoke(messages, **kwargs).content or ''
        response = self.sync_client.chat.completions.create(  # type: ignore
            model=model,
            messages=messages,  # type: ignore
            stream=streaming,
            timeout=self.request_timeout,
            **kwargs,
        )  # type: ignore
        if streaming:
            full_response = ""
            while True:
                try:
                    chunk = response.__next__()  # type: ignore
                    if not chunk or not chunk.choices:
                        continue

                    delta = (
                        chunk.choices[0].delta.content
                        if chunk.choices[0].delta and chunk.choices[0].delta.content
                        else ""
                    )  # type: ignore

                    full_response += delta
                    if callbacks:
                        for callback in callbacks:
                            callback.on_llm_new_token(delta)
                    if chunk.choices[0].finish_reason == "stop":  # type: ignore
                        break
                except StopIteration:
                    break
            return full_response
        return response.choices[0].message.content or ""  # type: ignore

    async def _agenerate(
        self,
        messages: str | list[Any],
        streaming: bool = True,
        callbacks: list[BaseLLMCallback] | None = None,
        **kwargs: Any,
    ) -> str:
        model = self.model
        if not model:
            raise ValueError(_MODEL_REQUIRED_MSG)

        llm_type, *models = model.split('.')
        if is_valid_llm_type(llm_type):
            chat_llm = use_chat_llm(llm_type, model='.'.join(models))
            if streaming:
                return ''.join([chunk.content async for chunk in
                                chat_llm.astream(messages, **kwargs)])
            return (await chat_llm.ainvoke(messages, **kwargs)).content or ''
        # print(self.request_timeout)
        start_time = time.time()
        try:
            async with async_timeout.timeout(240):
                response = await self.async_client.chat.completions.create(  # type: ignore
                    model=model,
                    messages=messages,  # type: ignore
                    stream=streaming,
                    timeout=self.request_timeout,
                    **kwargs,
                )
        except asyncio.TimeoutError:
            print("操作超时")
            return ""
        print(time.time() - start_time)
        if streaming:
            full_response = ""
            while True:
                try:
                    chunk = await response.__anext__()  # type: ignore
                    if not chunk or not chunk.choices:
                        continue

                    delta = (
                        chunk.choices[0].delta.content
                        if chunk.choices[0].delta and chunk.choices[0].delta.content
                        else ""
                    )  # type: ignore

                    full_response += delta
                    if callbacks:
                        for callback in callbacks:
                            callback.on_llm_new_token(delta)
                    if chunk.choices[0].finish_reason == "stop":  # type: ignore
                        break
                except StopIteration:
                    break
            return full_response

        return response.choices[0].message.content or ""  # type: ignore