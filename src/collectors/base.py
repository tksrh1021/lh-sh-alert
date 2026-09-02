from typing import Protocol


class Collector(Protocol):
    """공고 목록을 raw dict 리스트로 가져온다. 스키마 변환은 normalizer가 담당."""

    def collect(self) -> list[dict]: ...
